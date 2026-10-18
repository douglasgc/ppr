"""Read-only HTTP API and official MCP Streamable HTTP transport on one port."""

import argparse
import json
import os
from contextlib import asynccontextmanager
from datetime import date
from secrets import compare_digest
from typing import Literal

import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.concurrency import run_in_threadpool

from .config import PPRConfig
from .data import WorldBankDataLoader
from .dataset import build_dataset, metadata

Language = Literal["pt", "en"]
ChinaMode = Literal["separate", "combined"]
SortBy = Literal["ppr_per_capita", "gdp_per_capita", "ppr", "private_retention_pct", "rank_change"]
LLMS_TEXT = """# PPR study — machine access

Read /api/metadata first for definitions, units and methodological limitations.
GET /api/data?year=2023&alpha=2&min_population=100000&lang=en&china_mode=separate
returns ALL matching calculated records, ALL corresponding raw source records,
exclusion reasons and metadata. No top-N cap or pagination. Null means missing.
Use min_population=0 for every economy with valid essential data.
Use countries=BRA,USA to narrow output WITHOUT changing overall ranks.
GET /api/countries/BRA accepts the same year/alpha/min_population/lang/china_mode.
GET /api/data?china_mode=combined constructs CHN_AGG = CHN+HKG+MAC only when
all essential values exist. It replaces the three rows, recomputes per-capita
values from summed levels and is NOT an official World Bank observation.
sort_by accepts ppr_per_capita, gdp_per_capita, ppr, private_retention_pct, rank_change.

metadata.record_count == len(records); metadata.raw_record_count == len(raw_records).
metadata.complete=true and truncated=false describe the response, not historical
source coverage. Client/LLM context limits may still truncate what a model sees.
Use a file download or country queries when needed; never infer unseen rows.
generated_at is response time, NOT source publication time. Cached data may be revised.

Formula: PPR = GDP - alpha * government consumption. GDP and monetary inputs
are current USD, not PPP-adjusted. G is NOT total government spending.
Alpha=2 operationalizes a Rothbard-inspired premise, not a consensus measure,
official welfare statistic or a complete reconstruction of Rothbard's methodology.
Rank changes compare GDP and PPR in the same year, NOT economic growth over time.
China, Hong Kong and Macao have separate World Bank series. Do not silently combine them.

MCP endpoint: /mcp (Streamable HTTP, not a JSON dump).
Tools: get_metadata, get_dataset, get_country. Resource: ppr://metadata.
OpenAPI: /openapi.json. Interactive documentation: /docs.
If PPR_API_TOKEN is configured, send Authorization: Bearer <token> on every route.
"""


class SourceError(RuntimeError):
    pass


class DatasetService:
    def __init__(self, loader: WorldBankDataLoader | None = None):
        self.loader = loader or WorldBankDataLoader()

    def dataset(self, year: int = 2023, alpha: float = 2, min_population: int = 100_000,
                lang: Language = "en", china_mode: ChinaMode = "separate",
                countries: list[str] | None = None, sort_by: SortBy = "ppr_per_capita") -> dict:
        config = PPRConfig(year=year, alpha_g=alpha, min_population=min_population)
        # Validate options before doing network I/O, including MCP calls.
        if lang not in ("pt", "en") or china_mode not in ("separate", "combined"):
            raise ValueError("Invalid language or China aggregation mode")
        try:
            raw = self.loader.fetch(year)
        except (requests.RequestException, OSError, ValueError) as exc:
            raise SourceError("World Bank data could not be loaded; retry or refresh the local cache via CLI.") from exc
        return build_dataset(raw, config, lang=lang, china_mode=china_mode, countries=countries, sort_by=sort_by)


class BearerMiddleware:
    def __init__(self, app, token: str):
        self.app, self.token = app, token.encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            expected = b"Bearer " + self.token
            if not compare_digest(headers.get(b"authorization", b""), expected):
                await JSONResponse({"detail": "Unauthorized"}, status_code=401,
                                   headers={"WWW-Authenticate": "Bearer"})(scope, receive, send)
                return
        await self.app(scope, receive, send)


def create_app(loader: WorldBankDataLoader | None = None, token: str | None = None) -> FastAPI:
    service = DatasetService(loader)
    mcp = FastMCP("PPR study", instructions=LLMS_TEXT, stateless_http=True, json_response=True)
    read_only = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)

    @mcp.tool(annotations=read_only)
    def get_metadata(lang: Language = "en") -> dict:
        """Read the full field dictionary, units, Rothbard thesis and limitations before using data."""
        return metadata(lang)

    @mcp.tool(annotations=read_only)
    async def get_dataset(year: int = 2023, alpha: float = 2, min_population: int = 100_000,
                          lang: Language = "en", china_mode: ChinaMode = "separate",
                          countries: list[str] | None = None, sort_by: SortBy = "ppr_per_capita") -> dict:
        """Return COMPLETE calculated and raw data, metadata and exclusions. No top-N limit.

        Country selection preserves full-cohort ranks. Combined China requires all
        CHN/HKG/MAC essential inputs; never substitutes or fabricates missing data.
        """
        return await run_in_threadpool(service.dataset, year, alpha, min_population, lang, china_mode, countries, sort_by)

    @mcp.tool(annotations=read_only)
    async def get_country(country_code: str, year: int = 2023, alpha: float = 2,
                          min_population: int = 100_000, lang: Language = "en",
                          china_mode: ChinaMode = "separate") -> dict:
        """Read all fields for one economy, its raw inputs and exclusion reasons. Ranks remain global."""
        return await run_in_threadpool(service.dataset, year, alpha, min_population, lang, china_mode, [country_code])

    @mcp.resource("ppr://metadata", mime_type="application/json")
    def metadata_resource() -> str:
        return json.dumps(metadata(), ensure_ascii=False)

    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app):
        async with mcp.session_manager.run():
            yield

    app = FastAPI(title="PPR study API", version="1.0", description=LLMS_TEXT, lifespan=lifespan)
    app.state.mcp = mcp
    secret = token if token is not None else os.environ.get("PPR_API_TOKEN", "")
    if secret:
        app.add_middleware(BearerMiddleware, token=secret)

    @app.exception_handler(SourceError)
    async def source_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=502)

    @app.exception_handler(ValueError)
    async def bad_parameters(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.get("/", response_class=PlainTextResponse)
    def index():
        return "PPR study: /docs · /api/data · /api/metadata · /llms.txt · /mcp\n"

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/llms.txt", response_class=PlainTextResponse)
    def llms():
        return LLMS_TEXT

    @app.get("/api/metadata")
    def api_metadata(lang: Language = "en"):
        return metadata(lang)

    @app.get("/api/data")
    def api_data(year: int = Query(2023, ge=1960, le=date.today().year),
                 alpha: float = Query(2, ge=0, le=2), min_population: int = Query(100_000, ge=0),
                 lang: Language = "en", china_mode: ChinaMode = "separate",
                 countries: str | None = Query(None, description="Comma-separated codes; view filter, does not rerank."),
                 sort_by: SortBy = "ppr_per_capita"):
        codes = [code.strip().upper() for code in countries.split(",") if code.strip()] if countries is not None else None
        return service.dataset(year, alpha, min_population, lang, china_mode, codes, sort_by)

    @app.get("/api/countries/{country_code}")
    def api_country(country_code: str, year: int = Query(2023, ge=1960, le=date.today().year),
                    alpha: float = Query(2, ge=0, le=2), min_population: int = Query(100_000, ge=0),
                    lang: Language = "en", china_mode: ChinaMode = "separate"):
        result = service.dataset(year, alpha, min_population, lang, china_mode, [country_code])
        if not result["records"] and not result["excluded"] and not result["raw_records"]:
            raise HTTPException(404, "Economy not found for the requested coverage")
        return result

    # REST routes take precedence; the official SDK handles /mcp, initialize and tools/*.
    app.mount("/", mcp_app)
    return app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="PPR read-only JSON API + MCP Streamable HTTP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--cache-dir", default=".cache/ppr")
    args = parser.parse_args(argv)
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        parser.error("This minimal server is local-only. Use an authenticated TLS reverse proxy for remote access.")
    uvicorn.run(create_app(WorldBankDataLoader(args.cache_dir)), host=args.host, port=args.port)


if __name__ == "__main__":
    main()

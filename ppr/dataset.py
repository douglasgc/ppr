"""Complete, JSON-safe data contract shared by downloads, HTTP and MCP."""

import json
from datetime import datetime, timezone

import pandas as pd

from .aggregation import CHINA_COMPONENTS, aggregate_china, invalid_fields
from .config import PPRConfig
from .data import WorldBankDataLoader
from .engine import RothbardEngine
from .i18n import ABOUT, LANGUAGES, t
from .presentation import country_label, prepare_ranking, sort_options

FIELD_MAP = {
    "country_code": "country_code", "country_name": "source_country_name", "year": "year",
    "gdp": "gdp", "consumo_privado": "private_consumption", "investimento": "gross_capital_formation",
    "gastos_governo": "government_consumption", "exportacoes": "exports", "importacoes": "imports",
    "populacao": "population", "alpha_g": "alpha", "gpp": "gpp", "gpp_componentes": "gpp_components",
    "residuo_contabil": "accounting_residual", "ppr": "ppr", "gdp_per_capita": "gdp_per_capita",
    "ppr_per_capita": "ppr_per_capita", "retencao_privada_pct": "private_retention_pct",
    "peso_governo_pct": "government_share_pct", "rank_ppr_per_capita": "rank_ppr_per_capita",
    "rank_gdp_per_capita": "rank_gdp_per_capita", "dif_ranking": "rank_change",
    "nome": "country_name", "recorte": "coverage_note", "posicao": "position",
}
DESCRIPTIONS = {
    "country_code": "World Bank economy code; CHN_AGG is a synthetic aggregate, not ISO-3.",
    "source_country_name": "Name as published by the source; constructed for synthetic aggregates.",
    "country_name": "Localized display name; does not redefine sovereignty.",
    "coverage_note": "Geographic or synthetic aggregation scope.",
    "year": "Observation year. No backfilling across years.", "alpha": "Deduction weight in [0, 2].",
    "gdp": "Gross domestic product, current USD.",
    "government_consumption": "Government final consumption expenditure, current USD; NOT total government spending.",
    "private_consumption": "Household and NPISH final consumption, current USD.",
    "gross_capital_formation": "Gross capital formation including inventories, current USD; not exclusively private.",
    "exports": "Gross exports of goods and services, current USD.",
    "imports": "Gross imports of goods and services, current USD.", "population": "Total population, persons.",
    "gpp": "gdp - government_consumption, current USD.",
    "gpp_components": "private_consumption + gross_capital_formation + exports - imports, current USD.",
    "accounting_residual": "gpp - gpp_components; missing components yield null, not zero.",
    "ppr": "gdp - alpha * government_consumption, current USD. Negative values retained.",
    "gdp_per_capita": "gdp / population, current USD per person.",
    "ppr_per_capita": "ppr / population, current USD per person.",
    "private_retention_pct": "100 * ppr / gdp; may be negative; not disposable income.",
    "government_share_pct": "100 * government_consumption / gdp.",
    "rank_ppr_per_capita": "Descending competition rank of PPR per capita in the full eligible cohort (ties 1,1,3).",
    "rank_gdp_per_capita": "Descending competition rank of GDP per capita in the same cohort.",
    "rank_change": "rank_gdp_per_capita - rank_ppr_per_capita; positive means gaining positions, NOT change over time.",
    "position": "Descending rank for the requested sort criterion; view filters do not rerank.",
}


def records(frame: pd.DataFrame) -> list[dict]:
    columns = [column for column in FIELD_MAP if column in frame]
    # pandas serializes missing and infinite numbers as JSON null; no NaN/Infinity tokens.
    return json.loads(frame[columns].rename(columns=FIELD_MAP).to_json(orient="records", double_precision=15))


def metadata(lang: str = "en") -> dict:
    if lang not in LANGUAGES:
        raise ValueError("Supported languages: pt, en")
    return {
        "schema_version": "1.0", "source": "World Bank Indicators API",
        "source_url": "https://api.worldbank.org/v2/", "units": "monetary values: current USD; population: persons; shares: percent (not bounded to 0–100)",
        "formula": "ppr = gdp - alpha * government_consumption",
        "indicators": {FIELD_MAP[name]: code for code, name in WorldBankDataLoader.INDICATORS.items()},
        "fields": DESCRIPTIONS, "methodology": ABOUT[lang], "china_context": t("china_context", lang),
        "aggregation_note": t("aggregate_note", lang),
        "cautions": ["Not PPP- or inflation-adjusted; not a well-being or disposable-income measure.",
                     "Government consumption is not total government spending; alpha=2 is an operational approximation.",
                     "World Bank values can be revised; local snapshots do not expire automatically.",
                     "Null is missing, not zero. Do not invent missing China aggregates or extrapolate observations."],
    }


def build_dataset(raw: pd.DataFrame, config: PPRConfig, *, lang: str = "en", china_mode: str = "separate",
                  countries: list[str] | None = None, sort_by: str = "ppr_per_capita") -> dict:
    if config.custom_country_codes is not None:
        raise ValueError("Use countries as a view filter; dataset ranks must use the full cohort")
    if "year" in raw and not pd.to_numeric(raw["year"], errors="coerce").eq(config.year).all():
        raise ValueError("All raw observations must match config.year; no cross-year backfilling is allowed")
    catalog = metadata(lang)
    options = sort_options(lang)
    original_sort = next((key for key, value in FIELD_MAP.items() if value == sort_by), sort_by)
    matching = [label for label, (metric, _) in options.items() if metric == original_sort]
    if not matching:
        raise ValueError(f"Unsupported sort_by: {sort_by}")
    prepared, aggregation = aggregate_china(raw, china_mode)
    aggregation["missing"] = {code: [FIELD_MAP.get(field, field) for field in fields]
                              for code, fields in aggregation["missing"].items()}
    calculated = RothbardEngine().calculate(prepared, config)
    ranked = prepare_ranking(calculated, matching[0], lang)
    ranked_count = len(ranked)
    excluded = []
    eligible_codes = set(ranked["country_code"])
    for _, row in prepared.iterrows():
        if row["country_code"] not in eligible_codes:
            fields = invalid_fields(row)
            excluded.append({"country_code": row["country_code"],
                             "country_name": country_label(row["country_code"], row.get("country_name", ""), lang)[0],
                             "reasons": [f"missing_or_invalid:{FIELD_MAP[field]}" for field in fields] or ["below_min_population"]})
    raw_selected = raw.copy()
    if countries is not None:
        codes = {code.strip().upper() for code in countries}
        ranked = ranked.loc[ranked["country_code"].isin(codes)]
        raw_codes = codes | (set(CHINA_COMPONENTS) if "CHN_AGG" in codes else set())
        raw_selected = raw_selected.loc[raw_selected["country_code"].isin(raw_codes)]
        excluded = [item for item in excluded if item["country_code"] in codes]
    raw_selected["year"] = config.year
    return {
        "metadata": {**catalog, "generated_at": datetime.now(timezone.utc).isoformat(),
                     "year": config.year, "alpha": config.alpha_g, "min_population": config.min_population,
                     "language": lang, "sort_by": sort_by, "ranked_count": ranked_count,
                     "record_count": len(ranked), "raw_record_count": len(raw_selected),
                     "excluded_count": len(excluded), "complete": True, "truncated": False,
                     "countries": countries, "aggregation": aggregation,
                     "ranking_scope": "All eligible economies after aggregation and population filtering; country selection is view-only.",
                     "snapshot_note": "generated_at is response generation time, not source publication or refresh time."},
        "records": records(ranked), "excluded": excluded, "raw_records": records(raw_selected),
    }

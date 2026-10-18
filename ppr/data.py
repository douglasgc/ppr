"""Adaptador HTTP do Banco Mundial e cache dos dados harmonizados."""

import os
import tempfile
import time
from pathlib import Path

import pandas as pd
import requests

from .config import PPRConfig


class WorldBankDataLoader:
    BASE_URL = "https://api.worldbank.org/v2"
    INDICATORS = {
        "NY.GDP.MKTP.CD": "gdp",
        "NE.CON.PRVT.CD": "consumo_privado",
        # Formação BRUTA de capital, incluindo estoques (não apenas capital fixo).
        "NE.GDI.TOTL.CD": "investimento",
        "NE.CON.GOVT.CD": "gastos_governo",
        "NE.EXP.GNFS.CD": "exportacoes",
        "NE.IMP.GNFS.CD": "importacoes",
        "SP.POP.TOTL": "populacao",
    }

    def __init__(self, cache_dir: str | Path = ".cache/ppr", timeout: float = 30):
        self.cache_dir = Path(cache_dir)
        self.timeout = timeout

    def _page(self, endpoint: str, params: dict) -> list:
        for attempt in range(3):
            try:
                response = requests.get(
                    f"{self.BASE_URL}/{endpoint}", params=params, timeout=self.timeout
                )
                response.raise_for_status()
                payload = response.json()
                break
            except (requests.RequestException, ValueError):
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
        if (
            not isinstance(payload, list)
            or len(payload) != 2
            or not isinstance(payload[0], dict)
            or not isinstance(payload[1], list)
        ):
            raise ValueError("Resposta inválida ou sem dados da API do Banco Mundial.")
        return payload

    def _records(self, endpoint: str, **params) -> list[dict]:
        query = {"format": "json", "per_page": 400, **params}
        metadata, rows = self._page(endpoint, {**query, "page": 1})
        records = list(rows)
        for page in range(2, int(metadata.get("pages", 1)) + 1):
            _, rows = self._page(endpoint, {**query, "page": page})
            records.extend(rows)
        return records

    def fetch(self, year: int, *, refresh: bool = False) -> pd.DataFrame:
        cache_path = self.cache_dir / f"world_bank_v1_{year}.csv"
        if cache_path.exists() and not refresh:
            return pd.read_csv(cache_path, dtype={"country_code": str})

        countries = self._records("country")
        frame = pd.DataFrame(
            [
                {"country_code": c["id"], "country_name": c["name"]}
                for c in countries
                if c.get("region", {}).get("id") not in (None, "", "NA")
            ],
            columns=["country_code", "country_name"],
        )
        for code, name in self.INDICATORS.items():
            records = self._records(f"country/all/indicator/{code}", date=str(year))
            values = pd.DataFrame(
                [
                    {"country_code": r["countryiso3code"], name: r["value"]}
                    for r in records
                    if r.get("countryiso3code") and str(r.get("date")) == str(year)
                ],
                columns=["country_code", name],
            )
            frame = frame.merge(values, on="country_code", how="left", validate="one_to_one")
        frame["year"] = year

        self._write_cache(frame, cache_path)
        return frame

    def fetch_history(self, country_codes: tuple[str, ...], start_year: int = 1960,
                      end_year: int = 2023, *, refresh: bool = False) -> pd.DataFrame:
        config = PPRConfig(year=end_year, min_population=0, custom_country_codes=country_codes)
        PPRConfig(year=start_year)
        if start_year > end_year or not config.custom_country_codes:
            raise ValueError("Informe países e um intervalo de anos válido.")
        codes = tuple(sorted(config.custom_country_codes))
        cache_path = self.cache_dir / f"history_v1_{'_'.join(codes)}_{start_year}_{end_year}.csv"
        if cache_path.exists() and not refresh:
            return pd.read_csv(cache_path, dtype={"country_code": str})
        frame = pd.MultiIndex.from_product(
            [codes, range(start_year, end_year + 1)], names=["country_code", "year"]
        ).to_frame(index=False)
        frame["country_name"] = frame["country_code"]
        for code, name in self.INDICATORS.items():
            if name not in ("gdp", "gastos_governo", "populacao"):
                continue
            rows = self._records(f"country/{';'.join(codes)}/indicator/{code}", date=f"{start_year}:{end_year}")
            values = pd.DataFrame([
                {"country_code": row["countryiso3code"], "year": int(row["date"]), name: row["value"]}
                for row in rows if row.get("countryiso3code") in codes
                and str(row.get("date", "")).isdigit() and start_year <= int(row["date"]) <= end_year
            ], columns=["country_code", "year", name])
            frame = frame.merge(values, on=["country_code", "year"], how="left", validate="one_to_one")
        self._write_cache(frame, cache_path)
        return frame

    def _write_cache(self, frame: pd.DataFrame, cache_path: Path) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # Substituição atômica evita que CLI/dashboard leiam um CSV pela metade.
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", dir=self.cache_dir, delete=False, encoding="utf-8"
        ) as handle:
            temporary = Path(handle.name)
            try:
                frame.to_csv(handle, index=False)
                handle.close()
                os.replace(temporary, cache_path)
            finally:
                temporary.unlink(missing_ok=True)

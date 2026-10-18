"""Orquestração do pipeline e API pública do cliente."""

from dataclasses import replace
from pathlib import Path

import pandas as pd

from .config import PPRConfig
from .data import WorldBankDataLoader
from .engine import RothbardEngine


class RothbardPPRClient:
    TOP_COLUMNS = [
        "rank_ppr_per_capita", "country_code", "populacao", "ppr_per_capita", "gdp_per_capita",
        "retencao_privada_pct", "peso_governo_pct", "dif_ranking",
    ]

    def __init__(self, config: PPRConfig | None = None, loader: WorldBankDataLoader | None = None):
        self._config = config or PPRConfig()
        self.loader = loader or WorldBankDataLoader()
        self.engine = RothbardEngine()
        self._raw_data: pd.DataFrame | None = None
        self._processed_data: pd.DataFrame | None = None

    @property
    def config(self) -> PPRConfig:
        return self._config

    def set_config(self, **changes) -> "RothbardPPRClient":
        updated = replace(self.config, **changes)
        if updated.year != self.config.year:
            self._raw_data = None
        self._config = updated
        self._processed_data = None
        return self

    def load_data(self, *, refresh: bool = False) -> "RothbardPPRClient":
        if self._raw_data is None or refresh:
            data = self.loader.fetch(self.config.year, refresh=refresh)
            self._raw_data = data.copy(deep=True)
            self._processed_data = None
        return self

    def calculate(self) -> pd.DataFrame:
        self.load_data()
        if self._processed_data is None:
            self._processed_data = self.engine.calculate(self._raw_data, self.config)
        return self._processed_data.copy(deep=True)

    def get_top(self, n: int = 10) -> pd.DataFrame:
        if type(n) is not int or n < 1:
            raise ValueError("n deve ser um inteiro positivo.")
        return self.calculate()[self.TOP_COLUMNS].head(n)

    def get_country(self, country_code: str) -> pd.Series:
        data = self.calculate()
        result = data.loc[data["country_code"] == country_code.strip().upper()]
        if result.empty:
            raise ValueError(f"País {country_code} não encontrado nos dados filtrados.")
        return result.iloc[0].copy()

    def export(self, path: str | Path) -> Path:
        destination = Path(path)
        if destination.suffix.lower() not in (".csv", ".json"):
            raise ValueError("O arquivo de exportação deve terminar em .csv ou .json.")
        data = self.calculate()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.suffix.lower() == ".csv":
            data.to_csv(destination, index=False)
        else:
            destination.write_text(
                data.to_json(orient="records", indent=2, force_ascii=False), encoding="utf-8"
            )
        return destination

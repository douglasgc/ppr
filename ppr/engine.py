"""Regras de cálculo, sem HTTP, disco ou interface gráfica."""

import math

import pandas as pd

from .config import PPRConfig


class RothbardEngine:
    REQUIRED = {"country_code", "gdp", "gastos_governo", "populacao"}
    COMPONENTS = ("consumo_privado", "investimento", "exportacoes", "importacoes")

    def calculate(self, data: pd.DataFrame, config: PPRConfig) -> pd.DataFrame:
        missing = self.REQUIRED - set(data.columns)
        if missing:
            raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(sorted(missing))}")
        df = data.copy(deep=True)
        df = df.loc[df["country_code"].notna()].copy()
        df["country_code"] = df["country_code"].astype(str).str.strip().str.upper()
        if df["country_code"].duplicated().any():
            raise ValueError("O dataset deve conter uma única linha por país.")

        numeric = ("gdp", "gastos_governo", "populacao", *self.COMPONENTS)
        for column in numeric:
            if column not in df:
                df[column] = float("nan")
            df[column] = pd.to_numeric(df[column], errors="coerce")
        valid = df[["gdp", "gastos_governo", "populacao"]].apply(
            lambda series: series.map(lambda value: pd.notna(value) and math.isfinite(value))
        ).all(axis=1)
        df = df.loc[
            valid
            & (df["gdp"] > 0)
            & (df["gastos_governo"] >= 0)
            & (df["populacao"] > 0)
            & (df["populacao"] >= config.min_population)
        ].copy()
        if config.custom_country_codes is not None:
            df = df.loc[df["country_code"].isin(config.custom_country_codes)].copy()

        df["year"] = config.year
        df["alpha_g"] = config.alpha_g
        df["gpp"] = df["gdp"] - df["gastos_governo"]
        df["gpp_componentes"] = (
            df["consumo_privado"] + df["investimento"] + df["exportacoes"] - df["importacoes"]
        )
        df["residuo_contabil"] = df["gpp"] - df["gpp_componentes"]
        df["ppr"] = df["gdp"] - config.alpha_g * df["gastos_governo"]
        df["gdp_per_capita"] = df["gdp"] / df["populacao"]
        df["ppr_per_capita"] = df["ppr"] / df["populacao"]
        df["retencao_privada_pct"] = df["ppr"] / df["gdp"] * 100
        df["peso_governo_pct"] = df["gastos_governo"] / df["gdp"] * 100
        for metric in ("ppr", "gdp"):
            # Empates reais recebem a mesma posição: 1, 1, 3.
            df[f"rank_{metric}_per_capita"] = (
                df[f"{metric}_per_capita"].rank(ascending=False, method="min").astype("int64")
            )
        df["dif_ranking"] = df["rank_gdp_per_capita"] - df["rank_ppr_per_capita"]
        return df.sort_values(["rank_ppr_per_capita", "country_code"]).reset_index(drop=True)

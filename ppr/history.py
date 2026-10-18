"""Historical series: preserve gaps, never sum a partial China aggregate."""

from math import isfinite

import pandas as pd

from .aggregation import CHINA_AGGREGATE, CHINA_COMPONENTS
from .config import PPRConfig


def calculate_history(raw: pd.DataFrame, country_code: str, alpha: float = 2) -> pd.DataFrame:
    PPRConfig(alpha_g=alpha)
    columns = ["year", "country_code", "alpha", "gdp", "gastos_governo", "populacao",
               "ppr", "gdp_per_capita", "ppr_per_capita", "retencao_privada_pct"]
    if raw.empty:
        return pd.DataFrame(columns=columns)
    required = {"year", "country_code", "gdp", "gastos_governo", "populacao"}
    if missing := required - set(raw.columns):
        raise ValueError(f"Missing historical fields: {', '.join(sorted(missing))}")
    code = country_code.upper()
    codes = CHINA_COMPONENTS if code == CHINA_AGGREGATE else (code,)
    parts = raw.loc[raw["country_code"].isin(codes)].copy()
    if parts.duplicated(["country_code", "year"]).any():
        raise ValueError("Historical data must have one row per economy and year")
    years = sorted(raw["year"].unique())
    index = pd.MultiIndex.from_product([codes, years], names=["country_code", "year"])
    parts = parts.set_index(["country_code", "year"]).reindex(index)
    for field in ("gdp", "gastos_governo", "populacao"):
        values = pd.to_numeric(parts[field], errors="coerce")
        valid = values.map(lambda value: pd.notna(value) and isfinite(value))
        valid &= values.ge(0) if field == "gastos_governo" else values.gt(0)
        parts[field] = values.where(valid)
    result = parts[["gdp", "gastos_governo", "populacao"]].groupby("year").sum(min_count=len(codes))
    result["country_code"] = code
    result["alpha"] = alpha
    # Keep GDP even where G is unknown; PPR is then unknown, not zero.
    result["ppr"] = result["gdp"] - alpha * result["gastos_governo"]
    result["gdp_per_capita"] = result["gdp"] / result["populacao"]
    result["ppr_per_capita"] = result["ppr"] / result["populacao"]
    result["retencao_privada_pct"] = result["ppr"] / result["gdp"] * 100
    return result.reset_index()[columns]

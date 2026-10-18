"""Explicit synthetic China aggregate, computed before any population filtering."""

from math import isfinite

import pandas as pd

from .data import WorldBankDataLoader

CHINA_COMPONENTS = ("CHN", "HKG", "MAC")
CHINA_AGGREGATE = "CHN_AGG"


def invalid_fields(row: pd.Series) -> list[str]:
    invalid = []
    for field in ("gdp", "gastos_governo", "populacao"):
        value = pd.to_numeric(row.get(field), errors="coerce")
        if pd.isna(value) or not isfinite(value) or value < 0 or (field != "gastos_governo" and value == 0):
            invalid.append(field)
    return invalid


def aggregate_china(raw: pd.DataFrame, mode: str = "separate") -> tuple[pd.DataFrame, dict]:
    if mode not in ("separate", "combined"):
        raise ValueError("china_mode must be separate or combined")
    status = {"mode": mode, "applied": False, "code": CHINA_AGGREGATE,
              "components": list(CHINA_COMPONENTS), "missing": {}}
    if mode == "separate":
        return raw.copy(deep=True), status
    parts = raw.loc[raw["country_code"].isin(CHINA_COMPONENTS)]
    if parts["country_code"].duplicated().any():
        raise ValueError("China aggregation requires one row per component")
    missing = {}
    for code in CHINA_COMPONENTS:
        rows = parts.loc[parts["country_code"] == code]
        invalid = invalid_fields(rows.iloc[0]) if not rows.empty else ["series"]
        if invalid:
            missing[code] = invalid
    if missing:
        status["missing"] = missing
        return raw.copy(deep=True), status
    if "year" in parts and parts["year"].nunique(dropna=False) != 1:
        raise ValueError("Cannot aggregate China series from different years")
    aggregate = {"country_code": CHINA_AGGREGATE, "country_name": "China aggregate (CHN + HKG + MAC)"}
    for field in WorldBankDataLoader.INDICATORS.values():
        values = pd.to_numeric(parts[field], errors="coerce") if field in parts else pd.Series(dtype=float)
        # Optional components stay unknown unless all three series are finite.
        aggregate[field] = values.sum() if len(values) == 3 and values.map(lambda v: pd.notna(v) and isfinite(v)).all() else float("nan")
    if "year" in parts:
        aggregate["year"] = parts["year"].iloc[0]
    status["applied"] = True
    remaining = raw.loc[~raw["country_code"].isin(CHINA_COMPONENTS)]
    return pd.concat([remaining, pd.DataFrame([aggregate])], ignore_index=True), status

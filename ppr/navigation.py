"""Shareable, validated country links without JavaScript or client-side hacks."""

import re
from datetime import date
from math import isfinite
from urllib.parse import urlencode

from .config import PPRConfig


def country_url(country_code: str | None = None, **context) -> str:
    parameters = {key: value for key, value in context.items() if value is not None}
    if country_code:
        parameters["country"] = country_code
    return "?" + urlencode(parameters)


def route_defaults(parameters: dict) -> dict:
    def integer(key, default, minimum, maximum):
        try:
            value = int(parameters.get(key, default))
        except (ValueError, TypeError):
            return default
        return value if minimum <= value <= maximum else default

    year = integer("year", 2023, 1960, date.today().year)
    population = integer("min_population", 100_000, 0, 10**12)
    try:
        alpha = float(parameters.get("alpha", 2))
        if not isfinite(alpha) or not 0 <= alpha <= 2:
            alpha = 2.0
    except (ValueError, TypeError):
        alpha = 2.0
    config = PPRConfig(year, alpha, population)
    scenario = {2: "double", 1: "single", 0: "none"}.get(alpha, "custom")
    sort = parameters.get("sort", "ppr_per_capita")
    if sort not in ("ppr_per_capita", "gdp_per_capita", "ppr", "retencao_privada_pct", "dif_ranking"):
        sort = "ppr_per_capita"
    return {"data_year": config.year, "min_population": config.min_population,
            "custom_alpha": config.alpha_g, "scenario": scenario, "sort_order": sort,
            "language": "en" if parameters.get("lang") == "en" else "pt",
            "china_mode": "combined" if parameters.get("china_mode") == "combined" else "separate",
            "country_search": parameters.get("q", "")}


def requested_country(parameters: dict) -> str | None:
    code = str(parameters.get("country", "")).upper().strip()
    return code if re.fullmatch(r"[A-Z]{3}|CHN_AGG", code) else None

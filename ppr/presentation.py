"""Locale-aware presentation; numerical calculation rules remain in the engine."""

from html import escape
from math import isfinite
from unicodedata import normalize

import pandas as pd
import pycountry
from babel import Locale

from .i18n import t
from .navigation import country_url

SORT_FIELDS = [
    ("sort_ppr_pc", "ppr_per_capita", "ppr_pc"),
    ("sort_gdp_pc", "gdp_per_capita", "gdp_pc"),
    ("sort_ppr", "ppr", "ppr_total"),
    ("sort_retention", "retencao_privada_pct", "retention"),
    ("sort_change", "dif_ranking", "gain"),
]


def sort_options(lang: str = "pt") -> dict:
    return {t(key, lang): (metric, t(title, lang)) for key, metric, title in SORT_FIELDS}


def china_labels(lang: str = "pt") -> dict:
    return {"CHN": (t("china", lang), "🇨🇳"), "HKG": (t("hong_kong", lang), "🇭🇰"),
            "MAC": (t("macao", lang), "🇲🇴"), "CHN_AGG": (t("china_aggregate", lang), "🇨🇳")}


SORT_OPTIONS = sort_options()
CHINA_LABELS = china_labels()
CHINA_CONTEXT = t("china_context")
TAIWAN_REFERENCE = "https://datahelpdesk.worldbank.org/knowledgebase/articles/114933-where-are-your-data-on-taiwan"


def is_taiwan_query(query: str) -> bool:
    normalized = normalize("NFKD", query.casefold()).encode("ascii", "ignore").decode().strip()
    return normalized == "twn" or any(alias in normalized for alias in ("taiwan", "taiua", "formosa"))


def taiwan_availability_note(raw: pd.DataFrame, ranked: pd.DataFrame, lang: str = "pt") -> str:
    if ranked["country_code"].eq("TWN").any():
        return ""
    return t("taiwan_filtered" if raw["country_code"].eq("TWN").any() else "taiwan_missing", lang)


def number(value: float, decimals: int = 0, lang: str = "pt") -> str:
    formatted = f"{value:,.{decimals}f}"
    return formatted.translate(str.maketrans({",": ".", ".": ","})) if lang == "pt" else formatted


def money(value: float, decimals: int = 0, lang: str = "pt") -> str:
    return f"US$ {number(value, decimals, lang)}"


def percent(value: float, lang: str = "pt") -> str:
    return f"{number(value, 1, lang)}%"


def change(value: int, lang: str = "pt") -> str:
    value = int(value)
    if not value:
        return t("unchanged", lang)
    return t("places", lang, arrow="↑" if value > 0 else "↓", count=abs(value),
             unit=t("place_one" if abs(value) == 1 else "place_many", lang))


def country_label(code: str, fallback: str, lang: str = "pt") -> tuple[str, str]:
    if code == "TWN":
        return "Taiwan", "🇹🇼"
    labels = china_labels(lang)
    if code in labels:
        return labels[code]
    country = pycountry.countries.get(alpha_3=code)
    if country is None:
        return ("Kosovo", "🇽🇰") if code == "XKX" else (fallback, "🌐")
    locale = Locale("pt", "BR") if lang == "pt" else Locale("en", "US")
    name = locale.territories.get(country.alpha_2, fallback)
    flag = "".join(chr(127397 + ord(character)) for character in country.alpha_2)
    return name, flag


def prepare_ranking(data: pd.DataFrame, sort_label: str, lang: str = "pt") -> pd.DataFrame:
    result = data.copy(deep=True)
    if "country_name" not in result:
        result["country_name"] = result["country_code"]
    labels = [country_label(row.country_code, row.country_name, lang) for row in result.itertuples()]
    result["nome"] = [label[0] for label in labels]
    result["bandeira"] = [label[1] for label in labels]
    scopes = {"CHN": t("mainland_scope", lang), "HKG": t("sar_scope", lang), "MAC": t("sar_scope", lang)}
    scopes["CHN_AGG"] = t("aggregate_scope", lang)
    result["recorte"] = result["country_code"].map(scopes).fillna("")
    result["search_aliases"] = [" ".join(country_label(row.country_code, row.country_name, language)[0]
                                       for language in ("pt", "en")) for row in result.itertuples()]
    metric, _ = sort_options(lang)[sort_label]
    result["posicao"] = result[metric].rank(method="min", ascending=False).astype(int)
    return result.sort_values([metric, "nome"], ascending=[False, True]).reset_index(drop=True)


def search_ranking(data: pd.DataFrame, query: str, codes: list[str]) -> pd.DataFrame:
    """View filtering preserves positions; search accepts names in either language."""
    result = data
    if codes:
        result = result.loc[result["country_code"].isin(codes)]
    normalized = normalize("NFKD", query.strip().casefold()).encode("ascii", "ignore").decode()
    if normalized:
        columns = ["nome", "country_code", "country_name", "search_aliases"]
        text = result[columns].fillna("").agg(" ".join, axis=1)
        searchable = text.map(lambda value: normalize("NFKD", value.casefold()).encode("ascii", "ignore").decode())
        result = result.loc[searchable.str.contains(normalized, regex=False)]
    return result.copy()


def china_exclusion_note(raw: pd.DataFrame, ranked: pd.DataFrame, year: int, min_population: int,
                         lang: str = "pt") -> str:
    if ranked["country_code"].eq("CHN").any():
        return ""
    rows = raw.loc[raw["country_code"] == "CHN"]
    if rows.empty:
        reason = t("not_returned", lang)
    else:
        row = rows.iloc[0]
        invalid = []
        for column, label in (("gdp", "PIB" if lang == "pt" else "GDP"),
                              ("gastos_governo", t("government_field", lang)),
                              ("populacao", t("population", lang).lower())):
            value = pd.to_numeric(row.get(column), errors="coerce")
            if pd.isna(value) or not isfinite(value) or value < 0 or (column != "gastos_governo" and value == 0):
                invalid.append(label)
        reason = (t("invalid", lang, fields=", ".join(invalid)) if invalid else
                  t("below_population", lang, count=number(min_population, lang=lang)))
    return t("china_missing", lang, year=year, reason=reason)


def metric_value(row: pd.Series, metric: str, lang: str = "pt") -> str:
    if metric == "retencao_privada_pct":
        return percent(row[metric], lang)
    if metric == "dif_ranking":
        return change(row[metric], lang)
    return money(row[metric], lang=lang)


def podium_html(data: pd.DataFrame, sort_label: str, lang: str = "pt", link_context: dict | None = None) -> str:
    metric, title = sort_options(lang)[sort_label]
    cards = []
    for _, row in data.head(3).iterrows():
        hint = t("retained_hint", lang, value=percent(row["retencao_privada_pct"], lang))
        url = escape(country_url(row["country_code"], **(link_context or {"lang": lang})), quote=True)
        cards.append(
            f'<article class="leader-card"><span class="leader-place">#{int(row["posicao"]):02d}</span>'
            f'<div class="leader-country"><a class="country-link" href="{url}" target="_self">'
            f'{row["bandeira"]} {escape(row["nome"])}</a></div>'
            f'<div class="leader-value">{metric_value(row, metric, lang)}</div>'
            f'<div class="muted">{title} · {hint}</div>'
            f'<div class="muted">{t("population_note", lang, count=number(row["populacao"], lang=lang))}</div></article>'
        )
    return '<div class="leaders">' + "".join(cards) + "</div>"


def leaderboard_html(data: pd.DataFrame, sort_label: str, lang: str = "pt", link_context: dict | None = None) -> str:
    metric, title = sort_options(lang)[sort_label]
    comparison = "ppr_per_capita" if metric == "gdp_per_capita" else "gdp_per_capita"
    comparison_title = t("ppr_pc" if comparison == "ppr_per_capita" else "gdp_pc", lang)
    rows = []
    for _, row in data.iterrows():
        delta = int(row["dif_ranking"])
        tone = "up" if delta > 0 else "down" if delta < 0 else "neutral"
        scope = f' · {escape(row["recorte"])}' if row.get("recorte", "") else ""
        url = escape(country_url(row["country_code"], **(link_context or {"lang": lang})), quote=True)
        rows.append(
            '<tr>'
            f'<td><span class="position">{int(row["posicao"]):02d}</span></td>'
            f'<th scope="row"><a class="country-link country-cell" href="{url}" target="_self" '
            f'title="{t("open_analysis", lang)}"><span class="flag">{row["bandeira"]}</span>'
            f'<span>{escape(row["nome"])}<small>{escape(row["country_code"])}{scope}</small>'
            f'<small class="mobile-population">{t("population_note", lang, count=number(row["populacao"], lang=lang))}</small></span></a></th>'
            f'<td class="population-column">{number(row["populacao"], lang=lang)}</td>'
            f'<td class="primary-value">{metric_value(row, metric, lang)}</td>'
            f'<td class="secondary-column">{money(row[comparison], lang=lang)}</td>'
            f'<td class="secondary-column">{percent(row["retencao_privada_pct"], lang)}</td>'
            f'<td><span class="movement {tone}">{change(delta, lang)}</span></td></tr>'
        )
    return (
        '<div class="leaderboard-wrap"><table class="leaderboard">'
        f'<caption class="sr-only">{t("table_caption", lang)}</caption>'
        f'<thead><tr><th scope="col">{t("position", lang)}</th><th scope="col">{t("country", lang)}</th>'
        f'<th scope="col" class="population-column">{t("population", lang)}</th>'
        f'<th scope="col">{title}</th><th scope="col" class="secondary-column">{comparison_title}</th>'
        f'<th scope="col" class="secondary-column">{t("retention", lang)}</th>'
        f'<th scope="col">{t("movement", lang)}</th></tr></thead><tbody>'
        + "".join(rows) + '</tbody></table></div>'
    )

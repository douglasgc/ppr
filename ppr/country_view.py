"""Country analysis and on-demand history, shared by the tab and deep links."""

from html import escape

import pandas as pd
import requests
import streamlit as st

from .aggregation import CHINA_COMPONENTS
from .charts import history_chart
from .data import WorldBankDataLoader
from .history import calculate_history
from .i18n import t
from .navigation import country_url
from .presentation import (
    CHINA_LABELS,
    TAIWAN_REFERENCE,
    change,
    money,
    number,
    percent,
    prepare_ranking,
    sort_options,
)


@st.cache_data(ttl=3600, show_spinner=False)
def load_history(code: str, end_year: int, refresh: bool = False) -> pd.DataFrame:
    codes = CHINA_COMPONENTS if code == "CHN_AGG" else (code,)
    return WorldBankDataLoader().fetch_history(codes, 1960, end_year, refresh=refresh)


def analysis_link(label: str, code: str | None, context: dict) -> None:
    url = escape(country_url(code, **context), quote=True)
    st.html(f'<a class="analysis-button" href="{url}" target="_self">{escape(label)}</a>')


def render_history(code: str, year: int, alpha: float, lang: str, refresh: bool = False) -> None:
    def text(key, **values):
        return t(key, lang, **values)

    st.markdown(f"### {text('history_title')}")
    start, end = max(1960, year - 25), year
    if year > 1960:
        start, end = st.slider(text("history_period"), 1960, year, (start, year), key=f"history_period_{code}_{year}")
    mode = st.radio(text("history_measure"), ["total", "per_capita"], horizontal=True,
                     format_func=lambda value: text("history_total" if value == "total" else "history_per_capita"),
                     key="history_measure")
    retry = st.button(text("history_retry"), key="history_retry")
    if refresh or retry:
        load_history.clear()
    try:
        with st.spinner(text("history_loading")):
            history_raw = load_history(code, year, refresh=refresh or retry)
            history = calculate_history(history_raw, code, alpha)
    except (ValueError, OSError, requests.RequestException):
        st.warning(text("history_error"))
        return
    period = history.loc[history["year"].between(start, end)]
    per_capita = mode == "per_capita"
    metric = "ppr_per_capita" if per_capita else "ppr"
    gdp_metric = "gdp_per_capita" if per_capita else "gdp"
    if period.empty or not period[[metric, gdp_metric]].notna().any().any():
        st.info(text("history_empty"))
    else:
        st.plotly_chart(history_chart(period, per_capita, lang), width="stretch",
                        config={"displaylogo": False}, key="history_chart")
    st.caption(text("history_note", alpha=f"{alpha:g}"))
    st.caption(text("history_coverage", valid=int(period[metric].notna().sum()), total=len(period)))
    export = history.rename(columns={"gastos_governo": "government_consumption", "populacao": "population",
                                      "retencao_privada_pct": "private_retention_pct"})
    st.download_button(text("history_download"), export.to_csv(index=False).encode("utf-8-sig"),
                        file_name=f"history_{code}_1960_{year}_alpha_{alpha:g}.csv", mime="text/csv")
    with st.expander(text("history_data")):
        st.dataframe(export.loc[export["year"].between(start, end)], hide_index=True, width="stretch")


def render_country(data: pd.DataFrame, code: str, year: int, alpha: float, lang: str,
                   context: dict, *, with_history: bool = False, refresh: bool = False) -> None:
    def text(key, **values):
        return t(key, lang, **values)

    details = prepare_ranking(data, next(iter(sort_options(lang))), lang)
    matching = details.loc[details["country_code"] == code]
    if matching.empty:
        st.warning(text("country_unavailable"))
        if code == "TWN":
            st.info(text("taiwan_context"))
            st.link_button(text("taiwan_source"), TAIWAN_REFERENCE)
        return
    row = matching.iloc[0]
    st.html(f'<div class="country-heading">{row["bandeira"]} {escape(row["nome"])}</div>')
    st.caption(text("population_note", count=number(row["populacao"], lang=lang)))
    st.caption(text("country_rank", ppr=int(row["rank_ppr_per_capita"]), count=len(data),
                    gdp=int(row["rank_gdp_per_capita"]), change=change(row["dif_ranking"], lang)))
    if code in CHINA_LABELS:
        st.info(text("aggregate_note" if code == "CHN_AGG" else "china_context"))
    original, discount, remaining = st.columns(3)
    original.metric(text("gdp_pc"), money(row["gdp_per_capita"], 2, lang))
    discount.metric(text("discount_pc"), money(row["gdp_per_capita"] - row["ppr_per_capita"], 2, lang))
    remaining.metric(text("result_pc"), money(row["ppr_per_capita"], 2, lang))
    st.html('<div class="explanation">' + text("explanation", retained=money(row["retencao_privada_pct"], 2, lang),
            share=percent(row["peso_governo_pct"], lang), alpha=f"{alpha:g}") + '</div>')
    if row["ppr"] < 0:
        st.warning(text("negative"))
    if with_history:
        render_history(code, year, alpha, lang, refresh)
    else:
        analysis_link(text("open_analysis"), code, context)
    st.markdown(f"#### {text('scenarios')}")
    st.dataframe(pd.DataFrame({
        text("scenario_column"): [text("none"), text("single"), text("double")],
        text("result_column"): [money((row["gdp"] - weight * row["gastos_governo"]) / row["populacao"], 2, lang)
                                for weight in (0, 1, 2)],
        text("retention_column"): [percent((1 - weight * row["gastos_governo"] / row["gdp"]) * 100, lang)
                                   for weight in (0, 1, 2)],
    }), hide_index=True, width="stretch")
    with st.expander(text("totals")):
        st.table(pd.DataFrame({text("indicator"): [text(key) for key in ("population", "gdp_total", "government", "ppr_total")],
                               text("value"): [number(row["populacao"], lang=lang), money(row["gdp"], lang=lang),
                                               money(row["gastos_governo"], lang=lang), money(row["ppr"], lang=lang)]}))

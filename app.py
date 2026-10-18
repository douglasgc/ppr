"""Run with: streamlit run app.py"""

import json
from datetime import date
from html import escape
from math import ceil
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

from ppr import PPRConfig, RothbardEngine, WorldBankDataLoader
from ppr.aggregation import aggregate_china
from ppr.charts import comparison_chart, world_map
from ppr.dataset import FIELD_MAP, build_dataset
from ppr.i18n import ABOUT, t
from ppr.presentation import (
    CHINA_LABELS,
    change,
    china_exclusion_note,
    leaderboard_html,
    money,
    number,
    percent,
    podium_html,
    prepare_ranking,
    search_ranking,
    sort_options,
)


@st.cache_data(ttl=3600, show_spinner=False)
def load_data(year: int) -> pd.DataFrame:
    return WorldBankDataLoader().fetch(year)


st.set_page_config(page_title="PPR · World ranking", page_icon="🌎", layout="wide")
style = (Path(__file__).parent / "assets/dashboard.css").read_text(encoding="utf-8")
st.html(f"<style>{style}</style>")
lang = st.sidebar.selectbox("Idioma / Language", ["pt", "en"], key="language",
                            format_func=lambda code: "Português" if code == "pt" else "English")


def text(key: str, **values) -> str:
    return t(key, lang, **values)


with st.sidebar:
    st.markdown(f"### {text('configure')}")
    year = st.number_input(text("year"), min_value=1960, max_value=date.today().year, value=2023, step=1, key="data_year")
    scenario_keys = ["double", "single", "none", "custom"]
    gdp_label = "PIB" if lang == "pt" else "GDP"
    scenario_key = st.radio(text("scenario"), scenario_keys, format_func=text, key="scenario",
                        captions=[f"PPR = {gdp_label} − 2 × G", f"PPR = {gdp_label} − G", text("none_help"), text("custom_help")])
    scenario = text(scenario_key)
    scenario_index = scenario_keys.index(scenario_key)
    alpha = [2.0, 1.0, 0.0, 2.0][scenario_index]
    if scenario_index == 3:
        alpha = st.slider(text("weight"), 0.0, 2.0, 2.0, 0.05, key="custom_alpha")
    st.caption(text("g_warning"))
    china_mode = st.selectbox(text("china_mode"), ["separate", "combined"], key="china_mode",
                              format_func=lambda mode: text("china_separate" if mode == "separate" else "china_combined"))
    with st.expander(text("options")):
        min_population = st.number_input(text("min_pop"), min_value=0, value=100_000, step=10_000, key="min_population")
        refresh = st.button(text("refresh"), width="stretch")
        st.caption(text("cache"))

st.title(text("title"))
st.html(f'<p class="hero-copy">{text("intro")}</p>')
st.html(f'<div class="context-pills"><span>{text("year_chip", year=year)}</span><span>{text("source")}</span>'
        f'<span>{text("usd")}</span><span>{text("deduction", alpha=f"{alpha:g}")}</span></div>')

try:
    with st.spinner(text("loading")):
        if refresh:
            WorldBankDataLoader().fetch(int(year), refresh=True)
            load_data.clear()
        raw = load_data(int(year))
        prepared, aggregation = aggregate_china(raw, china_mode)
        config = PPRConfig(int(year), alpha, int(min_population))
        data = RothbardEngine().calculate(prepared, config)
except (ValueError, OSError, requests.RequestException) as exc:
    st.error(text("load_error", error=str(exc)))
    st.info(text("retry"))
    st.stop()

if china_mode == "combined":
    if aggregation["applied"]:
        st.caption(text("aggregate_note"))
    else:
        field_labels = {"gdp": gdp_label, "gastos_governo": text("government_field"),
                        "populacao": text("population"), "series": text("series")}
        details_missing = "; ".join(f"{code}: {', '.join(field_labels.get(field, field) for field in fields)}"
                                    for code, fields in aggregation["missing"].items())
        st.warning(text("aggregate_missing", details=details_missing))
if data.empty:
    st.warning(text("empty"))
    st.stop()

ranking_tab, map_tab, country_tab, about_tab = st.tabs([text(key) for key in ("ranking", "map", "country_tab", "about")])
with ranking_tab:
    st.caption(text("cohort", count=len(data), scenario=scenario))
    search_col, sort_col, size_col, filter_col = st.columns([1.2, 1.1, .65, .65])
    query = search_col.text_input(text("search"), placeholder=text("search_hint"), key="country_search")
    options = sort_options(lang)
    metric_labels = {metric: label for label, (metric, _) in options.items()}
    selected_metric = sort_col.selectbox(text("sort"), list(metric_labels), key="sort_order", format_func=metric_labels.get)
    sort_label = metric_labels[selected_metric]
    ranked = prepare_ranking(data, sort_label, lang)
    country_names = ranked.set_index("country_code")["nome"].to_dict()
    with filter_col:
        st.caption(text("filter"))
        with st.popover(text("select_countries"), width="stretch"):
            selected = st.multiselect(text("show_countries"), sorted(country_names, key=country_names.get),
                                      format_func=country_names.get, help=text("filter_help"), key="country_filter")
    visible = search_ranking(ranked, query, selected)
    page_size = size_col.selectbox(text("results"), [0, 15, 30, 50, 100], key="page_size",
                                   format_func=lambda size: text("all", count=len(visible)) if size == 0 else str(size))
    china_focus = (bool(query.strip() or selected) and visible["country_code"].isin(CHINA_LABELS).any()) or (
        "china" in query.casefold() or query.strip().upper() == "CHN"
    )
    if china_focus:
        st.info(text("aggregate_note" if aggregation["applied"] else "china_context"))
        if not aggregation["applied"]:
            exclusion = china_exclusion_note(raw, ranked, int(year), int(min_population), lang)
            if exclusion:
                st.warning(exclusion)
    if not query.strip() and not selected:
        st.html(podium_html(ranked, sort_label, lang))
    if visible.empty:
        st.info(text("no_matches"))
    else:
        size = page_size or len(visible)
        pages = max(1, ceil(len(visible) / size))
        signature = (query, tuple(selected), sort_label, page_size, int(year), alpha, int(min_population), lang, china_mode)
        if st.session_state.get("ranking_signature") != signature:
            st.session_state["ranking_page"] = 1
            st.session_state["ranking_signature"] = signature
        page = st.session_state.get("ranking_page", 1)
        start = (page - 1) * size
        st.markdown(text("range", start=start + 1, end=min(start + size, len(visible)), count=len(visible)))
        st.html(leaderboard_html(visible.iloc[start:start + size], sort_label, lang))
        if pages > 1:
            st.selectbox(text("page"), range(1, pages + 1), key="ranking_page",
                         format_func=lambda value: text("page_of", page=value, pages=pages))
        st.caption(text("rank_note"))
        if not china_focus and visible["country_code"].isin(CHINA_LABELS).any():
            with st.expander(text("china_question")):
                st.markdown(text("aggregate_note" if aggregation["applied"] else "china_context"))
                if not aggregation["applied"]:
                    exclusion = china_exclusion_note(raw, ranked, int(year), int(min_population), lang)
                    if exclusion:
                        st.warning(exclusion)
        with st.expander(text("comparison")):
            st.altair_chart(comparison_chart(visible, lang), width="stretch")
            st.caption(text("comparison_note"))
        with st.expander(text("export")):
            payload = build_dataset(raw, config, lang=lang, china_mode=china_mode,
                                    countries=visible["country_code"].tolist(), sort_by=FIELD_MAP[options[sort_label][0]])
            export = pd.DataFrame(payload["records"])
            st.caption(text("export_note"))
            left, right = st.columns(2)
            left.download_button(text("csv"), export.to_csv(index=False, sep=";" if lang == "pt" else ",",
                                 decimal="," if lang == "pt" else ".").encode("utf-8-sig"),
                                 file_name=f"ranking_{year}_alpha_{alpha:g}.csv", mime="text/csv", width="stretch")
            right.download_button(text("json"), json.dumps(payload, ensure_ascii=False, allow_nan=False),
                                  file_name=f"ranking_{year}_alpha_{alpha:g}.json", mime="application/json", width="stretch")

with map_tab:
    st.subheader(text("map_title"))
    st.caption(text("map_note", criterion=sort_label, count=len(ranked)))
    st.plotly_chart(world_map(ranked, lang), width="stretch", config={"displaylogo": False}, key="world_map")
    st.caption(text("map_scope"))
    if aggregation["applied"]:
        st.info(text("aggregate_note"))

with country_tab:
    st.subheader(text("country_intro"))
    details = prepare_ranking(data, next(iter(options)), lang)
    labels = details.set_index("country_code")["nome"].to_dict()
    codes = sorted(labels, key=labels.get)
    code = st.selectbox(text("choose_country"), codes, index=codes.index("BRA") if "BRA" in codes else 0,
                        format_func=labels.get, key="country_detail")
    row = details.set_index("country_code").loc[code]
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
    st.markdown(f"#### {text('scenarios')}")
    scenarios = pd.DataFrame({
        text("scenario_column"): [text("none"), text("single"), text("double")],
        text("result_column"): [money((row["gdp"] - weight * row["gastos_governo"]) / row["populacao"], 2, lang)
                                for weight in (0, 1, 2)],
        text("retention_column"): [percent((1 - weight * row["gastos_governo"] / row["gdp"]) * 100, lang)
                                   for weight in (0, 1, 2)],
    })
    st.dataframe(scenarios, hide_index=True, width="stretch")
    with st.expander(text("totals")):
        st.table(pd.DataFrame({text("indicator"): [text(key) for key in ("population", "gdp_total", "government", "ppr_total")],
                               text("value"): [number(row["populacao"], lang=lang), money(row["gdp"], lang=lang),
                                               money(row["gastos_governo"], lang=lang), money(row["ppr"], lang=lang)]}))

with about_tab:
    st.subheader(text("about_title"))
    st.markdown(ABOUT[lang])
    st.markdown(text("coverage", year=year, count=len(data), raw=len(raw), population=number(min_population, lang=lang)))
    with st.expander(text("china_question")):
        st.markdown(text("china_context"))
        st.markdown(text("aggregate_note"))
    with st.expander(text("technical")):
        full = build_dataset(raw, config, lang=lang, china_mode=china_mode)
        st.caption(text("technical_note"))
        st.dataframe(pd.DataFrame(full["records"]), hide_index=True, width="stretch")
        st.download_button(text("json"), json.dumps(full, ensure_ascii=False, allow_nan=False),
                           file_name=f"full_ppr_{year}_alpha_{alpha:g}.json", mime="application/json")
    with st.expander(text("machine")):
        st.markdown(text("machine_help"))
    st.link_button(text("source_link"), "https://data.worldbank.org/indicator/NE.CON.GOVT.CD")

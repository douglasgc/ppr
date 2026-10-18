"""Run with: streamlit run app.py"""

import json
from datetime import date
from math import ceil
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

from ppr import PPRConfig, RothbardEngine, WorldBankDataLoader
from ppr.aggregation import aggregate_china
from ppr.charts import comparison_chart, world_map
from ppr.country_view import analysis_link, load_history, render_country
from ppr.dataset import FIELD_MAP, build_dataset
from ppr.i18n import ABOUT, t
from ppr.navigation import requested_country, route_defaults
from ppr.presentation import (
    CHINA_LABELS,
    TAIWAN_REFERENCE,
    china_exclusion_note,
    is_taiwan_query,
    leaderboard_html,
    number,
    podium_html,
    prepare_ranking,
    search_ranking,
    sort_options,
    taiwan_availability_note,
)


@st.cache_data(ttl=3600, show_spinner=False)
def load_data(year: int) -> pd.DataFrame:
    return WorldBankDataLoader().fetch(year)


st.set_page_config(page_title="PPR · World ranking", page_icon="🌎", layout="wide")
style = (Path(__file__).parent / "assets/dashboard.css").read_text(encoding="utf-8")
st.html(f"<style>{style}</style>")
parameters = st.query_params.to_dict()
route_signature = tuple(sorted(parameters.items()))
if st.session_state.get("applied_route") != route_signature:
    for key, value in route_defaults(parameters).items():
        if parameters or key not in st.session_state:
            st.session_state[key] = value
    st.session_state["applied_route"] = route_signature
lang = st.sidebar.selectbox("Idioma / Language", ["pt", "en"], key="language",
                            format_func=lambda code: "Português" if code == "pt" else "English")


def text(key: str, **values) -> str:
    return t(key, lang, **values)


with st.sidebar:
    st.markdown(f"### {text('configure')}")
    year = st.number_input(text("year"), min_value=1960, max_value=date.today().year, step=1, key="data_year")
    scenario_keys = ["double", "single", "none", "custom"]
    gdp_label = "PIB" if lang == "pt" else "GDP"
    scenario_key = st.radio(text("scenario"), scenario_keys, format_func=text, key="scenario",
                        captions=[f"PPR = {gdp_label} − 2 × G", f"PPR = {gdp_label} − G", text("none_help"), text("custom_help")])
    scenario = text(scenario_key)
    scenario_index = scenario_keys.index(scenario_key)
    alpha = [2.0, 1.0, 0.0, 2.0][scenario_index]
    if scenario_index == 3:
        alpha = st.slider(text("weight"), 0.0, 2.0, step=0.05, key="custom_alpha")
    st.caption(text("g_warning"))
    china_mode = st.selectbox(text("china_mode"), ["separate", "combined"], key="china_mode",
                              format_func=lambda mode: text("china_separate" if mode == "separate" else "china_combined"))
    with st.expander(text("options")):
        min_population = st.number_input(text("min_pop"), min_value=0, step=10_000, key="min_population")
        refresh = st.button(text("refresh"), width="stretch")
        st.caption(text("cache"))

route_country = requested_country(parameters)
st.title(text("country_tab") if route_country else text("title"))
if not route_country:
    st.html(f'<p class="hero-copy">{text("intro")}</p>')
st.html(f'<div class="context-pills"><span>{text("year_chip", year=year)}</span><span>{text("source")}</span>'
        f'<span>{text("usd")}</span><span>{text("deduction", alpha=f"{alpha:g}")}</span></div>')

try:
    with st.spinner(text("loading")):
        if refresh:
            WorldBankDataLoader().fetch(int(year), refresh=True)
            load_data.clear()
            load_history.clear()
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

def link_context() -> dict:
    return {"year": int(year), "alpha": alpha, "lang": lang, "min_population": int(min_population),
            "china_mode": china_mode, "sort": st.session_state.get("sort_order", route_defaults(parameters)["sort_order"]),
            "q": st.session_state.get("country_search", parameters.get("q", ""))}


if route_country:
    analysis_link(text("back_ranking"), None, link_context())
    render_country(data, route_country, int(year), alpha, lang, link_context(), with_history=True, refresh=refresh)
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
    if is_taiwan_query(query) or "TWN" in selected:
        st.info(text("taiwan_context"))
        note = taiwan_availability_note(raw, ranked, lang)
        if note:
            st.warning(note)
        st.link_button(text("taiwan_source"), TAIWAN_REFERENCE)
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
        st.html(podium_html(ranked, sort_label, lang, link_context()))
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
        st.caption(text("click_country"))
        st.html(leaderboard_html(visible.iloc[start:start + size], sort_label, lang, link_context()))
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
    st.caption(text("map_click"))
    map_event = st.plotly_chart(world_map(ranked, lang), width="stretch", config={"displaylogo": False},
                                key="world_map", on_select="rerun", selection_mode="points")
    if map_event.selection.points:
        point = map_event.selection.points[-1]
        point_data = point.get("customdata", [])
        clicked = point_data[5] if len(point_data) > 5 else point.get("location")
        if clicked in set(ranked["country_code"]):
            st.query_params.from_dict({**link_context(), "country": clicked})
            st.rerun()
    st.caption(text("map_scope"))
    if not ranked["country_code"].eq("TWN").any():
        st.caption(taiwan_availability_note(raw, ranked, lang))
    if aggregation["applied"]:
        st.info(text("aggregate_note"))

with country_tab:
    st.subheader(text("country_intro"))
    details = prepare_ranking(data, next(iter(options)), lang)
    labels = details.set_index("country_code")["nome"].to_dict()
    codes = sorted(labels, key=labels.get)
    code = st.selectbox(text("choose_country"), codes, index=codes.index("BRA") if "BRA" in codes else 0,
                        format_func=labels.get, key="country_detail")
    render_country(data, code, int(year), alpha, lang, link_context())

with about_tab:
    st.subheader(text("about_title"))
    st.markdown(ABOUT[lang])
    st.markdown(text("coverage", year=year, count=len(data), raw=len(raw), population=number(min_population, lang=lang)))
    with st.expander(text("china_question")):
        st.markdown(text("china_context"))
        st.markdown(text("aggregate_note"))
        st.markdown(text("taiwan_context"))
        st.link_button(text("taiwan_source"), TAIWAN_REFERENCE)
    with st.expander(text("technical")):
        full = build_dataset(raw, config, lang=lang, china_mode=china_mode)
        st.caption(text("technical_note"))
        st.dataframe(pd.DataFrame(full["records"]), hide_index=True, width="stretch")
        st.download_button(text("json"), json.dumps(full, ensure_ascii=False, allow_nan=False),
                           file_name=f"full_ppr_{year}_alpha_{alpha:g}.json", mime="application/json")
    with st.expander(text("machine")):
        st.markdown(text("machine_help"))
    st.link_button(text("source_link"), "https://data.worldbank.org/indicator/NE.CON.GOVT.CD")

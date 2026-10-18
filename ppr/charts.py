"""Charts consume the same ranked DataFrame as the leaderboard."""

import altair as alt
import pandas as pd
import plotly.graph_objects as go

from .aggregation import CHINA_AGGREGATE, CHINA_COMPONENTS
from .i18n import t
from .presentation import money, number, percent


def comparison_chart(data: pd.DataFrame, lang: str = "pt") -> alt.Chart:
    country, gdp, ppr, indicator, value = (t(key, lang) for key in ("country", "gdp_pc", "ppr_pc", "indicator", "value"))
    population = t("population", lang)
    chart_data = data.head(10).rename(columns={"nome": country, "gdp_per_capita": gdp,
                                             "ppr_per_capita": ppr, "populacao": population})
    order = chart_data[country].tolist()
    long = chart_data.melt(id_vars=[country, population], value_vars=[gdp, ppr], var_name=indicator, value_name=value)
    return alt.Chart(long).mark_bar(cornerRadiusEnd=3).encode(
        y=alt.Y(f"{country}:N", sort=order, title=None, axis=alt.Axis(labelLimit=180)),
        x=alt.X(f"{value}:Q", title=f"{t('usd', lang)} / {t('population', lang).lower()}", axis=alt.Axis(format="~s")),
        yOffset=alt.YOffset(f"{indicator}:N", sort=[gdp, ppr]),
        color=alt.Color(f"{indicator}:N", scale=alt.Scale(domain=[gdp, ppr], range=["#cbd5e1", "#0f766e"]),
                        legend=alt.Legend(orient="top", title=None)),
        tooltip=[f"{country}:N", f"{indicator}:N", alt.Tooltip(f"{value}:Q", format=",.2f"),
                 alt.Tooltip(f"{population}:Q", format=",.0f")],
    ).properties(height=max(150, len(order) * 48)).configure_view(stroke=None)


def world_map(data: pd.DataFrame, lang: str = "pt") -> go.Figure:
    mapped = []
    for _, row in data.iterrows():
        locations = CHINA_COMPONENTS if row["country_code"] == CHINA_AGGREGATE else [row["country_code"]]
        for code in locations:
            mapped.append({"code": code, "source_code": row["country_code"], "rank": int(row["posicao"]), "name": row["nome"],
                           "ppr": money(row["ppr_per_capita"], lang=lang),
                           "gdp": money(row["gdp_per_capita"], lang=lang),
                           "population": number(row["populacao"], lang=lang),
                           "retention": percent(row["retencao_privada_pct"], lang)})
    frame = pd.DataFrame(mapped)
    figure = go.Figure(go.Choropleth(
        locations=frame["code"], locationmode="ISO-3", z=frame["rank"],
        zmin=1, zmax=max(2, int(frame["rank"].max())),
        colorscale=[[0, "#0f766e"], [0.5, "#f3d99f"], [1, "#bd5263"]],
        marker_line_color="#ffffff", marker_line_width=0.5,
        colorbar={"title": t("map_rank", lang), "tickformat": "d", "thickness": 14},
        customdata=frame[["name", "ppr", "gdp", "retention", "population", "source_code"]],
        hovertemplate=(f"<b>%{{customdata[0]}}</b><br>{t('map_rank', lang)}: #%{{z:.0f}}"
                       f"<br>{t('ppr_pc', lang)}: %{{customdata[1]}}<br>{t('gdp_pc', lang)}: %{{customdata[2]}}"
                       f"<br>{t('retention', lang)}: %{{customdata[3]}}"
                       f"<br>{t('population', lang)}: %{{customdata[4]}}<extra></extra>"),
    ))
    figure.update_geos(projection_type="natural earth", projection_rotation_lon=0,
                       projection_rotation_lat=0, center={"lon": 0, "lat": 0},
                       showframe=False, showcoastlines=False,
                       showland=True, landcolor="#e2e8f0", showcountries=True, countrycolor="white",
                       bgcolor="rgba(0,0,0,0)")
    figure.update_layout(height=550, clickmode="event+select", margin={"l": 0, "r": 0, "t": 0, "b": 0},
                         paper_bgcolor="rgba(0,0,0,0)", font={"family": "sans-serif", "color": "#172b41"})
    return figure


def history_chart(data: pd.DataFrame, per_capita: bool = False, lang: str = "pt") -> go.Figure:
    frame = data.sort_values("year")
    suffix = "_per_capita" if per_capita else ""
    figure = go.Figure()
    for metric, color in (("gdp", "#64748b"), ("ppr", "#0f766e")):
        label = t(f"{metric}_pc" if per_capita else f"{metric}_total", lang)
        values = frame[metric + suffix]
        custom = [[money(value, 2, lang) if pd.notna(value) else "—",
                   number(population, lang=lang) if pd.notna(population) else "—"]
                  for value, population in zip(values, frame["populacao"], strict=True)]
        figure.add_trace(go.Scatter(
            x=frame["year"].tolist(), y=values.where(values.notna(), None).tolist(),
            mode="lines+markers", name=label, line={"color": color, "width": 3},
            marker={"size": 5}, connectgaps=False, customdata=custom,
            hovertemplate=(f"<b>{label}</b><br>%{{x:.0f}}: %{{customdata[0]}}"
                           f"<br>{t('population', lang)}: %{{customdata[1]}}<extra></extra>"),
        ))
    figure.update_layout(height=430, hovermode="x unified", legend={"orientation": "h", "y": 1.12},
                         margin={"l": 0, "r": 10, "t": 35, "b": 0},
                         xaxis={"title": t("year", lang), "tickformat": "d"},
                         yaxis={"title": t("usd_per_person" if per_capita else "usd", lang), "tickformat": "~s"},
                         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return figure

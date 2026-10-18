# PPR · private product and government consumption study

[Português](README.md) · [LLM guide](llms.txt)

**Live study: [openppr.streamlit.app](https://openppr.streamlit.app/)**

A World Bank pipeline, interactive ranking, world map and HTTP/MCP access.

## Rothbard’s thesis, briefly

Rothbard argues that valuing government services at cost does not demonstrate their
market value: tax-financed spending does not reveal consumer preferences in the same
way as voluntary private transactions. He separates private product and deducts
resources absorbed by government.

In *America’s Great Depression*, he removes income originating in government and
government enterprises from national product, then considers expenditure or receipts,
whichever is higher, with adjustments by level of government. **The historical method
is not universally equivalent to GDP − 2G.**

This study implements a **simplified simulation inspired by that premise**:

```text
PPR = GDP − alpha × G
alpha = 0: GDP     alpha = 1: GDP − G     alpha = 2: GDP − 2G
```

Here G is **government final consumption, not total public spending**. Transfers,
public investment and the historical fiscal adjustments are not fully represented.
The weight compares assumptions; it does not estimate a scientifically “correct”
deduction. PPR is not official welfare, disposable income or proof that public
services have no value. Lack of market prices does not itself establish zero social benefit.

Sources:
- [Rothbard, *America’s Great Depression*, national-product appendix](https://mises.org/online-book/americas-great-depression/appendix-government-and-national-product-1929-1932).
- [Rothbard, *Power and Market*, national-product statistics appendix](https://mises.org/online-book/man-economy-and-state-power-and-market/5-binary-intervention-government-expenditures/appendix-role-government-expenditures-national-product-statistics).
- [Critical discussion: “GNP, PPR, and the Standard of Living”](https://mises.org/online-book/review-austrian-economics/gnp-ppr-and-standard-living).

## Run

Python 3.11+ and [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run streamlit run app.py
```

Open http://localhost:8501. Select **English** in the sidebar. Alternatively, create
a virtual environment, `pip install -e .`, then `streamlit run app.py`.

- All results are shown by default; optional 15/30/50/100-row pages.
- Population is always included in rankings, highlights, country details, map hover and exported/API/MCP records.
  Combined China uses the sum of all three populations; missing raw values remain null.
- Localized names, numbers, explanations, exports and charts in PT/EN.
- Sort by PPR/person, GDP/person, total PPR, retained share or places gained.
- Search by PT/EN name or code without reranking the full cohort.
- World map colors follow the selected ranking, with gray for no result. List search
  does not filter the map. Plotly’s basemap requires internet; small territories may not be visible.
- Country view explains GDP − deduction = PPR and compares the three scenarios.
- Click any country name in the ranking or highlights to open a shareable analysis
  URL, preserving year, weight, language and China coverage.
- Historical GDP/PPR chart: country totals or per-person values, adjustable period,
  yearly population and CSV download. Only three historical indicators are fetched
  for the selected economy, with caching; world rankings are not downloaded year by year.
- Full JSON includes every matching row, all indicators, raw inputs, exclusions and metadata.

Rank changes compare GDP and PPR in the **same year**, not change over time. Ties use
1,1,3; ranks are based on unrounded values. Minimum population changes the cohort;
search and country selection only filter the view.

History uses **current USD**, so changes include inflation and exchange-rate effects,
not necessarily real growth. The same alpha applies throughout. GDP can be shown
when G is missing, while PPR remains unknown. Per-person values require valid annual
population. Gaps are not interpolated or replaced with zero. Combined China requires
all three components for each annual total; partial aggregates are never fabricated.

Direct analysis example: [Brazil](https://openppr.streamlit.app/?country=BRA&year=2023&alpha=2&lang=en).

### China coverage

Choose **Separate series** (Mainland China, Hong Kong and Macao) or **Combined China**.
Hong Kong and Macao are special administrative regions, not independent countries.
Combined China sums GDP, government consumption and population **before** computing
per-person values; it never averages per-capita figures. It replaces all three rows
with synthetic `CHN_AGG`, not an official World Bank series. All essential data for
all three economies in the same year are required, before population filtering.
If unavailable, a warning explains why and only separate available series remain;
no partial aggregate is fabricated. Optional fields remain null if any component
is missing. Trade totals do not eliminate internal flows. The combined map gives
the three geographic components the same synthetic rank.

### What about Taiwan?

**Taiwan is not included in this study’s Combined China**, which is only `CHN + HKG + MAC`.
The World Bank [explains that WDI does not list Taiwan as a separate series](https://datahelpdesk.worldbank.org/knowledgebase/articles/114933-where-are-your-data-on-taiwan).
[CHN’s coverage note](https://databank.worldbank.org/metadataglossary/world-development-indicators/country/CHN)
also excludes Hong Kong, Macao and Taiwan unless otherwise stated. Mainland China
is not used as a substitute; missing Taiwan data do not mean zero GDP, PPR or population.
Searching `Taiwan`, `Formosa` or `TWN` explains this coverage gap.

Including Taiwan requires harmonizing GDP, government final consumption, population,
years and currency with another official source such as DGBAS; that integration is
not yet implemented. HTTP/MCP/JSON metadata disclose the limitation and whether TWN
actually appears in the input data. This is not a sovereignty classification.

## HTTP + mini MCP

Run separately:

```bash
uv run ppr-serve
```

Base URL: **http://127.0.0.1:8000**.

| Route | Purpose |
| --- | --- |
| `/api/data` | Complete `metadata`, `records`, `excluded`, `raw_records` |
| `/api/metadata` | Field dictionary, indicators, units and methodology |
| `/api/countries/BRA` | All country fields, raw inputs and exclusions; full-cohort ranks preserved |
| `/llms.txt` | Agent reading instructions |
| `/docs`, `/openapi.json` | Interactive documentation and OpenAPI |
| `/mcp` | Real MCP **Streamable HTTP**, official Python SDK |

```bash
curl 'http://127.0.0.1:8000/api/data?year=2023&alpha=2&min_population=0&lang=en' -o full_study.json
curl 'http://127.0.0.1:8000/api/data?china_mode=combined&countries=CHN_AGG'
```

Parameters: `year`, `alpha` (0–2), `min_population`, `lang` (`pt`/`en`), `china_mode`
(`separate`/`combined`), `countries` (comma-separated), `sort_by` (`ppr_per_capita`,
`gdp_per_capita`, `ppr`, `private_retention_pct`, `rank_change`). Country filtering
does not rerank; `custom_country_codes` in the legacy Python client does define its cohort.

Point an MCP client at `http://127.0.0.1:8000/mcp`, using Streamable HTTP.
Tools: `get_metadata`, `get_dataset`, `get_country`; resource: `ppr://metadata`.
Tool arguments mirror HTTP parameters, except `countries` is a list. The SDK handles
`initialize`, `tools/list` and `tools/call` — not a renamed plain JSON endpoint.

### Complete-data contract and safety

- No top-N cap, pagination or silent response truncation.
- `record_count == len(records)` and `raw_record_count == len(raw_records)`.
- `complete=true`, `truncated=false` describe the query response, **not** universal source coverage.
- Numbers remain numeric; missing values are `null`. Stable field names are English.
- `generated_at` means response generation, **not** source publication or refresh time.
- LLM/client context budgets may still truncate model-visible output. Download files
  or query individual economies; never infer unseen rows.
- Local-only, read-only tools; a cache miss may download source data. No execution,
  write or remote refresh tools; no automatic calls to an external LLM.
- Optional `PPR_API_TOKEN` enables Bearer authentication on every route.
  Do not publish tokens. Remote use requires an authenticated TLS proxy and rate limits;
  the command only binds loopback addresses.

## Python and CLI

```bash
uv run ppr --year 2023 --alpha 2 --top 20
uv run ppr --countries BRA USA ARG --alpha 1 --export exports/ppr.csv
uv run ppr --year 2023 --refresh --export exports/ppr.json
```

CLI export is the legacy calculated-record format, not the complete metadata/raw-data
envelope. Use the dashboard or HTTP/MCP for that. `--cache-dir` changes local storage.

```python
from ppr import PPRConfig, RothbardPPRClient
from ppr.dataset import build_dataset

client = RothbardPPRClient(PPRConfig(year=2023, alpha_g=2))
print(client.get_country("BRA"))
client.set_config(alpha_g=1)
client.export("exports/ppr.json")
# With your own raw DataFrame:
# full = build_dataset(df, PPRConfig(year=2023), lang="en", china_mode="combined")
```

## Data limitations

Current USD, no inflation or PPP adjustment. GDP and population must be positive;
government consumption nonnegative; all essential inputs finite. Negative PPR is retained.
Optional C/I/X/M gaps do not exclude an economy. `gpp = gdp - government_consumption`;
`gpp_components = C + I + X - M`; `accounting_residual` preserves discrepancies.
Capital formation includes inventories and need not be private. No year backfilling.
Source regional aggregates are excluded. Disk cache `.cache/ppr/` **does not expire**;
explicit refresh is needed for revisions. Indicator codes and definitions: `/api/metadata`.

## Tests and architecture

```text
World Bank → data → aggregation → engine → dataset → dashboard / HTTP / MCP
                                      ↘ legacy Python client / CLI
```

```bash
uv run python -m unittest discover -s tests -v
```

Offline tests use fictional data for calculation, aggregation, localization, UI,
map, full data contract, HTTP and MCP. No database or external LLM service is required.

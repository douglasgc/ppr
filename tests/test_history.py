import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pandas as pd

from ppr.charts import history_chart
from ppr.data import WorldBankDataLoader
from ppr.history import calculate_history
from ppr.navigation import country_url, requested_country, route_defaults
from ppr.presentation import leaderboard_html, prepare_ranking
from tests.test_ppr import sample_data
from tests.test_presentation import china_data


def historical_sample() -> pd.DataFrame:
    rows = []
    for year, gdp, government, population in ((2021, 1000, 200, 10), (2022, 1200, None, 12), (2023, 1400, 300, 14)):
        rows.append(dict(country_code="BRA", year=year, gdp=gdp, gastos_governo=government, populacao=population))
    return pd.DataFrame(rows)


class HistoryTests(unittest.TestCase):
    def test_formula_population_and_missing_government_gap(self):
        data = calculate_history(historical_sample(), "BRA", 2)
        self.assertEqual(data["year"].tolist(), [2021, 2022, 2023])
        self.assertEqual(data["populacao"].tolist(), [10, 12, 14])
        self.assertEqual(data.iloc[0]["ppr"], 600)
        self.assertEqual(data.iloc[2]["ppr_per_capita"], 800 / 14)
        self.assertEqual(data.iloc[1]["gdp"], 1200)
        self.assertTrue(pd.isna(data.iloc[1]["ppr"]))

    def test_alpha_changes_do_not_mutate_raw_series(self):
        raw = historical_sample()
        original = raw.copy(deep=True)
        self.assertEqual(calculate_history(raw, "BRA", 1).iloc[0]["ppr"], 800)
        self.assertEqual(calculate_history(raw, "BRA", 0).iloc[0]["ppr"], 1000)
        pd.testing.assert_frame_equal(raw, original)

    def test_china_uses_summed_levels_and_never_partial_totals(self):
        raw = pd.concat([china_data().assign(year=2022), china_data().assign(year=2023)], ignore_index=True)
        raw["populacao"] = [10, 100, 1000] * 2
        raw.loc[(raw["year"] == 2023) & (raw["country_code"] == "MAC"), "gastos_governo"] = float("nan")
        data = calculate_history(raw, "CHN_AGG")
        self.assertEqual(data.iloc[0]["gdp"], 3000)
        self.assertEqual(data.iloc[0]["populacao"], 1110)
        self.assertAlmostEqual(data.iloc[0]["ppr_per_capita"], 1800 / 1110)
        self.assertEqual(data.iloc[1]["gdp"], 3000)
        self.assertTrue(pd.isna(data.iloc[1]["ppr"]))

    def test_invalid_population_and_negative_ppr(self):
        raw = historical_sample()
        raw.loc[0, "populacao"] = 0
        raw.loc[2, "gastos_governo"] = 1000
        data = calculate_history(raw, "BRA")
        self.assertTrue(pd.isna(data.iloc[0]["gdp_per_capita"]))
        self.assertEqual(data.iloc[0]["ppr"], 600)
        self.assertEqual(data.iloc[2]["ppr"], -600)

    def test_duplicate_rows_and_missing_columns_raise(self):
        for frame in (pd.concat([historical_sample()] * 2), historical_sample().drop(columns=["populacao"])):
            with self.assertRaises(ValueError):
                calculate_history(frame, "BRA")

    def test_chart_does_not_connect_gaps_and_includes_population(self):
        data = calculate_history(historical_sample(), "BRA")
        chart = history_chart(data, lang="en")
        self.assertEqual([trace.name for trace in chart.data], ["Total GDP", "Total PPR"])
        self.assertTrue(all(trace.connectgaps is False for trace in chart.data))
        self.assertTrue(pd.isna(chart.data[1].y[1]))
        self.assertIn("Population", chart.data[0].hovertemplate)
        self.assertEqual(history_chart(data, True).data[0].y[0], 100)


class HistoryLoaderTests(unittest.TestCase):
    def test_downloads_three_indicators_for_year_range_and_caches(self):
        def records(endpoint, **params):
            self.assertIn("country/BRA/indicator/", endpoint)
            self.assertEqual(params["date"], "2021:2023")
            return [{"countryiso3code": "BRA", "date": str(year), "value": value}
                    for year, value in ((2021, 100), (2023, 200))]

        with tempfile.TemporaryDirectory() as directory:
            loader = WorldBankDataLoader(directory)
            with patch.object(loader, "_records", side_effect=records) as fetch:
                frame = loader.fetch_history(("bra",), 2021, 2023)
                self.assertEqual(fetch.call_count, 3)
                self.assertEqual(frame["year"].tolist(), [2021, 2022, 2023])
                self.assertTrue(pd.isna(frame.iloc[1]["gdp"]))
                loader.fetch_history(("BRA",), 2021, 2023)
                self.assertEqual(fetch.call_count, 3)
                loader.fetch_history(("BRA",), 2021, 2023, refresh=True)
                self.assertEqual(fetch.call_count, 6)

    def test_empty_years_and_regions_are_retained_as_missing_not_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            loader = WorldBankDataLoader(directory)
            with patch.object(loader, "_records", return_value=[]):
                frame = loader.fetch_history(("CHN", "HKG", "MAC"), 2022, 2023)
                self.assertEqual(len(frame), 6)
                self.assertTrue(frame["gdp"].isna().all())

    def test_invalid_range_or_country_cannot_be_used_in_cache_paths(self):
        loader = WorldBankDataLoader()
        for codes, start, end in ((("../",), 2021, 2023), (("BRA",), 2024, 2023), ((), 2021, 2023)):
            with self.assertRaises(ValueError):
                loader.fetch_history(codes, start, end)


class NavigationTests(unittest.TestCase):
    def test_share_link_round_trips_context(self):
        url = country_url("CHN_AGG", year=2023, alpha=1.25, lang="en", china_mode="combined", min_population=0)
        params = {key: values[-1] for key, values in parse_qs(urlsplit(url).query).items()}
        defaults = route_defaults(params)
        self.assertEqual(requested_country(params), "CHN_AGG")
        self.assertEqual(defaults["custom_alpha"], 1.25)
        self.assertEqual(defaults["scenario"], "custom")
        self.assertEqual(defaults["china_mode"], "combined")
        self.assertEqual(defaults["min_population"], 0)

    def test_malformed_links_have_safe_defaults(self):
        defaults = route_defaults({"alpha": "nan", "year": "../../", "min_population": "-1", "lang": "xx"})
        self.assertEqual(defaults["data_year"], 2023)
        self.assertEqual(defaults["custom_alpha"], 2)
        self.assertIsNone(requested_country({"country": "<script>"}))

    def test_country_names_are_links_preserving_year_and_weight(self):
        from ppr import PPRConfig, RothbardEngine

        data = RothbardEngine().calculate(sample_data(), PPRConfig(min_population=0))
        ranked = prepare_ranking(data, "Maior PPR por pessoa")
        html = leaderboard_html(ranked, "Maior PPR por pessoa", link_context={"year": 2022, "alpha": 1})
        self.assertIn("country=BRA", html)
        self.assertIn("year=2022&amp;alpha=1", html)
        self.assertIn('target="_self"', html)

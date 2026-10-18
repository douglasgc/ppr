import unittest
from pathlib import Path
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from tests.test_ppr import sample_data


class DashboardTests(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()

    def run_app(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.run(timeout=30)
        self.assertFalse(app.exception)
        return app

    @patch("ppr.data.WorldBankDataLoader.fetch")
    def test_dashboard_and_alpha_change(self, fetch):
        raw = sample_data()
        raw["populacao"] = raw["populacao"] * 100_000
        raw[["gdp", "gastos_governo"]] *= 100_000
        fetch.return_value = raw
        app = self.run_app()
        initial = app.metric[2].value
        app.sidebar.radio[0].set_value("none").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertNotEqual(app.metric[2].value, initial)
        app.sidebar.radio[0].set_value("custom").run(timeout=30)
        app.sidebar.slider[0].set_value(1.25).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.sidebar.slider[0].value, 1.25)

    @patch("ppr.data.WorldBankDataLoader.fetch")
    def test_search_sort_and_selection_preserve_ranking(self, fetch):
        raw = sample_data()
        raw["populacao"] *= 100_000
        fetch.return_value = raw
        app = self.run_app()
        initial = app.metric[0].value
        app.text_input[0].set_value("brasil").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("de **1** países" in item.value for item in app.markdown))
        # Searching is a view filter, not a change in the ranking universe.
        self.assertEqual(app.metric[0].value, initial)
        app.text_input[0].set_value("").run(timeout=30)
        app.selectbox(key="sort_order").set_value("ppr").run(timeout=30)
        app.multiselect[0].set_value(["BRA"]).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["ranking_page"], 1)
        app.text_input[0].set_value("inexistente").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("Nenhum país encontrado" in item.value for item in app.info))

    @patch("ppr.data.WorldBankDataLoader.fetch")
    def test_pagination_resets_after_filter(self, fetch):
        import pandas as pd
        import pycountry

        records = []
        for country in list(pycountry.countries)[:35]:
            row = sample_data().iloc[0].to_dict()
            row.update(country_code=country.alpha_3, country_name=country.name, populacao=1_000_000)
            records.append(row)
        fetch.return_value = pd.DataFrame(records)
        app = self.run_app()
        self.assertEqual(app.selectbox(key="page_size").value, 0)
        app.selectbox(key="page_size").set_value(15).run(timeout=30)
        app.selectbox(key="ranking_page").set_value(3).run(timeout=30)
        self.assertFalse(app.exception)
        app.text_input[0].set_value(records[0]["country_code"]).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["ranking_page"], 1)

    @patch("ppr.data.WorldBankDataLoader.fetch", return_value=sample_data())
    def test_empty_data_has_actionable_message(self, fetch):
        app = self.run_app()
        self.assertTrue(any("Nenhum país com dados suficientes" in item.value for item in app.warning))

    @patch("ppr.data.WorldBankDataLoader.fetch")
    def test_china_search_explains_regions_and_missing_mainland_data(self, fetch):
        from tests.test_presentation import china_data

        raw = china_data()
        raw["populacao"] *= 100_000
        raw.loc[raw["country_code"] == "CHN", "gastos_governo"] = float("nan")
        fetch.return_value = raw
        app = self.run_app()
        app.text_input[0].set_value("China").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("não indica" in item.value for item in app.info))
        self.assertTrue(any("China continental não participa" in item.value and "consumo governamental" in item.value
                            for item in app.warning))

    @patch("ppr.data.WorldBankDataLoader.fetch")
    def test_english_ui_all_results_and_population(self, fetch):
        raw = sample_data()
        raw["populacao"] *= 100_000
        fetch.return_value = raw
        app = self.run_app()
        self.assertEqual(app.selectbox(key="page_size").value, 0)
        app.selectbox(key="language").set_value("en").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Country ranking")
        self.assertEqual(app.tabs[1].label, "World map")
        self.assertTrue(any("Population:" in caption.value for caption in app.caption))
        app.text_input[0].set_value("Brasil").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("of **1** economies" in item.value for item in app.markdown))

    @patch("ppr.data.WorldBankDataLoader.fetch")
    def test_combined_china_ui_replaces_the_three_series(self, fetch):
        from tests.test_presentation import china_data

        raw = china_data()
        raw["populacao"] *= 100_000
        fetch.return_value = raw
        app = self.run_app()
        app.selectbox(key="china_mode").set_value("combined").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="country_detail").value, "CHN_AGG")
        self.assertTrue(any("3.000.000" in caption.value for caption in app.caption))
        self.assertTrue(any("1–1" in item.value for item in app.markdown))

    @patch("ppr.data.WorldBankDataLoader.fetch")
    def test_language_switch_preserves_simulation_and_sort(self, fetch):
        raw = sample_data()
        raw["populacao"] *= 100_000
        fetch.return_value = raw
        app = self.run_app()
        app.sidebar.radio[0].set_value("none").run(timeout=30)
        app.selectbox(key="sort_order").set_value("ppr").run(timeout=30)
        app.selectbox(key="language").set_value("en").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.sidebar.radio[0].value, "none")
        self.assertEqual(app.selectbox(key="sort_order").value, "ppr")

    @patch("ppr.data.WorldBankDataLoader.fetch_history")
    @patch("ppr.data.WorldBankDataLoader.fetch")
    def test_country_deep_link_opens_analysis_and_history(self, fetch, fetch_history):
        from tests.test_history import historical_sample

        raw = sample_data()
        raw["populacao"] *= 100_000
        fetch.return_value = raw
        fetch_history.return_value = historical_sample()
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.query_params.update(country="BRA", year="2023", alpha="1.25", lang="en", min_population="0")
        app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Explore a country")
        self.assertEqual(app.sidebar.slider[0].value, 1.25)
        self.assertEqual(app.radio(key="history_measure").value, "total")
        self.assertEqual(len(app.tabs), 0)
        self.assertTrue(any("GDP and PPR over time" in item.value for item in app.markdown))
        fetch_history.assert_called_once_with(("BRA",), 1960, 2023, refresh=False)
        app.radio(key="history_measure").set_value("per_capita").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(fetch_history.call_count, 1)

    @patch("ppr.data.WorldBankDataLoader.fetch_history")
    @patch("ppr.data.WorldBankDataLoader.fetch")
    def test_ranking_does_not_download_history_until_country_is_opened(self, fetch, fetch_history):
        raw = sample_data()
        raw["populacao"] *= 100_000
        fetch.return_value = raw
        self.run_app()
        fetch_history.assert_not_called()

    @patch("ppr.data.WorldBankDataLoader.fetch_history", side_effect=ValueError("API unavailable"))
    @patch("ppr.data.WorldBankDataLoader.fetch")
    def test_history_failure_does_not_hide_country_analysis(self, fetch, fetch_history):
        raw = sample_data()
        raw["populacao"] *= 100_000
        fetch.return_value = raw
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.query_params["country"] = "BRA"
        app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 3)
        self.assertTrue(any("Não foi possível carregar o histórico" in item.value for item in app.warning))

    @patch("ppr.data.WorldBankDataLoader.fetch")
    def test_taiwan_search_explains_source_coverage(self, fetch):
        raw = sample_data()
        raw["populacao"] *= 100_000
        fetch.return_value = raw
        app = self.run_app()
        app.text_input[0].set_value("Taiwan").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("não entra na China agregada" in item.value for item in app.info))
        self.assertTrue(any("Taiwan (TWN) não foi retornado" in item.value for item in app.warning))


if __name__ == "__main__":
    unittest.main()

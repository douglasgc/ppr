import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import pandas as pd
import requests

from ppr import PPRConfig, RothbardEngine, RothbardPPRClient, WorldBankDataLoader
from ppr.cli import main


def sample_data() -> pd.DataFrame:
    """Valores fictícios; não representam estatísticas reais dos países."""
    return pd.DataFrame([
        dict(country_code="BRA", country_name="Brazil", gdp=1000.0, gastos_governo=200.0,
             populacao=10, consumo_privado=500.0, investimento=250.0, exportacoes=100.0, importacoes=50.0),
        dict(country_code="USA", country_name="United States", gdp=2000.0, gastos_governo=100.0,
             populacao=20, consumo_privado=1200.0, investimento=600.0, exportacoes=200.0, importacoes=100.0),
    ])


class ConfigTests(unittest.TestCase):
    def test_invalid_alpha(self):
        for alpha in (-0.1, 2.1, float("nan"), float("inf"), "2", True):
            with self.subTest(alpha=alpha), self.assertRaises(ValueError):
                PPRConfig(alpha_g=alpha)

    def test_invalid_filters(self):
        for changes in ({"year": 1900}, {"year": True}, {"min_population": -1},
                        {"custom_country_codes": "BRA"}, {"custom_country_codes": ["BR"]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                PPRConfig(**changes)

    def test_normalize_countries(self):
        config = PPRConfig(custom_country_codes=[" bra ", "USA", "BRA"])
        self.assertEqual(config.custom_country_codes, ("BRA", "USA"))


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = RothbardEngine()
        self.config = PPRConfig(min_population=0)

    def test_alpha_endpoints_and_middle(self):
        for alpha in (0, 1, 2):
            with self.subTest(alpha=alpha):
                data = self.engine.calculate(sample_data(), PPRConfig(alpha_g=alpha, min_population=0))
                bra = data.set_index("country_code").loc["BRA"]
                self.assertEqual(bra["ppr"], 1000 - alpha * 200)
                self.assertEqual(bra["ppr_per_capita"], 100 - alpha * 20)

    def test_components_and_accounting_residual(self):
        row = self.engine.calculate(sample_data(), self.config).set_index("country_code").loc["BRA"]
        self.assertEqual(row["gpp"], 800)
        self.assertEqual(row["gpp_componentes"], 800)
        self.assertEqual(row["residuo_contabil"], 0)

    def test_missing_optional_components_do_not_remove_country(self):
        raw = sample_data().drop(columns=list(self.engine.COMPONENTS))
        data = self.engine.calculate(raw, self.config)
        self.assertEqual(len(data), 2)
        self.assertTrue(data["gpp_componentes"].isna().all())

    def test_invalid_essential_values_are_excluded(self):
        for column, values in {
            "gdp": [0, -1, float("nan"), float("inf")],
            "populacao": [0, -1, float("nan"), float("inf")],
            "gastos_governo": [-1, float("nan"), float("inf")],
        }.items():
            for value in values:
                with self.subTest(column=column, value=value):
                    raw = sample_data()
                    raw[column] = raw[column].astype(float)
                    raw.loc[0, column] = value
                    self.assertEqual(self.engine.calculate(raw, self.config)["country_code"].tolist(), ["USA"])

    def test_negative_ppr_is_preserved(self):
        raw = sample_data()
        raw.loc[0, "gastos_governo"] = 700
        row = self.engine.calculate(raw, self.config).set_index("country_code").loc["BRA"]
        self.assertEqual(row["ppr"], -400)

    def test_ties_have_shared_rank(self):
        data = self.engine.calculate(sample_data(), PPRConfig(alpha_g=0, min_population=0))
        self.assertEqual(data["rank_ppr_per_capita"].tolist(), [1, 1])
        self.assertTrue((data["dif_ranking"] == 0).all())

    def test_rank_delta_sign(self):
        raw = sample_data()
        raw.loc[0, "gdp"] = 1100
        row = self.engine.calculate(raw, self.config).set_index("country_code").loc["USA"]
        self.assertEqual(row["rank_gdp_per_capita"], 2)
        self.assertEqual(row["rank_ppr_per_capita"], 1)
        self.assertEqual(row["dif_ranking"], 1)

    def test_filters_and_empty_dataset(self):
        filtered = self.engine.calculate(sample_data(), PPRConfig(min_population=15, custom_country_codes=["USA"]))
        self.assertEqual(filtered["country_code"].tolist(), ["USA"])
        empty = self.engine.calculate(sample_data(), PPRConfig())
        self.assertTrue(empty.empty)
        self.assertIn("rank_ppr_per_capita", empty)
        self.assertTrue(self.engine.calculate(sample_data().iloc[:0], self.config).empty)

    def test_missing_columns_and_duplicates_raise(self):
        for data in (sample_data().drop(columns=["gdp"]), pd.concat([sample_data()] * 2)):
            with self.assertRaises(ValueError):
                self.engine.calculate(data, self.config)

    def test_input_is_not_mutated(self):
        raw = sample_data()
        original = raw.copy(deep=True)
        self.engine.calculate(raw, self.config)
        pd.testing.assert_frame_equal(raw, original)


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.loader = Mock(spec=WorldBankDataLoader)
        self.loader.fetch.return_value = sample_data()
        self.client = RothbardPPRClient(PPRConfig(min_population=0), self.loader)

    def test_change_alpha_invalidates_results_without_refetch(self):
        self.assertEqual(self.client.get_country("bra")["ppr"], 600)
        self.client.set_config(alpha_g=0)
        self.assertEqual(self.client.get_country("BRA")["ppr"], 1000)
        self.loader.fetch.assert_called_once_with(2023, refresh=False)

    def test_top_results_always_include_population(self):
        self.assertIn("populacao", self.client.get_top().columns)

    def test_year_change_refetches(self):
        self.client.calculate()
        self.client.set_config(year=2022).calculate()
        self.assertEqual(self.loader.fetch.call_count, 2)
        self.loader.fetch.assert_called_with(2022, refresh=False)

    def test_refresh_recalculates(self):
        self.client.calculate()
        self.client.load_data(refresh=True)
        self.loader.fetch.assert_called_with(2023, refresh=True)

    def test_filters_invalidate_results(self):
        self.client.calculate()
        self.client.set_config(custom_country_codes=["BRA"])
        self.assertEqual(self.client.get_top()["country_code"].tolist(), ["BRA"])

    def test_invalid_update_is_atomic(self):
        with self.assertRaises(ValueError):
            self.client.set_config(year=2022, alpha_g=10)
        self.assertEqual(self.client.config.year, 2023)

    def test_result_is_a_defensive_copy(self):
        result = self.client.calculate()
        result["ppr"] = 0
        self.assertGreater(self.client.get_country("BRA")["ppr"], 0)

    def test_unknown_country_and_invalid_top(self):
        with self.assertRaises(ValueError):
            self.client.get_country("XXX")
        with self.assertRaises(ValueError):
            self.client.get_top(0)

    def test_csv_json_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            for extension in ("csv", "json"):
                path = self.client.export(Path(directory) / f"nested/results.{extension}")
                if extension == "csv":
                    self.assertEqual(len(pd.read_csv(path)), 2)
                else:
                    rows = json.loads(path.read_text())
                    self.assertEqual(len(rows), 2)
                    self.assertEqual(rows[0]["alpha_g"], 2)
            with self.assertRaises(ValueError):
                self.client.export(Path(directory) / "unsupported.txt")


class LoaderTests(unittest.TestCase):
    def test_pagination(self):
        loader = WorldBankDataLoader()
        with patch.object(loader, "_page", side_effect=[
            [{"pages": 2}, [{"id": "BRA"}]], [{"pages": 2}, [{"id": "USA"}]],
        ]) as page:
            self.assertEqual(len(loader._records("country")), 2)
            self.assertEqual(page.call_args.args[1]["page"], 2)

    @patch("ppr.data.requests.get")
    def test_invalid_api_response(self, get):
        get.return_value.json.return_value = [{"message": [{"value": "Invalid indicator"}]}]
        with self.assertRaisesRegex(ValueError, "Resposta inválida"):
            WorldBankDataLoader()._records("country")

    @patch("ppr.data.time.sleep")
    @patch("ppr.data.requests.get")
    def test_network_retries(self, get, sleep):
        response = Mock()
        response.json.return_value = [{"pages": 1}, []]
        get.side_effect = [requests.Timeout("timeout"), response]
        self.assertEqual(WorldBankDataLoader()._records("country"), [])
        self.assertEqual(get.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_excludes_aggregates_retains_missing_components_and_caches(self):
        def records(endpoint, **params):
            if endpoint == "country":
                return [
                    {"id": "BRA", "name": "Brazil", "region": {"id": "LCN"}},
                    {"id": "WLD", "name": "World", "region": {"id": "NA"}},
                ]
            return [
                {"countryiso3code": "BRA", "date": "2023", "value": None},
                {"countryiso3code": "WLD", "date": "2023", "value": 999},
            ]

        with tempfile.TemporaryDirectory() as directory:
            loader = WorldBankDataLoader(directory)
            with patch.object(loader, "_records", side_effect=records) as fetch:
                data = loader.fetch(2023)
                self.assertEqual(data["country_code"].tolist(), ["BRA"])
                self.assertTrue(data["consumo_privado"].isna().all())
                self.assertEqual(fetch.call_count, 8)
                cached = loader.fetch(2023)
                self.assertEqual(fetch.call_count, 8)
                self.assertEqual(cached["country_code"].tolist(), ["BRA"])
                loader.fetch(2023, refresh=True)
                self.assertEqual(fetch.call_count, 16)


class CLITests(unittest.TestCase):
    @patch("ppr.data.WorldBankDataLoader.fetch", return_value=sample_data())
    def test_cli_output_and_export(self, fetch):
        with tempfile.TemporaryDirectory() as directory, patch("sys.stdout", new_callable=io.StringIO) as output:
            path = Path(directory) / "results.json"
            code = main(["--min-population", "0", "--countries", "BRA", "--alpha", "1", "--export", str(path)])
            self.assertEqual(code, 0)
            self.assertIn("BRA", output.getvalue())
            self.assertEqual(json.loads(path.read_text())[0]["ppr"], 800)

    def test_invalid_arguments_fail_before_fetch(self):
        with patch("sys.stderr", new_callable=io.StringIO), self.assertRaises(SystemExit) as error:
            main(["--alpha", "3"])
        self.assertEqual(error.exception.code, 1)


if __name__ == "__main__":
    unittest.main()

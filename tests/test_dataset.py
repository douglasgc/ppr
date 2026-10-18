import json
import unittest

import pandas as pd

from ppr import PPRConfig
from ppr.charts import world_map
from ppr.dataset import build_dataset, metadata
from ppr.i18n import LANGUAGES, TEXT, t
from ppr.presentation import country_label, money, prepare_ranking, sort_options
from tests.test_ppr import sample_data
from tests.test_presentation import china_data


class DatasetTests(unittest.TestCase):
    def test_complete_numeric_contract_and_all_fields(self):
        rows = []
        for index in range(60):
            row = sample_data().iloc[0].to_dict()
            row["country_code"] = f"X{index:02d}"
            rows.append(row)
        raw = pd.DataFrame(rows)
        raw.loc[0, "exportacoes"] = float("nan")
        result = build_dataset(raw, PPRConfig(min_population=0))
        self.assertEqual(result["metadata"]["record_count"], 60)
        self.assertEqual(result["metadata"]["raw_record_count"], 60)
        self.assertEqual(len(result["records"]), 60)
        self.assertEqual(len(result["raw_records"]), 60)
        self.assertTrue(result["metadata"]["complete"])
        self.assertFalse(result["metadata"]["truncated"])
        self.assertEqual(set(result["records"][0]), set(metadata()["fields"]))
        self.assertTrue(all("population" in row for row in result["records"]))
        self.assertTrue(all("population" in row for row in result["raw_records"]))
        self.assertIsInstance(result["records"][0]["ppr"], float)
        json.dumps(result, allow_nan=False)
        self.assertIsNone(next(row for row in result["records"] if row["country_code"] == "X00")["exports"])

    def test_country_view_preserves_ranks(self):
        result = build_dataset(sample_data(), PPRConfig(min_population=0), countries=["BRA"])
        self.assertEqual(result["metadata"]["ranked_count"], 2)
        self.assertEqual(result["records"][0]["rank_ppr_per_capita"], 2)
        self.assertEqual(result["records"][0]["position"], 2)

    def test_taiwan_coverage_is_explicit_without_fabricated_observations(self):
        result = build_dataset(sample_data(), PPRConfig(min_population=0), countries=["TWN"])
        self.assertEqual(result["records"], [])
        self.assertEqual(result["raw_records"], [])
        self.assertEqual(result["excluded"], [])
        self.assertEqual(result["metadata"]["coverage_notes"]["TWN"], {
            "source_series_present": False, "in_ranked_cohort": False, "included_in_china_aggregate": False,
        })
        self.assertIn("not included", result["metadata"]["taiwan_context"])
        self.assertIn("Taiwan", result["metadata"]["aggregation_note"])

    def test_wrong_year_cannot_be_silently_relabeled(self):
        raw = sample_data()
        raw["year"] = 2022
        with self.assertRaisesRegex(ValueError, "config.year"):
            build_dataset(raw, PPRConfig(year=2023))

    def test_raw_data_and_exclusions_explain_missing_results(self):
        raw = sample_data()
        raw.loc[0, "gastos_governo"] = float("nan")
        result = build_dataset(raw, PPRConfig(min_population=0))
        self.assertEqual(len(result["raw_records"]), 2)
        self.assertEqual(result["metadata"]["record_count"], 1)
        self.assertEqual(result["excluded"][0]["reasons"], ["missing_or_invalid:government_consumption"])

    def test_combined_china_preserves_original_raw_inputs(self):
        result = build_dataset(china_data(), PPRConfig(min_population=0), china_mode="combined", countries=["CHN_AGG"])
        self.assertEqual(result["records"][0]["country_code"], "CHN_AGG")
        self.assertEqual(len(result["raw_records"]), 3)
        self.assertTrue(result["metadata"]["aggregation"]["applied"])

    def test_english_sort_keys_and_no_hidden_reranking(self):
        for sort in ("ppr_per_capita", "gdp_per_capita", "ppr", "private_retention_pct", "rank_change"):
            with self.subTest(sort=sort):
                result = build_dataset(sample_data(), PPRConfig(min_population=0), sort_by=sort)
                self.assertEqual(result["metadata"]["sort_by"], sort)
        with self.assertRaises(ValueError):
            build_dataset(sample_data(), PPRConfig(custom_country_codes=["BRA"]))


class InternationalizationAndMapTests(unittest.TestCase):
    def test_catalog_is_complete_and_locales_format_names_and_numbers(self):
        for translations in TEXT.values():
            self.assertEqual(len(translations), len(LANGUAGES))
            self.assertTrue(all(translations))
        self.assertEqual(money(12345.67, 2, "en"), "US$ 12,345.67")
        self.assertEqual(country_label("CHN", "China", "en")[0], "Mainland China")
        self.assertEqual(country_label("BRA", "Brazil", "en")[0], "Brazil")
        with self.assertRaises(ValueError):
            t("title", "invalid")

    def test_map_uses_ranking_positions_and_expands_synthetic_china(self):
        from ppr.aggregation import aggregate_china
        from ppr.engine import RothbardEngine

        prepared, _ = aggregate_china(china_data(), "combined")
        data = RothbardEngine().calculate(prepared, PPRConfig(min_population=0))
        ranked = prepare_ranking(data, next(iter(sort_options("en"))), "en")
        figure = world_map(ranked, "en")
        self.assertEqual(list(figure.data[0].locations), ["CHN", "HKG", "MAC"])
        self.assertEqual(list(figure.data[0].z), [1, 1, 1])
        self.assertEqual(figure.data[0].colorbar.title.text, "Ranking position")

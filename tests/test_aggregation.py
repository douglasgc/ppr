import unittest

import pandas as pd

from ppr import PPRConfig, RothbardEngine
from ppr.aggregation import aggregate_china
from tests.test_presentation import china_data


class AggregationTests(unittest.TestCase):
    def test_sums_levels_and_replaces_components_before_per_capita(self):
        raw = china_data()
        raw["populacao"] = [10, 100, 1000]
        original = raw.copy(deep=True)
        prepared, status = aggregate_china(raw, "combined")
        self.assertTrue(status["applied"])
        self.assertEqual(prepared["country_code"].tolist(), ["CHN_AGG"])
        row = RothbardEngine().calculate(prepared, PPRConfig(min_population=0)).iloc[0]
        self.assertEqual(row["gdp"], 3000)
        self.assertEqual(row["gastos_governo"], 600)
        self.assertEqual(row["populacao"], 1110)
        self.assertAlmostEqual(row["ppr_per_capita"], 1800 / 1110)
        self.assertNotAlmostEqual(row["ppr_per_capita"], (60 + 6 + .6) / 3)
        pd.testing.assert_frame_equal(raw, original)

    def test_missing_essential_never_creates_partial_aggregate(self):
        for field in ("gdp", "gastos_governo", "populacao"):
            with self.subTest(field=field):
                raw = china_data()
                raw[field] = raw[field].astype(float)
                raw.loc[0, field] = float("nan")
                prepared, status = aggregate_china(raw, "combined")
                self.assertFalse(status["applied"])
                self.assertEqual(status["missing"], {"CHN": [field]})
                self.assertEqual(len(prepared), 3)

    def test_optional_fields_remain_null_if_any_part_is_missing(self):
        raw = china_data()
        raw.loc[0, "exportacoes"] = float("nan")
        prepared, status = aggregate_china(raw, "combined")
        self.assertTrue(status["applied"])
        self.assertTrue(pd.isna(prepared.iloc[0]["exportacoes"]))

    def test_year_mismatch_and_duplicate_components_rejected(self):
        raw = china_data()
        raw["year"] = [2023, 2023, 2022]
        with self.assertRaises(ValueError):
            aggregate_china(raw, "combined")
        with self.assertRaises(ValueError):
            aggregate_china(pd.concat([china_data(), china_data().iloc[:1]]), "combined")

    def test_population_filter_is_applied_after_sum(self):
        prepared, _ = aggregate_china(china_data(), "combined")
        self.assertEqual(len(RothbardEngine().calculate(prepared, PPRConfig(min_population=25))), 1)

    def test_separate_mode_preserves_input_and_missing_series_is_explicit(self):
        raw = china_data()
        separate, status = aggregate_china(raw)
        pd.testing.assert_frame_equal(raw, separate)
        self.assertFalse(status["applied"])
        _, status = aggregate_china(raw.iloc[:2], "combined")
        self.assertEqual(status["missing"], {"MAC": ["series"]})

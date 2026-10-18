import unittest

import pandas as pd

from ppr import PPRConfig, RothbardEngine
from ppr.presentation import (
    change,
    china_exclusion_note,
    country_label,
    leaderboard_html,
    money,
    percent,
    prepare_ranking,
    search_ranking,
)
from tests.test_ppr import sample_data


def china_data():
    records = []
    for code, name in (("CHN", "China"), ("HKG", "Hong Kong SAR, China"), ("MAC", "Macao SAR, China")):
        row = sample_data().iloc[0].to_dict()
        row.update(country_code=code, country_name=name)
        records.append(row)
    return pd.DataFrame(records)


class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.data = RothbardEngine().calculate(sample_data(), PPRConfig(min_population=0))

    def test_portuguese_numbers(self):
        self.assertEqual(money(12345.67, 2), "US$ 12.345,67")
        self.assertEqual(money(-500), "US$ -500")
        self.assertEqual(percent(61.91), "61,9%")
        self.assertEqual(change(1), "↑ 1 posição")
        self.assertEqual(change(-3), "↓ 3 posições")

    def test_country_names_are_localized(self):
        self.assertEqual(country_label("BRA", "Brazil"), ("Brasil", "🇧🇷"))
        self.assertEqual(country_label("USA", "United States")[0], "Estados Unidos")
        self.assertEqual(country_label("ZZZ", "Fallback")[0], "Fallback")

    def test_china_labels_scope_and_search_are_explicit(self):
        data = RothbardEngine().calculate(china_data(), PPRConfig(min_population=0))
        ranked = prepare_ranking(data, "Maior PPR por pessoa")
        self.assertEqual(set(ranked["nome"]), {"China continental", "Hong Kong (China)", "Macau (China)"})
        self.assertEqual(len(search_ranking(ranked, "china", [])), 3)
        self.assertEqual(search_ranking(ranked, "China continental", [])["country_code"].tolist(), ["CHN"])
        html = leaderboard_html(ranked, "Maior PPR por pessoa")
        self.assertIn("Não inclui Hong Kong e Macau", html)
        self.assertEqual(html.count("Região administrativa especial"), 2)

    def test_china_missing_data_is_explained_without_merging_regions(self):
        raw = china_data()
        raw.loc[raw["country_code"] == "CHN", "gastos_governo"] = float("nan")
        data = RothbardEngine().calculate(raw, PPRConfig(min_population=0))
        note = china_exclusion_note(raw, data, 2025, 0)
        self.assertIn("2025", note)
        self.assertIn("consumo governamental (G)", note)
        self.assertIn("não substituem", note)
        self.assertEqual(set(data["country_code"]), {"HKG", "MAC"})
        self.assertTrue((data["ppr"] == 600).all())

    def test_china_population_filter_is_not_reported_as_missing_data(self):
        raw = china_data()
        data = RothbardEngine().calculate(raw, PPRConfig(min_population=100))
        self.assertIn("população está abaixo", china_exclusion_note(raw, data, 2023, 100))
        all_data = RothbardEngine().calculate(raw, PPRConfig(min_population=0))
        self.assertEqual(china_exclusion_note(raw, all_data, 2023, 0), "")

    def test_ranking_is_sorted_and_search_does_not_rerank(self):
        ranked = prepare_ranking(self.data, "Maior PPR por pessoa")
        self.assertEqual(ranked["country_code"].tolist(), ["USA", "BRA"])
        brazil = search_ranking(ranked, "brasil", [])
        self.assertEqual(brazil["posicao"].tolist(), [2])
        self.assertEqual(brazil["rank_ppr_per_capita"].tolist(), [2])
        self.assertEqual(search_ranking(ranked, "", ["BRA"])["posicao"].tolist(), [2])

    def test_ties_are_preserved_for_other_orderings(self):
        ranked = prepare_ranking(self.data, "Maior PIB por pessoa")
        self.assertEqual(ranked["posicao"].tolist(), [1, 1])
        self.assertEqual(ranked["nome"].tolist(), ["Brasil", "Estados Unidos"])

    def test_total_and_per_person_have_different_orders(self):
        raw = sample_data()
        raw["populacao"] = [1, 200]
        data = RothbardEngine().calculate(raw, PPRConfig(min_population=0))
        by_person = prepare_ranking(data, "Maior PPR por pessoa")
        by_total = prepare_ranking(data, "Maior PPR total")
        self.assertEqual(by_person.iloc[0]["country_code"], "BRA")
        self.assertEqual(by_total.iloc[0]["country_code"], "USA")
        self.assertEqual(by_total.iloc[0]["rank_ppr_per_capita"], 2)

    def test_search_supports_accents_codes_and_literal_input(self):
        ranked = prepare_ranking(self.data, "Maior PPR por pessoa")
        for query in ("BRA", " brásil ", "Brazil"):
            self.assertEqual(len(search_ranking(ranked, query, [])), 1)
        self.assertTrue(search_ranking(ranked, "[", []).empty)

    def test_html_is_readable_and_escaped(self):
        ranked = prepare_ranking(self.data, "Maior PPR por pessoa")
        ranked.loc[0, "nome"] = '<script>alert("x")</script>'
        html = leaderboard_html(ranked, "Maior PPR por pessoa")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("PPR por pessoa", html)
        self.assertIn("US$ 90", html)
        self.assertNotIn("ppr_per_capita", html)

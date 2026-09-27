import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools/analyzers"))
from tools.strategy_engine import generate_call_plan
from market_sizer import triangulate


class ResearchContractsTests(unittest.TestCase):
    def test_configured_dimensions_choose_real_sources(self):
        plan = generate_call_plan(
            ["google_trends", "app_store", "reddit_public"],
            ["trend_analysis", "product_competition", "user_demand"],
            "watches", "sg", str(ROOT / "config/dimensions.yaml"),
        )
        self.assertEqual({item["source"] for item in plan["call_plan"]}, {"google_trends", "app_store"})
        self.assertTrue(any("user complaints" in query for query in plan["web_search_queries"]))
        self.assertTrue(any(str(date.today().year) in query for query in plan["web_search_queries"]))
        self.assertTrue(all(query.endswith("sg") for query in plan["web_search_queries"]))

    def test_empty_estimates_are_unknown_not_agreement(self):
        result = triangulate({}, {})
        self.assertIsNone(result["tam_midpoint"])
        self.assertEqual(result["consistency"], 0)
        self.assertEqual(result["combined_confidence"], 0)

    def test_one_estimate_is_not_averaged_with_missing_zero(self):
        result = triangulate({"tam": 100, "sam": 20, "som": 2, "confidence": 0.3}, {})
        self.assertEqual(result["tam_midpoint"], 100)
        self.assertEqual(result["combined_confidence"], 0)

    def test_two_matching_estimates_and_zero_growth_are_preserved(self):
        value = {"tam": 100, "sam": 20, "som": 2, "confidence": 0.5, "cagr": 0}
        result = triangulate(value, value)
        self.assertEqual(result["consistency"], 1)
        self.assertEqual(result["tam_midpoint"], 100)
        self.assertEqual(result["cagr"], 0)


if __name__ == "__main__":
    unittest.main()

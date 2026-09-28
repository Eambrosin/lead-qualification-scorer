import unittest

import pandas as pd

from lead_qualifier import (
    WEIGHTS,
    rank_leads,
    score_company_size,
    tier_for_score,
    validate_input_dataframe,
)


class LeadQualificationEngineTests(unittest.TestCase):

    def setUp(self):
        self.strong_lead = {
            "company_name": "Solis Renewables",
            "country": "Brazil",
            "region": "LATAM",
            "industry": "Renewable Energy",
            "company_size": 250,
            "estimated_deal_value_usd": 250000,
            "engagement_signal": "hot",
        }

        self.weak_lead = {
            "company_name": "Example Prospect",
            "country": "Singapore",
            "region": "APAC",
            "industry": "Other",
            "company_size": 5000,
            "estimated_deal_value_usd": 25000,
            "engagement_signal": "cold",
        }

    def test_default_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0, places=6)

    def test_company_size_inside_icp_scores_full_fit(self):
        self.assertEqual(score_company_size(250, 50, 1000), 100.0)

    def test_company_size_outside_icp_is_penalized(self):
        self.assertLess(score_company_size(5000, 50, 1000), 100.0)

    def test_default_tier_boundaries(self):
        self.assertEqual(tier_for_score(75), "A")
        self.assertEqual(tier_for_score(50), "B")
        self.assertEqual(tier_for_score(49.9), "C")

    def test_rank_leads_prioritizes_stronger_opportunity(self):
        dataframe = pd.DataFrame([self.weak_lead, self.strong_lead])
        ranked = rank_leads(dataframe)
        self.assertEqual(ranked.iloc[0]["company_name"], "Solis Renewables")
        self.assertGreater(ranked.iloc[0]["score"], ranked.iloc[1]["score"])

    def test_missing_required_column_raises_error(self):
        invalid = pd.DataFrame([self.strong_lead]).drop(columns=["industry"])
        with self.assertRaises(ValueError):
            validate_input_dataframe(invalid)

    def test_negative_deal_value_raises_error(self):
        invalid_lead = dict(self.strong_lead)
        invalid_lead["estimated_deal_value_usd"] = -1
        invalid = pd.DataFrame([invalid_lead])
        with self.assertRaises(ValueError):
            validate_input_dataframe(invalid)


if __name__ == "__main__":
    unittest.main()

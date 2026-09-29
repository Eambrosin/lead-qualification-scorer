import unittest

import pandas as pd

from qualification_profiles import get_qualification_profile
from lead_qualifier import (
    INDUSTRY_SCORES,
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

    def test_medical_aesthetics_is_supported_industry(self):
        self.assertIn("Medical Aesthetics", INDUSTRY_SCORES)

    def test_europe_region_alias_integrates_discovery_output(self):
        medical = {
            "company_name": "Example Aesthetic Clinic",
            "country": "Italy",
            "region": "Europe",
            "industry": "Medical Aesthetics",
            "company_size": 25,
            "estimated_deal_value_usd": 75000,
            "engagement_signal": "warm",
            "market_profile_id": "medical_aesthetics",
            "source_stage": "IDENTIFY",
        }
        ranked = rank_leads(pd.DataFrame([medical]))
        self.assertEqual(ranked.iloc[0]["market_profile_id"], "medical_aesthetics")
        self.assertEqual(ranked.iloc[0]["source_stage"], "IDENTIFY")
        self.assertGreater(ranked.iloc[0]["score"], 0)


    def test_medical_aesthetics_icp_does_not_penalize_small_clinics_by_default(self):
        profile = get_qualification_profile(
            "Medical Aesthetics — Clinics & Practitioners"
        )
        self.assertEqual(profile["profile_id"], "medical_aesthetics")
        self.assertEqual(profile["min_company_size"], 0)
        self.assertEqual(profile["max_company_size"], 250)
        self.assertIn("Medical Aesthetics", profile["preferred_industries"])

    def test_territory_metadata_survives_ranking(self):
        medical = {
            "company_name": "Example Aesthetic Clinic",
            "country": "Italy",
            "region": "EU",
            "industry": "Medical Aesthetics",
            "company_size": 18,
            "estimated_deal_value_usd": 75000,
            "engagement_signal": "warm",
            "market_profile_id": "medical_aesthetics",
            "territory_profile_id": "it_north_medical_aesthetics",
            "territory_region": "Lombardia",
            "territory_province": "Bergamo",
            "territory_city": "Bergamo",
            "account_opportunity_score": 88.0,
            "territory_status": "Find Decision Maker",
        }
        ranked = rank_leads(pd.DataFrame([medical]))
        self.assertEqual(
            ranked.iloc[0]["territory_profile_id"],
            "it_north_medical_aesthetics",
        )
        self.assertEqual(ranked.iloc[0]["territory_province"], "Bergamo")
        self.assertEqual(ranked.iloc[0]["account_opportunity_score"], 88.0)


if __name__ == "__main__":
    unittest.main()

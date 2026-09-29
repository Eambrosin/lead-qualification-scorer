import unittest

import pandas as pd

from integrated_scoring import rank_integrated_leads
from lead_qualifier import load_scoring_config


class IntegratedScoringTests(unittest.TestCase):

    def _config(self):
        config = load_scoring_config()
        config["weights"] = {
            "upstream_fit": 0.30,
            "region": 0.10,
            "industry": 0.20,
            "company_size": 0.05,
            "deal_value": 0.15,
            "engagement": 0.20,
        }
        config["region_scores"]["EU"] = 100
        config["industry_scores"]["Medical Aesthetics"] = 100
        config["company_size_range"] = {"min": 0, "max": 250}
        return config

    def test_unknown_commercial_fields_are_not_scored_as_zero_or_cold(self):
        data = pd.DataFrame(
            [{
                "company_name": "Example Clinic",
                "country": "Italy",
                "region": "EU",
                "industry": "Medical Aesthetics",
                "company_size": pd.NA,
                "estimated_deal_value_usd": 0,
                "deal_value_status": "unknown",
                "engagement_signal": "",
                "engagement_status": "unverified",
                "account_opportunity_score": 84,
                "discovery_score": 80,
            }]
        )

        ranked = rank_integrated_leads(data, self._config())
        row = ranked.iloc[0]

        self.assertGreater(row["score"], 80)
        self.assertLess(row["qualification_completeness"], 80)
        self.assertIn(
            row["qualification_status"],
            {"Partially Qualified", "Research / Enrichment Required"},
        )
        self.assertIn("Deal Value: not yet qualified", row["score_rationale"])
        self.assertIn("Engagement: not yet qualified", row["score_rationale"])

    def test_upstream_account_opportunity_differentiates_same_market_accounts(self):
        data = pd.DataFrame(
            [
                {
                    "company_name": "Clinic A",
                    "country": "Italy",
                    "region": "EU",
                    "industry": "Medical Aesthetics",
                    "company_size": pd.NA,
                    "estimated_deal_value_usd": 0,
                    "deal_value_status": "unknown",
                    "engagement_signal": "",
                    "engagement_status": "unverified",
                    "account_opportunity_score": 92,
                },
                {
                    "company_name": "Clinic B",
                    "country": "Italy",
                    "region": "EU",
                    "industry": "Medical Aesthetics",
                    "company_size": pd.NA,
                    "estimated_deal_value_usd": 0,
                    "deal_value_status": "unknown",
                    "engagement_signal": "",
                    "engagement_status": "unverified",
                    "account_opportunity_score": 68,
                },
            ]
        )

        ranked = rank_integrated_leads(data, self._config())
        self.assertEqual(ranked.iloc[0]["company_name"], "Clinic A")
        self.assertGreater(ranked.iloc[0]["score"], ranked.iloc[1]["score"])

    def test_verified_commercial_fields_increase_qualification_completeness(self):
        base = {
            "company_name": "Example Clinic",
            "country": "Italy",
            "region": "EU",
            "industry": "Medical Aesthetics",
            "account_opportunity_score": 85,
        }

        unknown = {
            **base,
            "company_size": pd.NA,
            "estimated_deal_value_usd": 0,
            "deal_value_status": "unknown",
            "engagement_signal": "",
            "engagement_status": "unverified",
        }

        qualified = {
            **base,
            "company_size": 25,
            "estimated_deal_value_usd": 90000,
            "deal_value_status": "verified",
            "engagement_signal": "warm",
            "engagement_status": "verified",
        }

        ranked = rank_integrated_leads(
            pd.DataFrame([unknown, qualified]),
            self._config(),
        )

        known_row = ranked[ranked["company_name"] == "Example Clinic"].iloc[0]
        # Duplicate names are allowed; inspect the maximum completeness.
        self.assertEqual(ranked["qualification_completeness"].max(), 100.0)
        self.assertLess(ranked["qualification_completeness"].min(), 100.0)


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from unittest.mock import patch

from ai_insights import (
    _has_api_key,
    generate_ai_insight,
    generate_outreach,
)


class AIInsightsFallbackTests(unittest.TestCase):

    def setUp(self):
        self.lead = {
            "company": "Example Company",
            "country": "Italy",
            "region": "EU",
            "industry": "Renewable Energy",
            "deal_value": 250000,
            "engagement_signal": "warm",
            "score": 82,
            "tier": "A",
            "recommended_action": "Immediate personalized outreach",
            "score_rationale": "Region Fit and Industry Fit are strong.",
            "score_breakdown": {},
            "priority_regions": ["EU"],
            "priority_industries": ["Renewable Energy"],
            "scoring_weights": {
                "region": 0.20,
                "industry": 0.20,
                "company_size": 0.15,
                "deal_value": 0.25,
                "engagement": 0.20,
            },
            "tier_thresholds": {
                "A": 75,
                "B": 50,
            },
            "outreach_language": "Italian",
        }

    def test_explicit_api_key_is_detected_without_environment_mutation(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(_has_api_key())
            self.assertTrue(_has_api_key("session-key"))
            self.assertNotIn("OPENAI_API_KEY", os.environ)

    def test_local_insight_fallback_works_without_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            output = generate_ai_insight(
                self.lead,
                api_key=None,
            )

        self.assertIsInstance(output, str)
        self.assertIn("Account Brief", output)
        self.assertIn("Example Company", output)

    def test_local_outreach_fallback_works_without_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            output = generate_outreach(
                self.lead,
                api_key=None,
            )

        self.assertIsInstance(output, str)
        self.assertIn("Email", output)
        self.assertIn("LinkedIn", output)


if __name__ == "__main__":
    unittest.main()

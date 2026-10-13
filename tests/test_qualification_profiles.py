import unittest

from qualification_profiles import get_qualification_profile


class QualificationProfileTests(unittest.TestCase):
    def test_photovoltaic_profile_matches_identify_id(self):
        profile = get_qualification_profile(
            "Fotovoltaico — C&I Energy Consumers"
        )
        self.assertEqual(
            profile["profile_id"],
            "photovoltaic_energy_consumers",
        )

    def test_machinery_brazil_profile_matches_identify_id(self):
        profile = get_qualification_profile(
            "Industrial Machinery — Brazil"
        )
        self.assertEqual(
            profile["profile_id"],
            "industrial_machinery_brazil",
        )
        self.assertIn("LATAM", profile["preferred_regions"])

    def test_specialty_coffee_profile_matches_identify_id(self):
        profile = get_qualification_profile(
            "Specialty Coffee — Europe"
        )
        self.assertEqual(
            profile["profile_id"],
            "specialty_coffee_europe",
        )
        self.assertIn("EU", profile["preferred_regions"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

QUALIFICATION_PROFILE_SCHEMA_VERSION = "1.0"

QUALIFICATION_PROFILES = {
    "General B2B": {
        "profile_id": "custom",
        "preferred_regions": ["LATAM", "MENA"],
        "preferred_industries": [
            "Agribusiness",
            "Renewable Energy",
            "Government / Public Sector",
        ],
        "min_company_size": 50,
        "max_company_size": 1000,
        "weights": {
            "region": 20,
            "industry": 20,
            "company_size": 15,
            "deal_value": 25,
            "engagement": 20,
        },
        "note": "General configurable B2B qualification profile.",
    },
    "Medical Aesthetics — Clinics & Practitioners": {
        "profile_id": "medical_aesthetics",
        "preferred_regions": ["EU"],
        "preferred_industries": ["Medical Aesthetics"],
        "min_company_size": 0,
        "max_company_size": 250,
        "weights": {
            "region": 15,
            "industry": 25,
            "company_size": 10,
            "deal_value": 20,
            "engagement": 30,
        },
        "note": (
            "Designed for clinic/practice qualification. Small organizations are not "
            "penalized simply for having fewer employees. Deal value and engagement "
            "remain manual qualification inputs."
        ),
    },
    "Renewable Energy": {
        "profile_id": "renewable_energy",
        "preferred_regions": ["EU", "LATAM", "MENA"],
        "preferred_industries": ["Renewable Energy"],
        "min_company_size": 20,
        "max_company_size": 1000,
        "weights": {
            "region": 20,
            "industry": 25,
            "company_size": 15,
            "deal_value": 25,
            "engagement": 15,
        },
        "note": "",
    },
    "Agribusiness": {
        "profile_id": "agribusiness",
        "preferred_regions": ["LATAM", "EU", "MENA"],
        "preferred_industries": ["Agribusiness"],
        "min_company_size": 20,
        "max_company_size": 2000,
        "weights": {
            "region": 20,
            "industry": 25,
            "company_size": 10,
            "deal_value": 30,
            "engagement": 15,
        },
        "note": "",
    },
    "Logistics & Trade": {
        "profile_id": "logistics_trade",
        "preferred_regions": ["EU", "LATAM", "MENA"],
        "preferred_industries": ["Logistics & Trade"],
        "min_company_size": 20,
        "max_company_size": 5000,
        "weights": {
            "region": 20,
            "industry": 25,
            "company_size": 10,
            "deal_value": 25,
            "engagement": 20,
        },
        "note": "",
    },
    "Fintech": {
        "profile_id": "fintech",
        "preferred_regions": ["EU", "MENA", "LATAM"],
        "preferred_industries": ["Fintech"],
        "min_company_size": 20,
        "max_company_size": 3000,
        "weights": {
            "region": 15,
            "industry": 25,
            "company_size": 10,
            "deal_value": 25,
            "engagement": 25,
        },
        "note": "",
    },
    "Real Estate": {
        "profile_id": "real_estate",
        "preferred_regions": ["EU", "MENA"],
        "preferred_industries": ["Real Estate"],
        "min_company_size": 10,
        "max_company_size": 5000,
        "weights": {
            "region": 20,
            "industry": 20,
            "company_size": 10,
            "deal_value": 30,
            "engagement": 20,
        },
        "note": "",
    },
    "Government / Public Sector": {
        "profile_id": "government_public_sector",
        "preferred_regions": ["LATAM", "EU"],
        "preferred_industries": ["Government / Public Sector"],
        "min_company_size": 0,
        "max_company_size": 100000,
        "weights": {
            "region": 20,
            "industry": 25,
            "company_size": 5,
            "deal_value": 30,
            "engagement": 20,
        },
        "note": "",
    },
}


def get_qualification_profile(name: str) -> dict:
    return QUALIFICATION_PROFILES[name].copy()

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
            "upstream_fit": 15,
            "region": 15,
            "industry": 20,
            "company_size": 10,
            "deal_value": 25,
            "engagement": 15,
        },
        "note": "General configurable B2B qualification profile.",
    },
    "Fotovoltaico — C&I Energy Consumers": {
        "profile_id": "photovoltaic_energy_consumers",
        "preferred_regions": ["EU"],
        "preferred_industries": [
            "Aziende ad Alto Consumo Energetico",
            "Industrial Manufacturing",
            "Food Manufacturing",
            "Food & Beverage",
            "Logistics",
            "Hospitality",
            "Healthcare",
            "Data Centers",
        ],
        "min_company_size": 10,
        "max_company_size": 10000,
        "weights": {
            "upstream_fit": 30,
            "region": 10,
            "industry": 20,
            "company_size": 5,
            "deal_value": 20,
            "engagement": 15,
        },
        "note": (
            "Qualification profile for commercial and industrial photovoltaic end customers. "
            "Public energy-intensity signals support prioritization but do not establish "
            "verified electricity consumption or technical feasibility."
        ),
    },
    "Industrial Machinery — Brazil": {
        "profile_id": "industrial_machinery_brazil",
        "preferred_regions": ["LATAM"],
        "preferred_industries": [
            "Macchinari e Attrezzature Industriali",
            "Industrial Manufacturing",
            "Food Manufacturing",
            "Beverage Manufacturing",
            "Packaging",
            "Pharmaceuticals",
            "Chemicals",
            "Metalworking",
            "Automotive",
        ],
        "min_company_size": 20,
        "max_company_size": 10000,
        "weights": {
            "upstream_fit": 30,
            "region": 10,
            "industry": 20,
            "company_size": 5,
            "deal_value": 20,
            "engagement": 15,
        },
        "note": (
            "Europe → Brazil machinery / equipment qualification profile. "
            "Use the Commercial Mandate to define the exact machine, industrial application, "
            "buyer type and route-to-market hypothesis."
        ),
    },
    "Specialty Coffee — Europe": {
        "profile_id": "specialty_coffee_europe",
        "preferred_regions": ["EU"],
        "preferred_industries": [
            "Specialty Coffee",
            "Coffee",
            "Food & Beverage",
            "Food Import",
        ],
        "min_company_size": 5,
        "max_company_size": 5000,
        "weights": {
            "upstream_fit": 30,
            "region": 10,
            "industry": 20,
            "company_size": 5,
            "deal_value": 20,
            "engagement": 15,
        },
        "note": (
            "Brazil → Europe specialty-coffee qualification profile. "
            "Quality, certifications, crop availability, logistics, pricing and actual "
            "buyer interest remain qualification inputs."
        ),
    },
    "Medical Aesthetics — Clinics & Practitioners": {
        "profile_id": "medical_aesthetics",
        "preferred_regions": ["EU"],
        "preferred_industries": ["Medicina Estetica", "Medical Aesthetics"],
        "min_company_size": 0,
        "max_company_size": 250,
        "weights": {
            "upstream_fit": 30,
            "region": 10,
            "industry": 20,
            "company_size": 5,
            "deal_value": 15,
            "engagement": 20,
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
            "upstream_fit": 15,
            "region": 15,
            "industry": 25,
            "company_size": 10,
            "deal_value": 25,
            "engagement": 10,
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
            "upstream_fit": 15,
            "region": 15,
            "industry": 25,
            "company_size": 10,
            "deal_value": 25,
            "engagement": 10,
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
            "upstream_fit": 15,
            "region": 15,
            "industry": 25,
            "company_size": 10,
            "deal_value": 20,
            "engagement": 15,
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
            "upstream_fit": 15,
            "region": 10,
            "industry": 25,
            "company_size": 10,
            "deal_value": 20,
            "engagement": 20,
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
            "upstream_fit": 15,
            "region": 15,
            "industry": 20,
            "company_size": 10,
            "deal_value": 25,
            "engagement": 15,
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
            "upstream_fit": 15,
            "region": 15,
            "industry": 25,
            "company_size": 5,
            "deal_value": 25,
            "engagement": 15,
        },
        "note": "",
    },
}


def get_qualification_profile(name: str) -> dict:
    return QUALIFICATION_PROFILES[name].copy()

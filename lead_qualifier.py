"""
AI-Assisted Lead Qualification & Revenue Prioritization Engine
--------------------------------------------------------------

A transparent commercial intelligence engine designed to:

1. Score leads using a configurable weighted model.
2. Compare leads against an Ideal Customer Profile (ICP).
3. Evaluate company-size fit instead of assuming bigger is always better.
4. Rank opportunities into priority tiers (A / B / C).
5. Explain how each component contributed to the final score.
6. Recommend the next commercial action.
7. Optionally use the Anthropic Claude API to generate:
   - a short qualification rationale
   - a localized outreach opening line

The deterministic scoring engine works independently from AI.

Without an ANTHROPIC_API_KEY, the full qualification and
prioritization workflow continues to operate normally.
"""

import argparse
import json
import os

import pandas as pd
import requests


# ----------------------------------------------------------------------
# 1. DEFAULT COMMERCIAL SCORING CONFIGURATION
# ----------------------------------------------------------------------

WEIGHTS = {
    "region": 0.20,
    "industry": 0.20,
    "company_size": 0.15,
    "deal_value": 0.25,
    "engagement": 0.20,
}

REGION_SCORES = {
    "LATAM": 100,
    "MENA": 90,
    "AFRICA": 70,
    "EU": 60,
    "NA": 50,
    "APAC": 40,
}

INDUSTRY_SCORES = {
    "Agribusiness": 100,
    "Renewable Energy": 100,
    "Government / Public Sector": 90,
    "Fintech": 85,
    "Real Estate": 80,
    "Logistics & Trade": 70,
    "Other": 30,
}

ENGAGEMENT_SCORES = {
    "hot": 100,
    "warm": 60,
    "cold": 20,
}

COMPANY_SIZE_RANGE = {
    "min": 50,
    "max": 1000,
}

TIER_THRESHOLDS = {
    "A": 75,
    "B": 50,
}

DEFAULT_FALLBACK_SCORE = 30

REQUIRED_COLUMNS = {
    "company_name",
    "country",
    "region",
    "industry",
    "estimated_deal_value_usd",
    "engagement_signal",
}


COUNTRY_LANGUAGE = {
    "Brazil": "Portuguese",
    "Portugal": "Portuguese",
    "Mexico": "Spanish",
    "Colombia": "Spanish",
    "Argentina": "Spanish",
    "Spain": "Spanish",
    "UAE": "English",
    "Saudi Arabia": "English",
    "Italy": "Italian",
    "France": "French",
    "Germany": "German",
}


# ----------------------------------------------------------------------
# 2. CONFIGURATION MANAGEMENT
# ----------------------------------------------------------------------

def validate_weights(weights):
    required = {
        "region",
        "industry",
        "company_size",
        "deal_value",
        "engagement",
    }

    missing = required - set(weights.keys())

    if missing:
        raise ValueError(
            "Missing scoring weights: "
            + ", ".join(sorted(missing))
        )

    for key, value in weights.items():
        if value < 0:
            raise ValueError(
                f"Weight '{key}' cannot be negative."
            )

    total = sum(weights.values())

    if abs(total - 1.0) > 0.001:
        raise ValueError(
            f"Scoring weights must sum to 1.0. "
            f"Current total: {total:.3f}"
        )


def validate_tier_thresholds(thresholds):
    if "A" not in thresholds or "B" not in thresholds:
        raise ValueError(
            "Tier thresholds must define both A and B."
        )

    if thresholds["A"] <= thresholds["B"]:
        raise ValueError(
            "Tier A threshold must be higher than Tier B threshold."
        )


def validate_company_size_range(size_range):
    if "min" not in size_range or "max" not in size_range:
        raise ValueError(
            "Company size configuration must define min and max."
        )

    minimum = float(size_range["min"])
    maximum = float(size_range["max"])

    if minimum < 0:
        raise ValueError(
            "Minimum company size cannot be negative."
        )

    if maximum <= 0:
        raise ValueError(
            "Maximum company size must be greater than zero."
        )

    if minimum > maximum:
        raise ValueError(
            "Minimum company size cannot exceed maximum company size."
        )


def load_scoring_config(config_path=None):
    config = {
        "weights": WEIGHTS.copy(),
        "region_scores": REGION_SCORES.copy(),
        "industry_scores": INDUSTRY_SCORES.copy(),
        "engagement_scores": ENGAGEMENT_SCORES.copy(),
        "company_size_range": COMPANY_SIZE_RANGE.copy(),
        "tier_thresholds": TIER_THRESHOLDS.copy(),
    }

    if config_path:
        with open(
            config_path,
            "r",
            encoding="utf-8",
        ) as file:
            custom_config = json.load(file)

        for key in config:
            if key in custom_config:
                if not isinstance(
                    custom_config[key],
                    dict,
                ):
                    raise ValueError(
                        f"Configuration section '{key}' "
                        "must be an object."
                    )

                config[key].update(
                    custom_config[key]
                )

    validate_weights(
        config["weights"]
    )

    validate_tier_thresholds(
        config["tier_thresholds"]
    )

    validate_company_size_range(
        config["company_size_range"]
    )

    return config


def _effective_weights(config):
    """
    Support both the new five-factor scoring model and older
    four-factor runtime configurations during migration.

    If company_size is missing, it receives zero weight so the
    previous Streamlit application continues to work until updated.
    """

    weights = config[
        "weights"
    ].copy()

    weights.setdefault(
        "company_size",
        0.0,
    )

    return weights


# ----------------------------------------------------------------------
# 3. INPUT VALIDATION
# ----------------------------------------------------------------------

def validate_input_dataframe(df):
    missing_columns = (
        REQUIRED_COLUMNS
        - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Input CSV is missing required columns: "
            + ", ".join(
                sorted(
                    missing_columns
                )
            )
        )

    if df.empty:
        raise ValueError(
            "Input CSV contains no leads."
        )

    if df[
        "estimated_deal_value_usd"
    ].isna().any():
        raise ValueError(
            "estimated_deal_value_usd contains missing values."
        )

    if (
        df[
            "estimated_deal_value_usd"
        ] < 0
    ).any():
        raise ValueError(
            "estimated_deal_value_usd cannot contain negative values."
        )

    if "company_size" in df.columns:
        if (
            pd.to_numeric(
                df["company_size"],
                errors="coerce",
            ) < 0
        ).any():
            raise ValueError(
                "company_size cannot contain negative values."
            )


# ----------------------------------------------------------------------
# 4. SCORING FUNCTIONS
# ----------------------------------------------------------------------

def score_deal_value(
    value,
    max_value,
):
    """
    Scale deal value to 0-100 relative to the largest opportunity
    in the current lead set.
    """

    if max_value <= 0:
        return 0.0

    return round(
        (
            float(value)
            / float(max_value)
        )
        * 100,
        1,
    )


def score_company_size(
    value,
    minimum,
    maximum,
):
    """
    Score company size against the active ICP range.

    A company inside the preferred range receives 100.

    Companies outside the range lose points progressively rather
    than being rejected outright.

    Examples for an ICP of 50-1000 employees:

    50 employees   -> 100
    500 employees  -> 100
    1000 employees -> 100
    40 employees   -> 80
    1200 employees -> 83.3
    2500 employees -> 40

    This avoids assuming that a larger company is automatically
    a better commercial fit.
    """

    try:
        value = float(value)
        minimum = float(minimum)
        maximum = float(maximum)
    except Exception:
        return 50.0

    if value < 0:
        return 0.0

    if minimum <= value <= maximum:
        return 100.0

    if value < minimum:
        if minimum <= 0:
            return 100.0

        score = (
            value
            / minimum
        ) * 100

        return round(
            max(
                20.0,
                min(
                    score,
                    100.0,
                ),
            ),
            1,
        )

    if value > maximum:
        if value == 0:
            return 0.0

        score = (
            maximum
            / value
        ) * 100

        return round(
            max(
                20.0,
                min(
                    score,
                    100.0,
                ),
            ),
            1,
        )

    return 50.0


def score_components(
    row,
    max_deal_value,
    config=None,
):
    """
    Calculate the complete explainable scoring breakdown.
    """

    if config is None:
        config = load_scoring_config()

    weights = _effective_weights(
        config
    )

    region_scores = config[
        "region_scores"
    ]

    industry_scores = config[
        "industry_scores"
    ]

    engagement_scores = config[
        "engagement_scores"
    ]

    company_size_range = config.get(
        "company_size_range",
        COMPANY_SIZE_RANGE,
    )

    region = str(
        row["region"]
    ).strip()

    industry = str(
        row["industry"]
    ).strip()

    engagement = str(
        row["engagement_signal"]
    ).strip().lower()

    region_score = region_scores.get(
        region,
        DEFAULT_FALLBACK_SCORE,
    )

    industry_score = industry_scores.get(
        industry,
        DEFAULT_FALLBACK_SCORE,
    )

    deal_value_score = score_deal_value(
        row[
            "estimated_deal_value_usd"
        ],
        max_deal_value,
    )

    engagement_score = engagement_scores.get(
        engagement,
        20,
    )

    if "company_size" in row.index:
        company_size_value = row[
            "company_size"
        ]
    else:
        company_size_value = None

    if (
        company_size_value is None
        or pd.isna(company_size_value)
    ):
        company_size_score = 50.0

    else:
        company_size_score = (
            score_company_size(
                company_size_value,
                company_size_range[
                    "min"
                ],
                company_size_range[
                    "max"
                ],
            )
        )

    raw_scores = {
        "region": round(
            float(region_score),
            1,
        ),
        "industry": round(
            float(industry_score),
            1,
        ),
        "company_size": round(
            float(company_size_score),
            1,
        ),
        "deal_value": round(
            float(deal_value_score),
            1,
        ),
        "engagement": round(
            float(engagement_score),
            1,
        ),
    }

    weighted_contributions = {
        key: round(
            raw_scores[key]
            * weights.get(
                key,
                0.0,
            ),
            1,
        )
        for key in raw_scores
    }

    total_score = round(
        sum(
            weighted_contributions.values()
        ),
        1,
    )

    return {
        "raw_scores": raw_scores,
        "weighted_contributions": weighted_contributions,
        "total_score": total_score,
        "company_size_range": {
            "min": company_size_range[
                "min"
            ],
            "max": company_size_range[
                "max"
            ],
        },
    }


def score_lead(
    row,
    max_deal_value,
    config=None,
):
    details = score_components(
        row,
        max_deal_value,
        config=config,
    )

    return details[
        "total_score"
    ]


def tier_for_score(
    score,
    thresholds=None,
):
    if thresholds is None:
        thresholds = (
            TIER_THRESHOLDS
        )

    if score >= thresholds[
        "A"
    ]:
        return "A"

    if score >= thresholds[
        "B"
    ]:
        return "B"

    return "C"


def recommended_action(
    score,
    tier,
    engagement_signal,
):
    engagement = str(
        engagement_signal
    ).strip().lower()

    if tier == "A":

        if engagement in {
            "hot",
            "warm",
        }:
            return (
                "Immediate personalized outreach"
            )

        return (
            "High-priority outreach with account research"
        )

    if tier == "B":

        if engagement == "hot":
            return (
                "Priority follow-up and qualification"
            )

        return (
            "Nurture and continue qualification"
        )

    if engagement == "hot":
        return (
            "Validate strategic fit before allocating resources"
        )

    return "Low-priority nurture"


def build_score_rationale(
    details,
    weights,
):
    labels = {
        "region": "Region Fit",
        "industry": "Industry Fit",
        "company_size": "Company Size Fit",
        "deal_value": "Deal Value",
        "engagement": "Engagement",
    }

    parts = []

    for key in [
        "region",
        "industry",
        "company_size",
        "deal_value",
        "engagement",
    ]:

        raw_score = details[
            "raw_scores"
        ][key]

        contribution = details[
            "weighted_contributions"
        ][key]

        weight_percent = int(
            round(
                weights.get(
                    key,
                    0.0,
                )
                * 100
            )
        )

        parts.append(
            f"{labels[key]}: "
            f"{raw_score:.1f}/100 "
            f"× {weight_percent}% "
            f"= {contribution:.1f}"
        )

    return " | ".join(
        parts
    )


def rank_leads(
    df,
    config=None,
):
    """
    Rank the complete pipeline and add transparent commercial outputs.
    """

    if config is None:
        config = (
            load_scoring_config()
        )

    validate_input_dataframe(
        df
    )

    ranked = df.copy()

    max_deal_value = ranked[
        "estimated_deal_value_usd"
    ].max()

    weights = _effective_weights(
        config
    )

    scores = []
    tiers = []
    recommendations = []
    rationales = []
    breakdowns = []

    for _, row in ranked.iterrows():

        details = score_components(
            row,
            max_deal_value,
            config=config,
        )

        score = details[
            "total_score"
        ]

        tier = tier_for_score(
            score,
            config[
                "tier_thresholds"
            ],
        )

        action = (
            recommended_action(
                score,
                tier,
                row[
                    "engagement_signal"
                ],
            )
        )

        rationale = (
            build_score_rationale(
                details,
                weights,
            )
        )

        scores.append(
            score
        )

        tiers.append(
            tier
        )

        recommendations.append(
            action
        )

        rationales.append(
            rationale
        )

        breakdowns.append(
            json.dumps(
                details,
                ensure_ascii=False,
            )
        )

    ranked[
        "score"
    ] = scores

    ranked[
        "tier"
    ] = tiers

    ranked[
        "recommended_action"
    ] = recommendations

    ranked[
        "score_rationale"
    ] = rationales

    ranked[
        "score_breakdown"
    ] = breakdowns

    ranked = (
        ranked.sort_values(
            "score",
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )

    return ranked


# ----------------------------------------------------------------------
# 5. OPTIONAL ANTHROPIC ENRICHMENT
# ----------------------------------------------------------------------

ANTHROPIC_MODEL = os.environ.get(
    "ANTHROPIC_MODEL",
    "claude-sonnet-5",
)


def generate_ai_brief(
    lead,
):
    """
    Optional CLI enrichment.

    The deterministic commercial score remains the source of truth.
    """

    api_key = os.environ.get(
        "ANTHROPIC_API_KEY"
    )

    if not api_key:
        return None

    language = COUNTRY_LANGUAGE.get(
        lead[
            "country"
        ],
        "English",
    )

    company_size = lead.get(
        "company_size",
        "Not provided",
    )

    prompt = (
        "You are a business development analyst.\n\n"
        "The deterministic commercial scoring engine has "
        "already evaluated this opportunity. "
        "Do not invent or change the score.\n\n"
        "Lead profile:\n"
        f"- Company: {lead['company_name']}\n"
        f"- Country: {lead['country']}\n"
        f"- Region: {lead['region']}\n"
        f"- Industry: {lead['industry']}\n"
        f"- Company size: {company_size} employees\n"
        f"- Estimated deal value: USD "
        f"{int(lead['estimated_deal_value_usd']):,}\n"
        f"- Engagement signal: {lead['engagement_signal']}\n"
        f"- Commercial score: {lead.get('score', 'N/A')}/100\n"
        f"- Priority tier: {lead.get('tier', 'N/A')}\n"
        f"- Recommended action: "
        f"{lead.get('recommended_action', 'N/A')}\n"
        f"- Score rationale: "
        f"{lead.get('score_rationale', 'N/A')}\n\n"
        "Respond ONLY with valid JSON.\n"
        "{"
        '"rationale": '
        '"2 concise sentences in English explaining the '
        'commercial priority without changing the score", '
        '"opening_line": '
        f'"1 short personalized outreach opening line '
        f'written in {language}"'
        "}"
    )

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 500,
                "thinking": {
                    "type": "disabled"
                },
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            },
            timeout=30,
        )

        response.raise_for_status()

        response_data = (
            response.json()
        )

        text_block = next(
            (
                block.get(
                    "text"
                )
                for block in response_data.get(
                    "content",
                    [],
                )
                if block.get(
                    "type"
                )
                == "text"
            ),
            None,
        )

        if not text_block:
            raise ValueError(
                "Anthropic response did not contain a text block."
            )

        clean_text = (
            text_block.strip()
        )

        if clean_text.startswith(
            "```"
        ):
            clean_text = (
                clean_text.strip(
                    "`"
                )
            )

            if clean_text.startswith(
                "json"
            ):
                clean_text = (
                    clean_text[
                        4:
                    ].strip()
                )

        return json.loads(
            clean_text
        )

    except Exception as exc:
        print(
            f"  [AI] Skipped for "
            f"{lead['company_name']}: "
            f"{exc}"
        )

        return None


# ----------------------------------------------------------------------
# 6. CLI PIPELINE
# ----------------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description=(
            "AI-assisted lead qualification "
            "and revenue prioritization engine"
        )
    )

    parser.add_argument(
        "--input",
        default=(
            "data/sample_leads.csv"
        ),
        help=(
            "Input CSV containing lead data"
        ),
    )

    parser.add_argument(
        "--output",
        default=(
            "exports/ranked_leads.csv"
        ),
        help=(
            "Output CSV containing qualification results"
        ),
    )

    parser.add_argument(
        "--top",
        type=int,
        default=3,
        help=(
            "Number of top-ranked leads "
            "to enrich with AI"
        ),
    )

    parser.add_argument(
        "--config",
        default=None,
        help=(
            "Optional JSON file containing "
            "custom ICP scoring configuration"
        ),
    )

    args = parser.parse_args()

    config = (
        load_scoring_config(
            args.config
        )
    )

    df = pd.read_csv(
        args.input
    )

    ranked_df = rank_leads(
        df,
        config=config,
    )

    print(
        "\n=== Ranked Leads ==="
    )

    display_columns = [
        "company_name",
        "country",
        "industry",
    ]

    if "company_size" in ranked_df.columns:
        display_columns.append(
            "company_size"
        )

    display_columns.extend(
        [
            "score",
            "tier",
            "recommended_action",
        ]
    )

    print(
        ranked_df[
            display_columns
        ].to_string(
            index=False
        )
    )

    ranked_df[
        "ai_rationale"
    ] = ""

    ranked_df[
        "ai_opening_line"
    ] = ""

    has_api_key = bool(
        os.environ.get(
            "ANTHROPIC_API_KEY"
        )
    )

    if has_api_key:

        print(
            f"\n=== AI Enrichment "
            f"(top {args.top} leads) ==="
        )

        for i in range(
            min(
                args.top,
                len(
                    ranked_df
                ),
            )
        ):

            lead = (
                ranked_df.iloc[i]
            )

            brief = (
                generate_ai_brief(
                    lead
                )
            )

            if brief:

                ranked_df.at[
                    i,
                    "ai_rationale",
                ] = brief.get(
                    "rationale",
                    "",
                )

                ranked_df.at[
                    i,
                    "ai_opening_line",
                ] = brief.get(
                    "opening_line",
                    "",
                )

    else:

        print(
            "\n[Info] ANTHROPIC_API_KEY not set "
            "- skipping optional CLI AI enrichment."
        )

    output_directory = os.path.dirname(
        args.output
    )

    if output_directory:
        os.makedirs(
            output_directory,
            exist_ok=True,
        )

    ranked_df.to_csv(
        args.output,
        index=False,
    )

    print(
        f"\nSaved ranked leads to: "
        f"{args.output}"
    )


if __name__ == "__main__":
    main()

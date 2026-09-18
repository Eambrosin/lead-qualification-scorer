"""
AI-Assisted Lead Qualification & Market Entry Scorer
-----------------------------------------------------
A small business-development tool that:

1. Scores leads using a transparent, weighted scoring model
   (region priority, industry fit, deal value, engagement level).
2. Ranks leads into priority tiers (A / B / C).
3. (Optional) Uses the Anthropic Claude API to generate, for the
   top-ranked leads, a short qualification rationale AND a localized
   outreach opening line written in the lead's likely language.

Usage:
    python lead_qualifier.py --input sample_leads.csv --output ranked_leads.csv --top 3

The AI step is fully optional. Without an ANTHROPIC_API_KEY set, the
script still runs end-to-end and produces the full ranked list using
the rule-based score only.
"""

import argparse
import os
import json
import pandas as pd
import requests


# ----------------------------------------------------------------------
# 1. SCORING CONFIGURATION
# Adjust these to match your own Ideal Customer Profile (ICP).
# Weights must sum to 1.0
# ----------------------------------------------------------------------

WEIGHTS = {
    "region": 0.25,
    "industry": 0.20,
    "deal_value": 0.30,
    "engagement": 0.25,
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

# Language used for AI-generated outreach lines, based on country.
# Falls back to English if the country isn't listed.
COUNTRY_LANGUAGE = {
    "Brazil": "Portuguese",
    "Portugal": "Portuguese",
    "Mexico": "Spanish",
    "Colombia": "Spanish",
    "Argentina": "Spanish",
    "UAE": "English",
    "Saudi Arabia": "English",
    "Italy": "Italian",
}


def score_deal_value(value, max_value):
    """Scale deal value to 0-100, relative to the largest deal in the batch."""
    if max_value == 0:
        return 0
    return round((value / max_value) * 100, 1)


def score_lead(row, max_deal_value):
    region_score = REGION_SCORES.get(row["region"], 30)
    industry_score = INDUSTRY_SCORES.get(row["industry"], 30)
    deal_score = score_deal_value(row["estimated_deal_value_usd"], max_deal_value)
    engagement_score = ENGAGEMENT_SCORES.get(str(row["engagement_signal"]).lower(), 20)

    total = (
        region_score * WEIGHTS["region"]
        + industry_score * WEIGHTS["industry"]
        + deal_score * WEIGHTS["deal_value"]
        + engagement_score * WEIGHTS["engagement"]
    )
    return round(total, 1)


def tier_for_score(score):
    if score >= 75:
        return "A"
    if score >= 50:
        return "B"
    return "C"


# ----------------------------------------------------------------------
# 2. AI ENRICHMENT (optional — requires ANTHROPIC_API_KEY)
# ----------------------------------------------------------------------

# You can override the model via the ANTHROPIC_MODEL env var.
# Check https://docs.claude.com for current model names.
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")


def generate_ai_brief(lead):
    """
    Calls the Anthropic API to generate:
      - 'rationale': a 2-sentence explanation of why this lead is a priority
      - 'opening_line': a short outreach opener in the lead's likely language

    Returns None if no API key is configured or the call fails
    (the rest of the pipeline keeps working either way).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    language = COUNTRY_LANGUAGE.get(lead["country"], "English")

    prompt = (
        "You are a business development analyst. Lead profile:\n"
        f"- Company: {lead['company_name']}\n"
        f"- Country: {lead['country']}\n"
        f"- Industry: {lead['industry']}\n"
        f"- Estimated deal value: USD {int(lead['estimated_deal_value_usd']):,}\n"
        f"- Engagement signal: {lead['engagement_signal']}\n\n"
        "Respond ONLY with valid JSON, no markdown, in this exact format:\n"
        '{"rationale": "2 sentences in English on why this lead is a priority", '
        f'"opening_line": "1 short outreach opening line written in {language}"}}'
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
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        response.raise_for_status()
        text = response.json()["content"][0]["text"]
        return json.loads(text)
    except Exception as exc:
        print(f"  [AI] Skipped for {lead['company_name']}: {exc}")
        return None


# ----------------------------------------------------------------------
# 3. MAIN PIPELINE
# ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AI-assisted lead qualification scorer")
    parser.add_argument("--input", default="sample_leads.csv", help="Input CSV with leads")
    parser.add_argument("--output", default="ranked_leads.csv", help="Output CSV with scores")
    parser.add_argument("--top", type=int, default=3, help="Number of top leads to enrich with AI")
    args = parser.parse_args()

    df = pd.read_csv(args.input)

    max_deal_value = df["estimated_deal_value_usd"].max()
    df["score"] = df.apply(lambda row: score_lead(row, max_deal_value), axis=1)
    df["tier"] = df["score"].apply(tier_for_score)
    df = df.sort_values("score", ascending=False).reset_index(drop=True)

    print("\n=== Ranked Leads ===")
    print(df[["company_name", "country", "industry", "score", "tier"]].to_string(index=False))

    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    df["ai_rationale"] = ""
    df["ai_opening_line"] = ""

    if has_api_key:
        print(f"\n=== AI Enrichment (top {args.top} leads) ===")
        for i in range(min(args.top, len(df))):
            lead = df.iloc[i]
            print(f"  -> {lead['company_name']} ({lead['country']})")
            brief = generate_ai_brief(lead)
            if brief:
                df.at[i, "ai_rationale"] = brief.get("rationale", "")
                df.at[i, "ai_opening_line"] = brief.get("opening_line", "")
                print(f"     Rationale: {brief.get('rationale')}")
                print(f"     Opening line: {brief.get('opening_line')}")
    else:
        print("\n[Info] ANTHROPIC_API_KEY not set - skipping AI enrichment step.")
        print("       export ANTHROPIC_API_KEY='your-key' to generate outreach briefs.")

    df.to_csv(args.output, index=False)
    print(f"\nSaved full ranked list to: {args.output}")


if __name__ == "__main__":
    main()
"""
AI-Assisted Lead Qualification & Revenue Prioritization Engine
--------------------------------------------------------------

A transparent commercial intelligence engine designed to:

1. Score leads using a configurable weighted model.
2. Compare leads against an Ideal Customer Profile (ICP).
3. Rank opportunities into priority tiers (A / B / C).
4. Explain how each component contributed to the final score.
5. Recommend the next commercial action.
6. Optionally use the Anthropic Claude API to generate:
   - a short qualification rationale
   - a localized outreach opening line

The rule-based scoring engine works independently from AI.

Without an ANTHROPIC_API_KEY, the full qualification and
prioritization workflow continues to operate normally.

Example usage:

    python lead_qualifier.py \
        --input sample_leads.csv \
        --output ranked_leads.csv \
        --top 3

Optional custom configuration:

    python lead_qualifier.py \
        --input sample_leads.csv \
        --output ranked_leads.csv \
        --config scoring_config.json
"""

import argparse
import json
import os

import pandas as pd
import requests


# ----------------------------------------------------------------------
# 1. DEFAULT COMMERCIAL SCORING CONFIGURATION
# ----------------------------------------------------------------------

# These defaults represent the baseline ICP.
# They can later be overridden through a JSON configuration
# or through the Streamlit interface.

WEIGHTS = {
    "region": 0.25,
    "industry": 0.20,
    "deal_value": 0.30,
    "engagement": 0.25,
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


# Language used for AI-generated outreach lines.
# Falls back to English when the country is not mapped.

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
    """
    Ensure scoring weights are valid and sum to 1.0.
    """
    required = {"region", "industry", "deal_value", "engagement"}

    missing = required - set(weights.keys())

    if missing:
        raise ValueError(
            f"Missing scoring weights: {', '.join(sorted(missing))}"
        )

    for key, value in weights.items():
        if value < 0:
            raise ValueError(
                f"Weight '{key}' cannot be negative."
            )

    total = sum(weights.values())

    if abs(total - 1.0) > 0.001:
        raise ValueError(
            f"Scoring weights must sum to 1.0. Current total: {total:.3f}"
        )


def validate_tier_thresholds(thresholds):
    """
    Ensure tier thresholds follow A > B.
    """
    if "A" not in thresholds or "B" not in thresholds:
        raise ValueError(
            "Tier thresholds must define both A and B."
        )

    if thresholds["A"] <= thresholds["B"]:
        raise ValueError(
            "Tier A threshold must be higher than Tier B threshold."
        )


def load_scoring_config(config_path=None):
    """
    Load the baseline scoring configuration.

    If a JSON configuration file is supplied, its values override
    the defaults while preserving unspecified baseline settings.
    """

    config = {
        "weights": WEIGHTS.copy(),
        "region_scores": REGION_SCORES.copy(),
        "industry_scores": INDUSTRY_SCORES.copy(),
        "engagement_scores": ENGAGEMENT_SCORES.copy(),
        "tier_thresholds": TIER_THRESHOLDS.copy(),
    }

    if config_path:
        with open(config_path, "r", encoding="utf-8") as file:
            custom_config = json.load(file)

        for key in config:
            if key in custom_config:
                if not isinstance(custom_config[key], dict):
                    raise ValueError(
                        f"Configuration section '{key}' must be an object."
                    )

                config[key].update(custom_config[key])

    validate_weights(config["weights"])
    validate_tier_thresholds(config["tier_thresholds"])

    return config


# ----------------------------------------------------------------------
# 3. INPUT VALIDATION
# ----------------------------------------------------------------------

def validate_input_dataframe(df):
    """
    Validate that the lead dataset contains the required fields.
    """

    missing_columns = REQUIRED_COLUMNS - set(df.columns)

    if missing_columns:
        raise ValueError(
            "Input CSV is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    if df.empty:
        raise ValueError("Input CSV contains no leads.")

    if df["estimated_deal_value_usd"].isna().any():
        raise ValueError(
            "estimated_deal_value_usd contains missing values."
        )

    if (df["estimated_deal_value_usd"] < 0).any():
        raise ValueError(
            "estimated_deal_value_usd cannot contain negative values."
        )


# ----------------------------------------------------------------------
# 4. SCORING ENGINE
# ----------------------------------------------------------------------

def score_deal_value(value, max_value):
    """
    Scale deal value to 0-100 relative to the largest deal
    in the current opportunity set.
    """

    if max_value <= 0:
        return 0.0

    return round((float(value) / float(max_value)) * 100, 1)


def score_components(row, max_deal_value, config=None):
    """
    Calculate the complete scoring breakdown for one lead.

    Returns raw component scores, weighted contributions
    and the final commercial score.
    """

    if config is None:
        config = load_scoring_config()

    weights = config["weights"]
    region_scores = config["region_scores"]
    industry_scores = config["industry_scores"]
    engagement_scores = config["engagement_scores"]

    region = str(row["region"]).strip()
    industry = str(row["industry"]).strip()
    engagement = str(row["engagement_signal"]).strip().lower()

    region_score = region_scores.get(
        region,
        DEFAULT_FALLBACK_SCORE,
    )

    industry_score = industry_scores.get(
        industry,
        DEFAULT_FALLBACK_SCORE,
    )

    deal_value_score = score_deal_value(
        row["estimated_deal_value_usd"],
        max_deal_value,
    )

    engagement_score = engagement_scores.get(
        engagement,
        20,
    )

    raw_scores = {
        "region": round(float(region_score), 1),
        "industry": round(float(industry_score), 1),
        "deal_value": round(float(deal_value_score), 1),
        "engagement": round(float(engagement_score), 1),
    }

    weighted_contributions = {
        key: round(raw_scores[key] * weights[key], 1)
        for key in raw_scores
    }

    total_score = round(
        sum(weighted_contributions.values()),
        1,
    )

    return {
        "raw_scores": raw_scores,
        "weighted_contributions": weighted_contributions,
        "total_score": total_score,
    }


def score_lead(row, max_deal_value, config=None):
    """
    Return the final commercial score for a lead.

    This function intentionally keeps the original interface
    compatible with existing code.
    """

    details = score_components(
        row,
        max_deal_value,
        config=config,
    )

    return details["total_score"]


def tier_for_score(score, thresholds=None):
    """
    Convert a commercial score into a priority tier.
    """

    if thresholds is None:
        thresholds = TIER_THRESHOLDS

    if score >= thresholds["A"]:
        return "A"

    if score >= thresholds["B"]:
        return "B"

    return "C"


def recommended_action(score, tier, engagement_signal):
    """
    Translate qualification results into a practical
    Business Development recommendation.
    """

    engagement = str(engagement_signal).strip().lower()

    if tier == "A":
        if engagement in {"hot", "warm"}:
            return "Immediate personalized outreach"
        return "High-priority outreach with account research"

    if tier == "B":
        if engagement == "hot":
            return "Priority follow-up and qualification"
        return "Nurture and continue qualification"

    if engagement == "hot":
        return "Validate strategic fit before allocating resources"

    return "Low-priority nurture"


def build_score_rationale(details, weights):
    """
    Produce a transparent explanation of how the score
    was calculated.
    """

    labels = {
        "region": "Region Fit",
        "industry": "Industry Fit",
        "deal_value": "Deal Value",
        "engagement": "Engagement",
    }

    parts = []

    for key in [
        "region",
        "industry",
        "deal_value",
        "engagement",
    ]:
        raw_score = details["raw_scores"][key]
        contribution = details["weighted_contributions"][key]
        weight_percent = int(round(weights[key] * 100))

        parts.append(
            f"{labels[key]}: {raw_score:.1f}/100 "
            f"× {weight_percent}% = {contribution:.1f}"
        )

    return " | ".join(parts)


def rank_leads(df, config=None):
    """
    Rank an entire lead dataframe and add:

    - commercial score
    - priority tier
    - recommended action
    - explainable scoring rationale
    - machine-readable score breakdown
    """

    if config is None:
        config = load_scoring_config()

    validate_input_dataframe(df)

    ranked = df.copy()

    max_deal_value = ranked["estimated_deal_value_usd"].max()

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

        score = details["total_score"]

        tier = tier_for_score(
            score,
            config["tier_thresholds"],
        )

        action = recommended_action(
            score,
            tier,
            row["engagement_signal"],
        )

        rationale = build_score_rationale(
            details,
            config["weights"],
        )

        scores.append(score)
        tiers.append(tier)
        recommendations.append(action)
        rationales.append(rationale)

        breakdowns.append(
            json.dumps(
                details,
                ensure_ascii=False,
            )
        )

    ranked["score"] = scores
    ranked["tier"] = tiers
    ranked["recommended_action"] = recommendations
    ranked["score_rationale"] = rationales
    ranked["score_breakdown"] = breakdowns

    ranked = ranked.sort_values(
        "score",
        ascending=False,
    ).reset_index(drop=True)

    return ranked


# ----------------------------------------------------------------------
# 5. AI ENRICHMENT
# ----------------------------------------------------------------------

# Environment variable override remains available.
#
# Example:
# export ANTHROPIC_MODEL="claude-sonnet-5"

ANTHROPIC_MODEL = os.environ.get(
    "ANTHROPIC_MODEL",
    "claude-sonnet-5",
)


def generate_ai_brief(lead):
    """
    Generate optional qualitative enrichment for a lead.

    Claude receives the deterministic commercial score and
    recommendation rather than replacing the scoring model.

    Returns:
        {
            "rationale": "...",
            "opening_line": "..."
        }

    Returns None when no API key is available or when
    the API request fails.
    """

    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        return None

    country = str(lead.get("country", "")).strip()

    language = COUNTRY_LANGUAGE.get(
        country,
        "English",
    )

    score = lead.get("score", "N/A")
    tier = lead.get("tier", "N/A")
    action = lead.get(
        "recommended_action",
        "N/A",
    )

    score_rationale = lead.get(
        "score_rationale",
        "Not available",
    )

    prompt = (
        "You are a business development analyst.\n\n"
        "The deterministic commercial scoring engine has already "
        "evaluated this opportunity. Do not invent a new score.\n\n"
        "Lead profile:\n"
        f"- Company: {lead['company_name']}\n"
        f"- Country: {lead['country']}\n"
        f"- Region: {lead['region']}\n"
        f"- Industry: {lead['industry']}\n"
        f"- Estimated deal value: USD "
        f"{int(lead['estimated_deal_value_usd']):,}\n"
        f"- Engagement signal: {lead['engagement_signal']}\n"
        f"- Commercial score: {score}/100\n"
        f"- Priority tier: {tier}\n"
        f"- Recommended action: {action}\n"
        f"- Score rationale: {score_rationale}\n\n"
        "Your role is to add qualitative commercial context "
        "to the deterministic result.\n\n"
        "Respond ONLY with valid JSON. "
        "Do not use markdown or code fences.\n\n"
        "Use exactly this format:\n"
        "{"
        '"rationale": '
        '"2 concise sentences in English explaining the commercial '
        'priority without changing the deterministic score", '
        '"opening_line": '
        f'"1 short personalized outreach opening line in {language}"'
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

        response_data = response.json()

        text_block = next(
            (
                block.get("text")
                for block in response_data.get(
                    "content",
                    [],
                )
                if block.get("type") == "text"
            ),
            None,
        )

        if not text_block:
            raise ValueError(
                "Anthropic response did not contain a text block."
            )

        clean_text = text_block.strip()

        # Defensive cleanup in case the model unexpectedly
        # returns JSON inside markdown code fences.
        if clean_text.startswith("```"):
            clean_text = clean_text.strip("`")

            if clean_text.startswith("json"):
                clean_text = clean_text[4:].strip()

        return json.loads(clean_text)

    except Exception as exc:
        print(
            f"  [AI] Skipped for "
            f"{lead['company_name']}: {exc}"
        )

        return None


# ----------------------------------------------------------------------
# 6. MAIN PIPELINE
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
        default="sample_leads.csv",
        help="Input CSV containing lead data",
    )

    parser.add_argument(
        "--output",
        default="ranked_leads.csv",
        help="Output CSV containing qualification results",
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

    config = load_scoring_config(
        args.config
    )

    df = pd.read_csv(
        args.input
    )

    ranked_df = rank_leads(
        df,
        config=config,
    )

    print("\n=== Ranked Leads ===")

    print(
        ranked_df[
            [
                "company_name",
                "country",
                "industry",
                "score",
                "tier",
                "recommended_action",
            ]
        ].to_string(index=False)
    )

    ranked_df["ai_rationale"] = ""
    ranked_df["ai_opening_line"] = ""

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
                len(ranked_df),
            )
        ):

            lead = ranked_df.iloc[i]

            print(
                f"  -> "
                f"{lead['company_name']} "
                f"({lead['country']})"
            )

            brief = generate_ai_brief(
                lead
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

                print(
                    "     Rationale: "
                    f"{brief.get('rationale')}"
                )

                print(
                    "     Opening line: "
                    f"{brief.get('opening_line')}"
                )

    else:

        print(
            "\n[Info] ANTHROPIC_API_KEY "
            "not set - skipping AI enrichment."
        )

        print(
            "       The deterministic "
            "qualification engine remains fully operational."
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

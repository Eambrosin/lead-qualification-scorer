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

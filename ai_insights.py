import os
import json
from openai import OpenAI


def _get_value(lead, key, default=""):
    try:
        value = lead.get(key, default)
    except AttributeError:
        value = default

    if value is None:
        return default

    return str(value)


def _format_money(value):
    try:
        return f"${float(value):,.0f}"
    except Exception:
        return str(value)


def _lead_context(lead):
    return {
        "company": _get_value(lead, "company", "Unknown Company"),
        "country": _get_value(lead, "country", "Unknown Country"),
        "region": _get_value(lead, "region", "Unknown Region"),
        "industry": _get_value(lead, "industry", "Unknown Industry"),
        "deal_value": _get_value(lead, "deal_value", "Unknown Deal Value"),
        "engagement_signal": _get_value(lead, "engagement_signal", "Unknown Engagement"),
        "score": _get_value(lead, "score", "Not scored"),
        "tier": _get_value(lead, "tier", "Unclassified"),
    }


def _has_api_key():
    return bool(os.getenv("OPENAI_API_KEY"))


def _client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_ai_insight(lead):
    lead_data = _lead_context(lead)

    if not _has_api_key():
        return _local_ai_insight(lead_data)

    prompt = f"""
You are an AI Business Development Strategist.

Analyze this account from a Business Development, Partnerships, Revenue and GTM perspective.

Lead:
{json.dumps(lead_data, indent=2)}

Return the analysis in this exact structure:

Account Brief:
Company:
Industry:
Market:
Tier:
Estimated Opportunity:
Engagement Signal:

Opportunity Assessment:
- Why this account matters
- Strategic relevance
- Commercial priority

Recommended GTM Angle:
- Main business angle
- Potential value proposition
- Suggested conversation theme

Discovery Questions:
1.
2.
3.
4.

Next Best Action:

Tone:
- Executive
- Commercial
- International Business Development
- Revenue-oriented
- No generic AI hype
"""

    try:
        response = _client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You help Business Development, Partnerships and GTM teams qualify accounts and prioritize revenue opportunities."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
        )

        return response.choices[0].message.content.strip()

    except Exception:
        return _local_ai_insight(lead_data)


def generate_outreach(lead):
    lead_data = _lead_context(lead)

    if not _has_api_key():
        return _local_outreach(lead_data)

    prompt = f"""
You are an expert in B2B Business Development, Partnerships, GTM and strategic outbound.

Create a premium outreach package for this account.

Lead:
{json.dumps(lead_data, indent=2)}

Return exactly this structure:

Account Brief:
- Company:
- Industry:
- Market:
- Tier:
- Commercial Priority:
- Estimated Opportunity:

Opportunity Hypothesis:
Explain why this account may be commercially relevant.

Email Subject:

Email:
Write a short, consultative email. Focus on business outcomes, growth, partnerships, revenue efficiency or market expansion. Avoid sounding like a generic SDR.

LinkedIn Message:
Write a concise connection message.

Call Opener:
Write a natural first-call opener.

Discovery Questions:
1.
2.
3.

Recommended Next Step:
Give one clear commercial next action.

Rules:
- Do not overuse the word AI.
- Do not sound technical.
- Sound like a Business Development professional using AI to improve revenue execution.
- Keep it realistic and suitable for international B2B outreach.
"""

    try:
        response = _client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You create practical, high-quality B2B outreach for Business Development, Sales, Partnerships and GTM teams."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
        )

        return response.choices[0].message.content.strip()

    except Exception:
        return _local_outreach(lead_data)


def _commercial_priority(tier):
    if tier == "A":
        return "High"
    if tier == "B":
        return "Medium"
    return "Low"


def _local_ai_insight(lead):
    company = lead["company"]
    industry = lead["industry"]
    country = lead["country"]
    region = lead["region"]
    deal_value = _format_money(lead["deal_value"])
    engagement = lead["engagement_signal"]
    score = lead["score"]
    tier = lead["tier"]
    priority = _commercial_priority(tier)

    return f"""Account Brief:
Company: {company}
Industry: {industry}
Market: {country} / {region}
Tier: {tier}
Estimated Opportunity: {deal_value}
Engagement Signal: {engagement}
Lead Score: {score}

Opportunity Assessment:
- {company} is a Tier {tier} account with {priority.lower()} commercial priority.
- The account is relevant because it operates in {industry}, a sector where commercial expansion, partnerships and pipeline prioritization can create measurable business value.
- The {engagement} engagement signal suggests this lead should be evaluated for near-term business development potential.

Recommended GTM Angle:
- Main business angle: Identify whether {company} is actively expanding, entering new markets, building partnerships or improving sales execution.
- Potential value proposition: Help the commercial team prioritize higher-value opportunities and focus resources on accounts with stronger revenue potential.
- Suggested conversation theme: Growth priorities, market expansion, partnership opportunities and pipeline efficiency.

Discovery Questions:
1. What are {company}'s main commercial growth priorities for the next 6 to 12 months?
2. Are you currently exploring new markets, channels or strategic partnerships?
3. How does your team prioritize high-value commercial opportunities today?
4. What bottlenecks exist in your current pipeline generation or lead qualification process?

Next Best Action:
Prioritize {company} for personalized outreach and use the first conversation to validate business fit, decision-making process, current growth initiatives and potential revenue timing."""


def _local_outreach(lead):
    company = lead["company"]
    industry = lead["industry"]
    country = lead["country"]
    region = lead["region"]
    deal_value = _format_money(lead["deal_value"])
    engagement = lead["engagement_signal"]
    tier = lead["tier"]
    priority = _commercial_priority(tier)

    return f"""Account Brief:
- Company: {company}
- Industry: {industry}
- Market: {country} / {region}
- Tier: {tier}
- Commercial Priority: {priority}
- Estimated Opportunity: {deal_value}

Opportunity Hypothesis:
{company} may be a relevant commercial opportunity due to its position in {industry}, its market presence in {country}, and a {engagement} engagement signal. This account should be approached around growth priorities, partnership potential, market expansion and revenue efficiency.

Email Subject:
Exploring growth priorities at {company}

Email:
Hi,

I noticed {company}'s presence in the {industry} market and wanted to reach out with a practical business development idea.

For companies expanding across {region}, one challenge is identifying which commercial opportunities deserve immediate focus and which accounts should move into a longer-term nurture motion.

Given {company}'s market profile and current engagement signal, I thought it could be relevant to exchange ideas around growth priorities, partnership opportunities and pipeline efficiency.

Would it make sense to have a short conversation to understand whether this is relevant for your team?

Best,

LinkedIn Message:
Hi, I noticed {company}'s work in {industry}. I’m interested in connecting with leaders focused on growth, partnerships and commercial expansion in {region}. Thought it would be valuable to connect.

Call Opener:
The reason I’m reaching out is that {company} appears to be a Tier {tier} account with potential commercial relevance. I wanted to better understand your current growth priorities and see whether there may be an opportunity to support pipeline prioritization, market expansion or partnership development.

Discovery Questions:
1. What are your main growth priorities over the next 6 to 12 months?
2. Are you currently evaluating new partnerships, markets or commercial channels?
3. How does your team decide which opportunities deserve immediate sales focus?

Recommended Next Step:
Schedule a short discovery conversation to validate business fit, understand current expansion priorities, identify the right stakeholder and assess whether the estimated opportunity of {deal_value} aligns with an active commercial initiative."""

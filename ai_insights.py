import json
import os

from openai import OpenAI


# ----------------------------------------------------------------------
# MODEL & LANGUAGE CONFIGURATION
# ----------------------------------------------------------------------

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
OPENAI_FALLBACK_MODEL = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4o-mini")

COUNTRY_LANGUAGE = {
    "Brazil": "Portuguese",
    "Portugal": "Portuguese",
    "Mexico": "Spanish",
    "Colombia": "Spanish",
    "Argentina": "Spanish",
    "Spain": "Spanish",
    "Italy": "Italian",
    "France": "French",
    "Germany": "German",
    "UAE": "English",
    "United Arab Emirates": "English",
    "Saudi Arabia": "English",
    "United States": "English",
    "United Kingdom": "English",
    "Singapore": "English",
    "South Africa": "English",
}


# ----------------------------------------------------------------------
# SAFE DATA HELPERS
# ----------------------------------------------------------------------

def _get_value(lead, key, default=""):
    try:
        value = lead.get(key, default)
    except AttributeError:
        value = default

    if value is None:
        return default

    return value


def _get_text(lead, key, default=""):
    value = _get_value(lead, key, default)

    if value is None:
        return default

    return str(value)


def _format_money(value):
    try:
        return f"${float(value):,.0f}"
    except Exception:
        return str(value)


def _parse_json_if_possible(value):
    """
    Accept either a dictionary/list or a JSON string.
    If parsing fails, return the original value.
    """
    if isinstance(value, (dict, list)):
        return value

    if isinstance(value, str):
        stripped = value.strip()

        if not stripped:
            return ""

        try:
            return json.loads(stripped)
        except Exception:
            return value

    return value


def _lead_context(lead):
    """
    Normalize all deterministic commercial intelligence passed
    from the scoring engine / Streamlit interface.

    New fields are optional so the AI layer remains compatible
    with older versions of the app.
    """

    country = _get_text(
        lead,
        "country",
        "Unknown Country",
    )

    return {
        "company": _get_text(
            lead,
            "company",
            "Unknown Company",
        ),
        "country": country,
        "region": _get_text(
            lead,
            "region",
            "Unknown Region",
        ),
        "industry": _get_text(
            lead,
            "industry",
            "Unknown Industry",
        ),
        "deal_value": _get_value(
            lead,
            "deal_value",
            "Unknown Deal Value",
        ),
        "engagement_signal": _get_text(
            lead,
            "engagement_signal",
            "Unknown Engagement",
        ),
        "score": _get_value(
            lead,
            "score",
            "Not scored",
        ),
        "tier": _get_text(
            lead,
            "tier",
            "Unclassified",
        ),
        "recommended_action": _get_text(
            lead,
            "recommended_action",
            "Not available",
        ),
        "score_rationale": _get_text(
            lead,
            "score_rationale",
            "Not available",
        ),
        "score_breakdown": _parse_json_if_possible(
            _get_value(
                lead,
                "score_breakdown",
                "",
            )
        ),
        "priority_regions": _parse_json_if_possible(
            _get_value(
                lead,
                "priority_regions",
                [],
            )
        ),
        "priority_industries": _parse_json_if_possible(
            _get_value(
                lead,
                "priority_industries",
                [],
            )
        ),
        "scoring_weights": _parse_json_if_possible(
            _get_value(
                lead,
                "scoring_weights",
                {},
            )
        ),
        "tier_thresholds": _parse_json_if_possible(
            _get_value(
                lead,
                "tier_thresholds",
                {},
            )
        ),
        "outreach_language": _get_text(
            lead,
            "outreach_language",
            COUNTRY_LANGUAGE.get(
                country,
                "English",
            ),
        ),
    }


# ----------------------------------------------------------------------
# OPENAI CLIENT
# ----------------------------------------------------------------------

def _has_api_key():
    return bool(os.getenv("OPENAI_API_KEY"))


def _client():
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )


def _extract_response_text(response):
    """
    Extract text from the Responses API when available.
    """

    output_text = getattr(
        response,
        "output_text",
        None,
    )

    if output_text:
        return output_text.strip()

    try:
        texts = []

        for item in response.output:
            for content in item.content:
                text = getattr(
                    content,
                    "text",
                    None,
                )

                if text:
                    texts.append(text)

        if texts:
            return "\n".join(texts).strip()

    except Exception:
        pass

    raise ValueError(
        "OpenAI response contained no text output."
    )


def _generate_openai_text(
    system_prompt,
    user_prompt,
):
    """
    Generate text using the Responses API when available.

    If the installed SDK does not expose Responses API, the function
    falls back to Chat Completions. A secondary model is also used if
    the preferred model is unavailable for the account.
    """

    client = _client()

    models_to_try = []

    for model in [
        OPENAI_MODEL,
        OPENAI_FALLBACK_MODEL,
    ]:
        if model and model not in models_to_try:
            models_to_try.append(model)

    last_error = None

    for model in models_to_try:

        try:
            if hasattr(client, "responses"):
                response = client.responses.create(
                    model=model,
                    instructions=system_prompt,
                    input=user_prompt,
                )

                return _extract_response_text(
                    response
                )

        except Exception as exc:
            last_error = exc

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
            )

            text = response.choices[0].message.content

            if text:
                return text.strip()

        except Exception as exc:
            last_error = exc

    if last_error:
        raise last_error

    raise RuntimeError(
        "No OpenAI model could generate a response."
    )


# ----------------------------------------------------------------------
# PROMPT CONTEXT
# ----------------------------------------------------------------------

def _commercial_context_block(lead_data):
    """
    Build a clear, auditable commercial context block.

    The deterministic engine remains the source of truth for:
    - score
    - tier
    - scoring rationale
    - recommended action

    The model only interprets those outputs.
    """

    context = {
        "account": {
            "company": lead_data["company"],
            "country": lead_data["country"],
            "region": lead_data["region"],
            "industry": lead_data["industry"],
            "estimated_deal_value": _format_money(
                lead_data["deal_value"]
            ),
            "engagement_signal": lead_data[
                "engagement_signal"
            ],
        },
        "deterministic_commercial_intelligence": {
            "score": lead_data["score"],
            "tier": lead_data["tier"],
            "recommended_action": lead_data[
                "recommended_action"
            ],
            "score_rationale": lead_data[
                "score_rationale"
            ],
            "score_breakdown": lead_data[
                "score_breakdown"
            ],
        },
        "active_icp": {
            "priority_regions": lead_data[
                "priority_regions"
            ],
            "priority_industries": lead_data[
                "priority_industries"
            ],
            "scoring_weights": lead_data[
                "scoring_weights"
            ],
            "tier_thresholds": lead_data[
                "tier_thresholds"
            ],
        },
        "preferred_outreach_language": lead_data[
            "outreach_language"
        ],
    }

    return json.dumps(
        context,
        indent=2,
        ensure_ascii=False,
        default=str,
    )


# ----------------------------------------------------------------------
# AI ACCOUNT INTELLIGENCE
# ----------------------------------------------------------------------

def generate_ai_insight(lead):
    lead_data = _lead_context(lead)

    if not _has_api_key():
        return _local_ai_insight(
            lead_data
        )

    context_block = _commercial_context_block(
        lead_data
    )

    system_prompt = """
You are an International Business Development and Commercial Intelligence strategist.

Your role is to interpret an existing deterministic commercial qualification result.

The deterministic scoring engine is the source of truth for the commercial score, tier, score rationale and recommended action.

Do NOT:
- invent a different score
- change the tier
- contradict the scoring rationale without clearly identifying a limitation in the available data
- pretend to know facts about the company that are not included in the supplied account data
- fabricate market research, financial data, decision makers or company initiatives

You may:
- explain what the supplied commercial signals imply
- identify reasonable business-development hypotheses
- suggest discovery questions
- recommend how a human BD professional should validate the opportunity

Keep the analysis practical, commercial, concise and executive.
Avoid generic AI language and exaggerated claims.
""".strip()

    prompt = f"""
Analyze the following account using the commercial intelligence already calculated by the scoring engine.

COMMERCIAL CONTEXT
{context_block}

Return the analysis in this exact structure:

Account Brief:
Company:
Industry:
Market:
Tier:
Commercial Score:
Estimated Opportunity:
Engagement Signal:
Recommended Action:

Opportunity Assessment:
- Explain why this account matters based only on the supplied signals
- Explain the strategic relevance of the region / industry / opportunity profile
- Explain the commercial priority without changing the deterministic score or tier

Score Interpretation:
- Summarize the strongest positive scoring factors
- Identify the weakest scoring factor or the main qualification gap
- Explain what should be validated by a human before resources are committed

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
Provide one concrete next commercial step aligned with the deterministic recommended action.

Tone:
- Executive
- Commercial
- International Business Development
- Revenue-oriented
- Evidence-aware
- No generic AI hype
""".strip()

    try:
        return _generate_openai_text(
            system_prompt,
            prompt,
        )

    except Exception:
        return _local_ai_insight(
            lead_data
        )


# ----------------------------------------------------------------------
# AI OUTREACH
# ----------------------------------------------------------------------

def generate_outreach(lead):
    lead_data = _lead_context(lead)

    if not _has_api_key():
        return _local_outreach(
            lead_data
        )

    context_block = _commercial_context_block(
        lead_data
    )

    outreach_language = lead_data[
        "outreach_language"
    ]

    system_prompt = """
You create practical, consultative B2B outreach for international Business Development, Strategic Partnerships and GTM teams.

Use the deterministic commercial intelligence supplied by the application as context.

Do not invent facts about the target company.
Do not claim that the recipient has specific projects, priorities, problems or expansion plans unless those facts are explicitly supplied.

Treat any unverified commercial angle as a hypothesis to explore, not as a fact.

The outreach must sound like a senior Business Development professional, not a mass-market SDR sequence.
""".strip()

    prompt = f"""
Create a premium B2B outreach package for this account.

COMMERCIAL CONTEXT
{context_block}

Write the Email, LinkedIn Message and Call Opener in {outreach_language}.
Keep section labels in English so the application can parse the result correctly.

Return exactly this structure:

Account Brief:
- Company:
- Industry:
- Market:
- Tier:
- Commercial Score:
- Commercial Priority:
- Estimated Opportunity:
- Recommended Action:

Opportunity Hypothesis:
Explain, without inventing company-specific facts, why the account may justify commercial discovery based on the supplied industry, region, deal value, engagement signal, ICP fit and qualification score.

Email Subject:

Email:
Write a short consultative email.
Use a natural professional tone.
Do not mention the internal lead score, tier or scoring model to the prospect.
Do not say that the company is expanding or has a problem unless that information was explicitly supplied.
Frame uncertain ideas as questions or possible areas of relevance.
Avoid generic SDR language.

LinkedIn Message:
Write a concise and natural connection message.
Do not mention the lead score or tier.

Call Opener:
Write a natural first-call opener.
Do not mention the internal score or tier.

Discovery Questions:
1.
2.
3.

Recommended Next Step:
Give one concrete internal commercial action for the BD professional.

Rules:
- Do not overuse the word AI
- Do not sound technical
- Do not fabricate research
- Do not expose internal scoring to the prospect
- Sound like an experienced international Business Development professional
- Keep the outreach realistic and suitable for B2B use
""".strip()

    try:
        return _generate_openai_text(
            system_prompt,
            prompt,
        )

    except Exception:
        return _local_outreach(
            lead_data
        )


# ----------------------------------------------------------------------
# LOCAL / NO-API FALLBACK
# ----------------------------------------------------------------------

def _commercial_priority(tier):
    if tier == "A":
        return "High"

    if tier == "B":
        return "Medium"

    return "Low"


def _qualification_gap(lead):
    engagement = str(
        lead["engagement_signal"]
    ).lower()

    if engagement == "cold":
        return (
            "Engagement is currently weak and should be validated "
            "before significant commercial resources are committed."
        )

    if engagement == "warm":
        return (
            "The opportunity shows some engagement, but timing, "
            "decision authority and active commercial need still "
            "require validation."
        )

    return (
        "The opportunity shows a strong engagement signal, but "
        "decision authority, business need and buying timeline "
        "still require validation."
    )


def _local_ai_insight(lead):
    company = lead["company"]
    industry = lead["industry"]
    country = lead["country"]
    region = lead["region"]

    deal_value = _format_money(
        lead["deal_value"]
    )

    engagement = lead[
        "engagement_signal"
    ]

    score = lead["score"]
    tier = lead["tier"]

    priority = _commercial_priority(
        tier
    )

    recommended_action = lead[
        "recommended_action"
    ]

    score_rationale = lead[
        "score_rationale"
    ]

    qualification_gap = _qualification_gap(
        lead
    )

    return f"""Account Brief:
Company: {company}
Industry: {industry}
Market: {country} / {region}
Tier: {tier}
Commercial Score: {score}
Estimated Opportunity: {deal_value}
Engagement Signal: {engagement}
Recommended Action: {recommended_action}

Opportunity Assessment:
- {company} is currently classified as a Tier {tier} opportunity with {priority.lower()} commercial priority under the active scoring model.
- The opportunity should be evaluated using its industry fit, regional fit, estimated deal value and current engagement signal rather than treated as qualified solely because of the final score.
- The deterministic engine recommends: {recommended_action}.

Score Interpretation:
- Scoring rationale: {score_rationale}
- Qualification gap: {qualification_gap}
- A human Business Development professional should validate business need, stakeholder relevance, decision authority and commercial timing before committing substantial resources.

Recommended GTM Angle:
- Main business angle: Explore whether there is a relevant commercial, partnership or market-development objective that matches the account profile.
- Potential value proposition: Focus the conversation on measurable commercial outcomes rather than technology.
- Suggested conversation theme: Current growth priorities, partnership opportunities, market-development challenges and commercial execution.

Discovery Questions:
1. What are {company}'s main commercial priorities over the next 6 to 12 months?
2. Are there specific markets, channels or partnerships currently under evaluation?
3. How does the team prioritize higher-value commercial opportunities today?
4. What would need to be true for this opportunity to become a near-term priority?

Next Best Action:
{recommended_action}. Use the next interaction to validate fit, stakeholder relevance, current need and timing."""


def _local_outreach(lead):
    company = lead["company"]
    industry = lead["industry"]
    country = lead["country"]
    region = lead["region"]

    deal_value = _format_money(
        lead["deal_value"]
    )

    engagement = lead[
        "engagement_signal"
    ]

    score = lead["score"]
    tier = lead["tier"]

    priority = _commercial_priority(
        tier
    )

    recommended_action = lead[
        "recommended_action"
    ]

    return f"""Account Brief:
- Company: {company}
- Industry: {industry}
- Market: {country} / {region}
- Tier: {tier}
- Commercial Score: {score}
- Commercial Priority: {priority}
- Estimated Opportunity: {deal_value}
- Recommended Action: {recommended_action}

Opportunity Hypothesis:
Based on the available commercial data, {company} may justify further discovery because of its {industry} profile, presence in {region}, estimated opportunity size and {engagement} engagement signal. These indicators support qualification, but they do not by themselves confirm an active project, buying need or expansion initiative.

Email Subject:
Exploring potential commercial alignment with {company}

Email:
Hi,

I came across {company} while looking at organizations operating in the {industry} space and thought it could be worthwhile to connect.

My work focuses on international business development, partnerships and commercial growth, particularly where companies are evaluating new markets, channels or strategic commercial relationships.

I do not want to assume this is currently a priority for your team, but I would be interested in understanding whether any of those areas are relevant to {company} at the moment.

Would a short introductory conversation make sense?

Best,

LinkedIn Message:
Hi, I came across {company} through the {industry} space and thought it would be useful to connect. My focus is international business development, partnerships and commercial growth, and I would be interested in learning more about your current priorities.

Call Opener:
The reason for my call is simple: I came across {company} while looking at companies in the {industry} sector, and I wanted to understand whether international growth, partnerships or broader commercial development are currently relevant areas for your team.

Discovery Questions:
1. What commercial priorities are most important for the team over the next 6 to 12 months?
2. Are new markets, channels or strategic partnerships currently being evaluated?
3. What would make an external commercial conversation genuinely useful to your team?

Recommended Next Step:
{recommended_action}. Internally, use the next interaction to validate business need, stakeholder fit, decision authority and timing before increasing commercial investment."""

from __future__ import annotations

import json

import pandas as pd

from lead_qualifier import (
    DEFAULT_FALLBACK_SCORE,
    INDUSTRY_SCORES,
    REGION_ALIASES,
    REGION_SCORES,
    ENGAGEMENT_SCORES,
    score_company_size,
    score_deal_value,
    tier_for_score,
)


COMPONENT_LABELS = {
    "upstream_fit": "Upstream Account Fit",
    "region": "Region Fit",
    "industry": "Industry Fit",
    "company_size": "Company Size Fit",
    "deal_value": "Deal Value",
    "engagement": "Engagement",
}


def _text(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def _unknown_status(row: pd.Series, field: str) -> bool:
    if field not in row.index:
        return False
    value = _text(row.get(field)).lower()
    return value in {"", "unknown", "unverified", "not qualified", "not_qualified"}


def _first_numeric(row: pd.Series, fields: list[str]) -> float | None:
    for field in fields:
        if field not in row.index:
            continue
        try:
            value = float(row.get(field))
            if pd.notna(value) and value > 0:
                return max(0.0, min(value, 100.0))
        except Exception:
            continue
    return None


def validate_integrated_dataframe(df: pd.DataFrame) -> None:
    required = {
        "company_name",
        "country",
        "region",
        "industry",
        "estimated_deal_value_usd",
        "engagement_signal",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            "Input CSV is missing required columns: "
            + ", ".join(sorted(missing))
        )
    if df.empty:
        raise ValueError("Input CSV contains no leads.")

    numeric = pd.to_numeric(df["estimated_deal_value_usd"], errors="coerce")
    known_mask = pd.Series(True, index=df.index)
    if "deal_value_status" in df.columns:
        known_mask = ~df["deal_value_status"].fillna("").astype(str).str.lower().isin(
            {"", "unknown", "unverified", "not qualified", "not_qualified"}
        )
    invalid_known = known_mask & numeric.isna()
    if invalid_known.any():
        raise ValueError(
            "Verified deal values must be numeric. Unknown deal values should use "
            "deal_value_status='unknown'."
        )
    if (numeric.fillna(0) < 0).any():
        raise ValueError("estimated_deal_value_usd cannot contain negative values.")


def score_integrated_components(
    row: pd.Series,
    max_verified_deal_value: float,
    config: dict,
) -> dict:
    weights = config["weights"].copy()
    weights.setdefault("upstream_fit", 0.30)

    region_raw = _text(row.get("region"))
    region = REGION_ALIASES.get(region_raw, region_raw)
    industry = _text(row.get("industry"))
    engagement = _text(row.get("engagement_signal")).lower()

    upstream_score = _first_numeric(
        row,
        ["account_opportunity_score", "discovery_score"],
    )

    region_score = (
        config.get("region_scores", REGION_SCORES).get(
            region,
            DEFAULT_FALLBACK_SCORE,
        )
        if region
        else None
    )

    industry_score = (
        config.get("industry_scores", INDUSTRY_SCORES).get(
            industry,
            DEFAULT_FALLBACK_SCORE,
        )
        if industry
        else None
    )

    company_size_value = row.get("company_size")
    if company_size_value is None or pd.isna(company_size_value):
        company_size_score = None
    else:
        size_range = config["company_size_range"]
        company_size_score = score_company_size(
            company_size_value,
            size_range["min"],
            size_range["max"],
        )

    deal_unknown = _unknown_status(row, "deal_value_status")
    try:
        deal_value = float(row.get("estimated_deal_value_usd"))
    except Exception:
        deal_value = 0.0

    if deal_unknown or pd.isna(deal_value) or deal_value <= 0 or max_verified_deal_value <= 0:
        deal_value_score = None
    else:
        deal_value_score = score_deal_value(
            deal_value,
            max_verified_deal_value,
        )

    engagement_unknown = _unknown_status(row, "engagement_status")
    if engagement_unknown or not engagement:
        engagement_score = None
    else:
        engagement_score = config.get(
            "engagement_scores",
            ENGAGEMENT_SCORES,
        ).get(engagement, 20)

    raw_scores = {
        "upstream_fit": upstream_score,
        "region": region_score,
        "industry": industry_score,
        "company_size": company_size_score,
        "deal_value": deal_value_score,
        "engagement": engagement_score,
    }

    active_base_weights = {
        key: float(weights.get(key, 0.0))
        for key, value in raw_scores.items()
        if value is not None and float(weights.get(key, 0.0)) > 0
    }
    active_total = sum(active_base_weights.values()) or 1.0
    effective_weights = {
        key: weight / active_total
        for key, weight in active_base_weights.items()
    }

    contributions = {
        key: (
            round(float(value) * effective_weights.get(key, 0.0), 1)
            if value is not None
            else 0.0
        )
        for key, value in raw_scores.items()
    }

    total_score = round(sum(contributions.values()), 1)
    configured_weight = sum(
        float(value) for value in weights.values() if float(value) > 0
    ) or 1.0
    available_weight = sum(active_base_weights.values())
    completeness = round(
        min(100.0, (available_weight / configured_weight) * 100),
        1,
    )

    return {
        "raw_scores": raw_scores,
        "weighted_contributions": contributions,
        "configured_weights": weights,
        "effective_weights": effective_weights,
        "unavailable_components": [
            key
            for key, value in raw_scores.items()
            if value is None and float(weights.get(key, 0.0)) > 0
        ],
        "qualification_completeness": completeness,
        "total_score": total_score,
    }


def _rationale(details: dict) -> str:
    parts = []
    effective = details["effective_weights"]
    for key in [
        "upstream_fit",
        "region",
        "industry",
        "company_size",
        "deal_value",
        "engagement",
    ]:
        value = details["raw_scores"].get(key)
        if value is None:
            parts.append(f"{COMPONENT_LABELS[key]}: not yet qualified")
            continue
        contribution = details["weighted_contributions"].get(key, 0.0)
        weight = effective.get(key, 0.0)
        parts.append(
            f"{COMPONENT_LABELS[key]}: {value:.1f}/100 × "
            f"{weight:.0%} active weight = {contribution:.1f}"
        )
    parts.append(
        f"Qualification completeness: "
        f"{details['qualification_completeness']:.0f}%"
    )
    return " | ".join(parts)


def _recommended_action(
    tier: str,
    engagement_signal: str,
    engagement_status: str,
    completeness: float,
    territory_status: str,
) -> str:
    if territory_status == "Eligibility Validation":
        return "Validate professional/device eligibility before device-specific outreach"

    if completeness < 55:
        return "Research and enrich qualification gaps"

    engagement_verified = engagement_status.lower() not in {
        "",
        "unknown",
        "unverified",
        "not qualified",
        "not_qualified",
    }

    if not engagement_verified:
        if tier == "A":
            return "High-fit account — verify decision maker and engagement"
        if tier == "B":
            return "Promising account — continue qualification"
        return "Research before allocating commercial resources"

    engagement = engagement_signal.lower()
    if tier == "A":
        return (
            "Immediate personalized outreach"
            if engagement in {"hot", "warm"}
            else "High-priority outreach with account research"
        )
    if tier == "B":
        return (
            "Priority follow-up and qualification"
            if engagement == "hot"
            else "Nurture and continue qualification"
        )
    return (
        "Validate strategic fit before allocating resources"
        if engagement == "hot"
        else "Low-priority nurture"
    )


def rank_integrated_leads(
    df: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    validate_integrated_dataframe(df)
    ranked = df.copy()

    deal_values = pd.to_numeric(
        ranked["estimated_deal_value_usd"],
        errors="coerce",
    ).fillna(0)

    verified_mask = pd.Series(True, index=ranked.index)
    if "deal_value_status" in ranked.columns:
        verified_mask = ~ranked["deal_value_status"].fillna("").astype(str).str.lower().isin(
            {"", "unknown", "unverified", "not qualified", "not_qualified"}
        )

    verified_values = deal_values[verified_mask & (deal_values > 0)]
    max_verified_deal_value = (
        float(verified_values.max())
        if not verified_values.empty
        else 0.0
    )

    scores = []
    tiers = []
    actions = []
    rationales = []
    breakdowns = []
    completeness_values = []
    qualification_statuses = []

    for _, row in ranked.iterrows():
        details = score_integrated_components(
            row,
            max_verified_deal_value,
            config,
        )
        score = details["total_score"]
        tier = tier_for_score(score, config["tier_thresholds"])
        completeness = details["qualification_completeness"]

        if completeness >= 80:
            qualification_status = "Commercially Qualified"
        elif completeness >= 55:
            qualification_status = "Partially Qualified"
        else:
            qualification_status = "Research / Enrichment Required"

        action = _recommended_action(
            tier=tier,
            engagement_signal=_text(row.get("engagement_signal")).lower(),
            engagement_status=_text(row.get("engagement_status")).lower(),
            completeness=completeness,
            territory_status=_text(row.get("territory_status")),
        )

        scores.append(score)
        tiers.append(tier)
        actions.append(action)
        rationales.append(_rationale(details))
        breakdowns.append(json.dumps(details, ensure_ascii=False))
        completeness_values.append(completeness)
        qualification_statuses.append(qualification_status)

    ranked["score"] = scores
    ranked["tier"] = tiers
    ranked["recommended_action"] = actions
    ranked["score_rationale"] = rationales
    ranked["score_breakdown"] = breakdowns
    ranked["qualification_completeness"] = completeness_values
    ranked["qualification_status"] = qualification_statuses

    return ranked.sort_values(
        ["score", "qualification_completeness"],
        ascending=[False, False],
    ).reset_index(drop=True)

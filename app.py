import html
import json
import os
import pandas as pd
import plotly.express as px
import streamlit as st

from ai_insights import generate_ai_insight, generate_outreach
from integrated_scoring import rank_integrated_leads
from lead_qualifier import load_scoring_config
from qualification_profiles import QUALIFICATION_PROFILES, get_qualification_profile


st.set_page_config(
    page_title="AI Lead Qualification & Revenue Prioritization",
    page_icon="🚀",
    layout="wide",
)

PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}

BASE_CONFIG = load_scoring_config()


def build_runtime_config(
    preferred_regions,
    preferred_industries,
    minimum_company_size,
    maximum_company_size,
    upstream_fit_priority,
    region_priority,
    industry_priority,
    company_size_priority,
    deal_value_priority,
    engagement_priority,
    tier_a_threshold,
    tier_b_threshold,
):
    """Build a runtime ICP/scoring configuration from Streamlit controls."""

    config = {
        "weights": BASE_CONFIG["weights"].copy(),
        "region_scores": BASE_CONFIG["region_scores"].copy(),
        "industry_scores": BASE_CONFIG["industry_scores"].copy(),
        "engagement_scores": BASE_CONFIG["engagement_scores"].copy(),
        "company_size_range": BASE_CONFIG["company_size_range"].copy(),
        "tier_thresholds": BASE_CONFIG["tier_thresholds"].copy(),
    }

    if minimum_company_size > maximum_company_size:
        raise ValueError(
            "Minimum company size cannot exceed maximum company size."
        )

    config["company_size_range"] = {
        "min": float(minimum_company_size),
        "max": float(maximum_company_size),
    }

    raw_priorities = {
        "upstream_fit": float(upstream_fit_priority),
        "region": float(region_priority),
        "industry": float(industry_priority),
        "company_size": float(company_size_priority),
        "deal_value": float(deal_value_priority),
        "engagement": float(engagement_priority),
    }

    total_priority = sum(raw_priorities.values())

    if total_priority <= 0:
        raise ValueError(
            "At least one scoring priority must be greater than zero."
        )

    config["weights"] = {
        key: value / total_priority
        for key, value in raw_priorities.items()
    }

    for region in preferred_regions:
        config["region_scores"][region] = 100

    for industry in preferred_industries:
        config["industry_scores"][industry] = 100

    if tier_a_threshold <= tier_b_threshold:
        raise ValueError(
            "Tier A threshold must be higher than Tier B threshold."
        )

    config["tier_thresholds"] = {
        "A": float(tier_a_threshold),
        "B": float(tier_b_threshold),
    }

    return config


def prepare_lead_for_ai(
    row,
    runtime_config,
    preferred_regions,
    preferred_industries,
):
    """Prepare deterministic commercial context for the AI layer."""

    company_size = row.get("company_size", "")

    return {
        "company": row["company_name"],
        "country": row["country"],
        "region": row["region"],
        "industry": row["industry"],
        "company_size": company_size,
        "deal_value": row["estimated_deal_value_usd"],
        "engagement_signal": row["engagement_signal"],
        "score": row["score"],
        "tier": row["tier"],
        "recommended_action": row.get("recommended_action", ""),
        "score_rationale": row.get("score_rationale", ""),
        "score_breakdown": row.get("score_breakdown", ""),
        "priority_regions": list(preferred_regions),
        "priority_industries": list(preferred_industries),
        "company_size_range": runtime_config["company_size_range"],
        "scoring_weights": runtime_config["weights"],
        "tier_thresholds": runtime_config["tier_thresholds"],
        "market_profile_id": row.get("market_profile_id", ""),
        "territory_profile_id": row.get("territory_profile_id", ""),
        "territory_region": row.get("territory_region", ""),
        "territory_province": row.get("territory_province", ""),
        "territory_city": row.get("territory_city", ""),
        "account_opportunity_score": row.get("account_opportunity_score", ""),
        "territory_status": row.get("territory_status", ""),
        "professional_setting": row.get("professional_setting", ""),
        "observed_technology_axes": row.get("observed_technology_axes", ""),
        "technology_validation_questions": row.get("technology_validation_questions", ""),
    }


def safe_filename(value):
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )


def render_ai_output(title, content, icon="📌"):
    cleaned_content = html.escape(
        str(content).strip()
    ).replace(
        "\n",
        "<br>",
    )

    st.markdown(
        f"### {icon} {title}"
    )

    st.markdown(
        f"""
<div style="
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 18px;
    background-color: #ffffff;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    white-space: pre-wrap;
    line-height: 1.6;
">{cleaned_content}</div>
        """,
        unsafe_allow_html=True,
    )


def split_sections(text):
    section_titles = [
        "Account Brief:",
        "Opportunity Assessment:",
        "Score Interpretation:",
        "Recommended GTM Angle:",
        "Opportunity Hypothesis:",
        "Email Subject:",
        "Email:",
        "LinkedIn Message:",
        "Call Opener:",
        "Discovery Questions:",
        "Recommended Next Step:",
        "Next Best Action:",
    ]

    sections = {}
    current_title = None
    current_lines = []

    for line in text.splitlines():
        stripped = line.strip()

        if stripped in section_titles:
            if current_title:
                sections[current_title] = "\n".join(
                    current_lines
                ).strip()

            current_title = stripped.replace(
                ":",
                "",
            )

            current_lines = []

        else:
            current_lines.append(
                line
            )

    if current_title:
        sections[current_title] = "\n".join(
            current_lines
        ).strip()

    return sections


def render_structured_ai_result(
    text,
    mode,
):
    sections = split_sections(
        text
    )

    if not sections:
        st.text_area(
            "Generated output",
            text,
            height=420,
        )
        return

    if "Account Brief" in sections:
        render_ai_output(
            "Account Brief",
            sections["Account Brief"],
            "📋",
        )

    if "Opportunity Assessment" in sections:
        render_ai_output(
            "Opportunity Assessment",
            sections["Opportunity Assessment"],
            "🎯",
        )

    if "Score Interpretation" in sections:
        render_ai_output(
            "Score Interpretation",
            sections["Score Interpretation"],
            "🔎",
        )

    if "Recommended GTM Angle" in sections:
        render_ai_output(
            "Recommended GTM Angle",
            sections["Recommended GTM Angle"],
            "🧭",
        )

    if "Opportunity Hypothesis" in sections:
        render_ai_output(
            "Opportunity Hypothesis",
            sections["Opportunity Hypothesis"],
            "🎯",
        )

    if "Email Subject" in sections:
        render_ai_output(
            "Email Subject",
            sections["Email Subject"],
            "✉️",
        )

    if "Email" in sections:
        render_ai_output(
            "Email Outreach",
            sections["Email"],
            "📧",
        )

    if "LinkedIn Message" in sections:
        render_ai_output(
            "LinkedIn Message",
            sections["LinkedIn Message"],
            "💼",
        )

    if "Call Opener" in sections:
        render_ai_output(
            "Call Opener",
            sections["Call Opener"],
            "📞",
        )

    if "Discovery Questions" in sections:
        render_ai_output(
            "Discovery Questions",
            sections["Discovery Questions"],
            "❓",
        )

    if "Recommended Next Step" in sections:
        render_ai_output(
            "Recommended Next Step",
            sections["Recommended Next Step"],
            "🚀",
        )

    if "Next Best Action" in sections:
        render_ai_output(
            "Next Best Action",
            sections["Next Best Action"],
            "🚀",
        )


def priority_reason(
    row,
    high_value_threshold,
):
    reasons = []

    if row["tier"] == "A":
        reasons.append(
            "Tier A account"
        )

    elif row["tier"] == "B":
        reasons.append(
            "Tier B account"
        )

    else:
        reasons.append(
            "lower-priority account"
        )

    engagement = str(
        row["engagement_signal"]
    ).lower()

    if engagement == "hot":
        reasons.append(
            "hot engagement signal"
        )

    elif engagement == "warm":
        reasons.append(
            "warm engagement signal"
        )

    if (
        row["estimated_deal_value_usd"]
        >= high_value_threshold
    ):
        reasons.append(
            "high estimated deal value"
        )

    return (
        ", ".join(reasons).capitalize()
        + "."
    )


def get_highest_risk_account(df):
    """
    Return the coldest/highest-priority account
    without relying on alphabetic sorting.
    """

    risk_rank = {
        "hot": 1,
        "warm": 2,
        "cold": 3,
    }

    risk_df = df.copy()

    risk_df["_risk_rank"] = (
        risk_df["engagement_signal"]
        .astype(str)
        .str.lower()
        .map(risk_rank)
        .fillna(2)
    )

    return risk_df.sort_values(
        [
            "_risk_rank",
            "score",
        ],
        ascending=[
            False,
            False,
        ],
    ).iloc[0]


st.title(
    "🚀 AI Lead Qualification & Revenue Prioritization"
)

st.caption(
    "Configure your Ideal Customer Profile, rank commercial opportunities, "
    "understand every score and generate AI-assisted account intelligence."
)


# ----------------------------------------------------------------------
# SIDEBAR — ICP, SCORING & AI SETTINGS
# ----------------------------------------------------------------------

with st.sidebar:

    st.header(
        "🎯 ICP & Scoring"
    )

    st.caption(
        "Configure the commercial model before uploading "
        "or reviewing your pipeline."
    )

    icp_profile_name = st.selectbox(
        "ICP preset",
        list(QUALIFICATION_PROFILES.keys()),
        help=(
            "Presets align qualification with the same market profiles used "
            "across the Commercial Intelligence suite. Every setting remains editable."
        ),
    )
    icp_profile = get_qualification_profile(icp_profile_name)
    icp_profile_id = icp_profile["profile_id"]
    icp_key = icp_profile_id.replace("/", "_")

    if icp_profile.get("note"):
        st.info(icp_profile["note"])

    region_options = list(
        BASE_CONFIG[
            "region_scores"
        ].keys()
    )

    industry_options = list(
        BASE_CONFIG[
            "industry_scores"
        ].keys()
    )

    preferred_regions = st.multiselect(
        "Priority regions",
        options=region_options,
        default=[
            region
            for region in icp_profile["preferred_regions"]
            if region in region_options
        ],
        key=f"preferred_regions_{icp_key}",
        help=(
            "Selected regions receive "
            "the maximum Region Fit score."
        ),
    )

    preferred_industries = st.multiselect(
        "Priority industries",
        options=industry_options,
        default=[
            industry
            for industry in icp_profile["preferred_industries"]
            if industry in industry_options
        ],
        key=f"preferred_industries_{icp_key}",
        help=(
            "Selected industries receive "
            "the maximum Industry Fit score."
        ),
    )

    st.markdown(
        "#### Preferred Company Size"
    )

    size_col_1, size_col_2 = (
        st.columns(2)
    )

    with size_col_1:

        minimum_company_size = (
            st.number_input(
                "Minimum employees",
                min_value=0,
                value=int(icp_profile["min_company_size"]),
                step=10,
                key=f"minimum_company_size_{icp_key}",
            )
        )

    with size_col_2:

        maximum_company_size = (
            st.number_input(
                "Maximum employees",
                min_value=1,
                value=int(icp_profile["max_company_size"]),
                step=50,
                key=f"maximum_company_size_{icp_key}",
            )
        )

    st.caption(
        "Companies inside this range receive the strongest "
        "Company Size Fit score. Companies outside the range "
        "are penalized progressively rather than rejected."
    )

    with st.expander(
        "Scoring priorities",
        expanded=True,
    ):

        st.caption(
            "The values below express relative importance. "
            "They are automatically normalized to 100%."
        )

        upstream_fit_priority = st.slider(
            "Upstream account fit",
            min_value=0,
            max_value=100,
            value=int(icp_profile["weights"].get("upstream_fit", 0)),
            step=5,
            key=f"upstream_fit_priority_{icp_key}",
            help=(
                "Uses Account Opportunity Score from Territory Intelligence "
                "or Discovery Score when available."
            ),
        )

        region_priority = st.slider(
            "Region fit",
            min_value=0,
            max_value=100,
            value=int(icp_profile["weights"]["region"]),
            step=5,
            key=f"region_priority_{icp_key}",
        )

        industry_priority = st.slider(
            "Industry fit",
            min_value=0,
            max_value=100,
            value=int(icp_profile["weights"]["industry"]),
            step=5,
            key=f"industry_priority_{icp_key}",
        )

        company_size_priority = st.slider(
            "Company size fit",
            min_value=0,
            max_value=100,
            value=int(icp_profile["weights"]["company_size"]),
            step=5,
            key=f"company_size_priority_{icp_key}",
        )

        deal_value_priority = st.slider(
            "Deal value",
            min_value=0,
            max_value=100,
            value=int(icp_profile["weights"]["deal_value"]),
            step=5,
            key=f"deal_value_priority_{icp_key}",
        )

        engagement_priority = st.slider(
            "Engagement",
            min_value=0,
            max_value=100,
            value=int(icp_profile["weights"]["engagement"]),
            step=5,
            key=f"engagement_priority_{icp_key}",
        )

    with st.expander(
        "Tier thresholds"
    ):

        tier_a_threshold = st.slider(
            "Tier A minimum score",
            min_value=55,
            max_value=95,
            value=75,
            step=1,
            key=f"tier_a_threshold_{icp_key}",
        )

        tier_b_threshold = st.slider(
            "Tier B minimum score",
            min_value=25,
            max_value=80,
            value=50,
            step=1,
            key=f"tier_b_threshold_{icp_key}",
        )

    try:

        runtime_config = (
            build_runtime_config(
                preferred_regions=(
                    preferred_regions
                ),
                preferred_industries=(
                    preferred_industries
                ),
                minimum_company_size=(
                    minimum_company_size
                ),
                maximum_company_size=(
                    maximum_company_size
                ),
                upstream_fit_priority=(
                    upstream_fit_priority
                ),
                region_priority=(
                    region_priority
                ),
                industry_priority=(
                    industry_priority
                ),
                company_size_priority=(
                    company_size_priority
                ),
                deal_value_priority=(
                    deal_value_priority
                ),
                engagement_priority=(
                    engagement_priority
                ),
                tier_a_threshold=(
                    tier_a_threshold
                ),
                tier_b_threshold=(
                    tier_b_threshold
                ),
            )
        )

    except ValueError as exc:

        st.error(
            str(exc)
        )

        st.stop()

    effective_weights = (
        runtime_config[
            "weights"
        ]
    )

    st.markdown(
        "#### Effective weights"
    )

    st.caption(
        " · ".join(
            [
                f"Upstream Fit {effective_weights.get('upstream_fit', 0):.0%}",
                f"Region {effective_weights['region']:.0%}",
                f"Industry {effective_weights['industry']:.0%}",
                f"Company Size {effective_weights['company_size']:.0%}",
                f"Deal {effective_weights['deal_value']:.0%}",
                f"Engagement {effective_weights['engagement']:.0%}",
            ]
        )
    )

    st.divider()

    st.header(
        "🤖 AI Settings"
    )

    api_key_input = st.text_input(
        "Optional OpenAI API Key",
        type="password",
        value="",
        help=(
            "Optional key for AI-assisted interpretation in this session. "
            "It is not written into the process environment."
        ),
    )

    server_api_key = os.getenv(
        "OPENAI_API_KEY",
        "",
    )

    active_api_key = (
        api_key_input
        or server_api_key
        or None
    )

    st.text_input(
        "Model",
        value=os.getenv(
            "OPENAI_MODEL",
            "gpt-5.6-luna",
        ),
        disabled=True,
    )

    if server_api_key and not api_key_input:
        st.caption(
            "A server-side AI key is configured. "
            "The deterministic scoring engine remains independent from AI."
        )
    else:
        st.caption(
            "Without an API key, the scoring and prioritization "
            "engine remains fully operational."
        )

    if active_api_key:
        st.caption(
            "When AI features are used, the selected account context is sent to OpenAI "
            "for generation. Avoid uploading or sending sensitive personal or confidential data."
        )


uploaded = st.file_uploader(
    "Upload Pipeline CSV",
    type=["csv"],
    help=(
        "Required fields: company_name, country, region, industry, "
        "estimated_deal_value_usd, engagement_signal. "
        "Recommended for Company Size Fit: company_size."
    ),
)


if uploaded is not None:

    try:

        source_df = pd.read_csv(
            uploaded
        )

        source_df[
            "estimated_deal_value_usd"
        ] = pd.to_numeric(
            source_df[
                "estimated_deal_value_usd"
            ],
            errors="coerce",
        )

        if (
            "company_size"
            in source_df.columns
        ):

            source_df[
                "company_size"
            ] = pd.to_numeric(
                source_df[
                    "company_size"
                ],
                errors="coerce",
            )

        # Backward-compatible repair for older IDENTIFY handoffs.
        # New exports already provide these fields explicitly.
        if "market_profile_id" in source_df.columns:
            medical_mask = (
                source_df["market_profile_id"]
                .fillna("")
                .astype(str)
                .str.strip()
                .eq("medical_aesthetics")
            )

            if "industry" in source_df.columns:
                missing_industry = source_df["industry"].fillna("").astype(str).str.strip().eq("")
                source_df.loc[medical_mask & missing_industry, "industry"] = "Medical Aesthetics"

            if "territory_profile_id" in source_df.columns:
                north_italy_mask = (
                    source_df["territory_profile_id"]
                    .fillna("")
                    .astype(str)
                    .str.startswith("it_north_")
                )

                if "country" in source_df.columns:
                    missing_country = source_df["country"].fillna("").astype(str).str.strip().eq("")
                    source_df.loc[north_italy_mask & missing_country, "country"] = "Italy"

                if "region" in source_df.columns:
                    missing_region = source_df["region"].fillna("").astype(str).str.strip().eq("")
                    source_df.loc[north_italy_mask & missing_region, "region"] = "EU"

        # Hold obvious documents/content pages out of commercial qualification.
        if "account_identity_status" in source_df.columns:
            identity_ready = ~source_df["account_identity_status"].fillna("").astype(str).str.contains(
                "Content / document",
                case=False,
                regex=False,
            )
            source_df = source_df[identity_ready].copy()
        else:
            content_name_mask = source_df["company_name"].fillna("").astype(str).str.lower().str.contains(
                r"(^cv\b|programma congressuale|^programma congressuale|programmi viso|^criolipolisi$|offerte di lavoro)",
                regex=True,
            )
            removed_content_rows = int(content_name_mask.sum())
            if removed_content_rows:
                st.warning(
                    f"{removed_content_rows} obvious content/document results from an older "
                    "Discovery export were excluded from commercial qualification."
                )
                source_df = source_df[~content_name_mask].copy()

        if "source_stage" in source_df.columns:
            upstream_stages = sorted(
                source_df["source_stage"].dropna().astype(str).unique().tolist()
            )
            if upstream_stages:
                st.caption(
                    "Integrated pipeline source: "
                    + ", ".join(upstream_stages)
                    + ". Upstream metadata is preserved through qualification."
                )

        if "market_profile_id" in source_df.columns:
            upstream_profiles = sorted(
                source_df["market_profile_id"]
                .dropna()
                .astype(str)
                .loc[lambda values: values.str.strip() != ""]
                .unique()
                .tolist()
            )
            if upstream_profiles:
                upstream_profile = upstream_profiles[0]
                if upstream_profile != icp_profile_id:
                    st.warning(
                        f"Upstream market profile is '{upstream_profile}', while the active "
                        f"ICP preset is '{icp_profile_id}'. Review the ICP settings before "
                        "using the resulting ranking."
                    )
                else:
                    st.success(
                        f"Market profile aligned across apps: {upstream_profile}."
                    )

        df = rank_integrated_leads(
            source_df,
            config=runtime_config,
        )

    except Exception as exc:

        st.error(
            f"Unable to process this pipeline: {exc}"
        )

        st.stop()

    # ------------------------------------------------------------------
    # EXECUTIVE SUMMARY
    # ------------------------------------------------------------------

    st.subheader(
        "📊 Executive Summary"
    )

    col1, col2, col3, col4 = (
        st.columns(4)
    )

    col1.metric(
        "Total Leads",
        len(df),
    )

    verified_deal_mask = pd.Series(True, index=df.index)
    if "deal_value_status" in df.columns:
        verified_deal_mask = ~df["deal_value_status"].fillna("").astype(str).str.lower().isin(
            ["", "unknown", "unverified"]
        )

    verified_deal_values = pd.to_numeric(
        df["estimated_deal_value_usd"],
        errors="coerce",
    ).fillna(0)
    verified_pipeline_value = verified_deal_values[verified_deal_mask].sum()

    col2.metric(
        "Qualified Pipeline Value",
        (
            "$" + f"{verified_pipeline_value:,.0f}"
            if verified_pipeline_value > 0
            else "Not qualified"
        ),
    )

    col3.metric(
        "Average Score",
        round(
            df["score"].mean(),
            1,
        ),
    )

    col4.metric(
        "Tier A Leads",
        len(
            df[
                df["tier"]
                == "A"
            ]
        ),
    )

    if "territory_region" in df.columns:
        territory_rows = df[
            df["territory_region"].fillna("").astype(str).str.strip() != ""
        ].copy()

        if not territory_rows.empty:
            st.markdown("### 🗺️ Territory Qualification View")

            tq1, tq2, tq3, tq4 = st.columns(4)
            tq1.metric("Mapped Accounts", len(territory_rows))
            tq2.metric(
                "Tier A in Territory",
                int((territory_rows["tier"] == "A").sum()),
            )
            tq3.metric(
                "Find Decision Maker",
                int(
                    (
                        territory_rows.get(
                            "territory_status",
                            pd.Series(dtype=str),
                        ).astype(str)
                        == "Find Decision Maker"
                    ).sum()
                ),
            )
            tq4.metric(
                "Eligibility Validation",
                int(
                    (
                        territory_rows.get(
                            "territory_status",
                            pd.Series(dtype=str),
                        ).astype(str)
                        == "Eligibility Validation"
                    ).sum()
                ),
            )

            territory_group = (
                territory_rows.groupby("territory_region", dropna=False)
                .agg(
                    accounts=("company_name", "count"),
                    tier_a=("tier", lambda values: int((values == "A").sum())),
                    average_score=("score", "mean"),
                )
                .reset_index()
            )
            territory_group["average_score"] = territory_group["average_score"].round(1)
            st.dataframe(
                territory_group,
                hide_index=True,
                use_container_width=True,
            )

    with st.expander(
        "⚙️ Active ICP & Scoring Model"
    ):

        model_col_1, model_col_2 = (
            st.columns(2)
        )

        with model_col_1:

            st.markdown(
                "**Priority Regions**"
            )

            st.write(
                ", ".join(
                    preferred_regions
                )
                if preferred_regions
                else "Baseline model"
            )

            st.markdown(
                "**Priority Industries**"
            )

            st.write(
                ", ".join(
                    preferred_industries
                )
                if preferred_industries
                else "Baseline model"
            )

            st.markdown(
                "**Preferred Company Size**"
            )

            st.write(
                f"{minimum_company_size:,}–"
                f"{maximum_company_size:,} employees"
            )

        with model_col_2:

            weights_df = (
                pd.DataFrame(
                    {
                        "Component": [
                            "Upstream Account Fit",
                            "Region Fit",
                            "Industry Fit",
                            "Company Size Fit",
                            "Deal Value",
                            "Engagement",
                        ],
                        "Effective Weight": [
                            effective_weights.get(
                                "upstream_fit",
                                0,
                            ),
                            effective_weights[
                                "region"
                            ],
                            effective_weights[
                                "industry"
                            ],
                            effective_weights[
                                "company_size"
                            ],
                            effective_weights[
                                "deal_value"
                            ],
                            effective_weights[
                                "engagement"
                            ],
                        ],
                    }
                )
            )

            weights_df[
                "Effective Weight"
            ] = weights_df[
                "Effective Weight"
            ].map(
                lambda value: (
                    f"{value:.0%}"
                )
            )

            st.dataframe(
                weights_df,
                hide_index=True,
                width="stretch",
            )

            st.caption(
                f"Tier A ≥ "
                f"{runtime_config['tier_thresholds']['A']:.0f} · "
                f"Tier B ≥ "
                f"{runtime_config['tier_thresholds']['B']:.0f}"
            )

    st.divider()

    # ------------------------------------------------------------------
    # EXECUTIVE ACCOUNT DASHBOARD
    # ------------------------------------------------------------------

    st.subheader(
        "👔 Executive Account Dashboard"
    )

    st.caption(
        "Executive view of the pipeline: "
        "where to focus commercial effort first."
    )

    verified_deal_accounts = df[
        verified_deal_mask
        & (
            pd.to_numeric(
                df["estimated_deal_value_usd"],
                errors="coerce",
            ).fillna(0)
            > 0
        )
    ].copy()

    top_revenue = (
        verified_deal_accounts.sort_values(
            "estimated_deal_value_usd",
            ascending=False,
        ).iloc[0]
        if not verified_deal_accounts.empty
        else None
    )

    top_partnership = (
        df.sort_values(
            ["score", "qualification_completeness"],
            ascending=[False, False],
        ).iloc[0]
    )

    expansion_regions = preferred_regions or ["LATAM", "MENA", "AFRICA"]
    top_expansion = (
        df[df["region"].isin(expansion_regions)]
        .sort_values(
            ["score", "qualification_completeness"],
            ascending=[False, False],
        )
    )
    top_expansion_account = (
        top_expansion.iloc[0]
        if len(top_expansion) > 0
        else df.sort_values(
            ["score", "qualification_completeness"],
            ascending=[False, False],
        ).iloc[0]
    )

    verified_engagement = df.copy()
    if "engagement_status" in verified_engagement.columns:
        verified_engagement = verified_engagement[
            ~verified_engagement["engagement_status"]
            .fillna("")
            .astype(str)
            .str.lower()
            .isin(["", "unknown", "unverified"])
        ]

    highest_risk = (
        get_highest_risk_account(verified_engagement)
        if not verified_engagement.empty
        else None
    )

    fastest_path = df[
        (df["tier"] == "A")
        & (
            df.get(
                "engagement_status",
                pd.Series([""] * len(df)),
            )
            .fillna("")
            .astype(str)
            .str.lower()
            .eq("verified")
        )
        & (
            df["engagement_signal"]
            .astype(str)
            .str.lower()
            .isin(["hot", "warm"])
        )
    ]

    fastest_path_account = (
        fastest_path.sort_values(
            ["score", "qualification_completeness"],
            ascending=[False, False],
        ).iloc[0]
        if len(fastest_path) > 0
        else None
    )

    exec_col_1, exec_col_2, exec_col_3 = (
        st.columns(3)
    )

    with exec_col_1:

        st.metric(
            "Top Revenue Opportunity",
            (
                top_revenue["company_name"]
                if top_revenue is not None
                else "Not qualified"
            ),
            (
                "$" + f"{top_revenue['estimated_deal_value_usd']:,.0f}"
                if top_revenue is not None
                else "Deal values unknown"
            ),
        )

        st.metric(
            "Fastest Path To Revenue",
            (
                fastest_path_account["company_name"]
                if fastest_path_account is not None
                else "Not established"
            ),
            (
                f"Score {fastest_path_account['score']}"
                if fastest_path_account is not None
                else "Engagement unverified"
            ),
        )

    with exec_col_2:

        st.metric(
            "Top Strategic Opportunity",
            top_partnership["company_name"],
            f"Tier {top_partnership['tier']}",
        )

        st.metric(
            "Top Expansion Opportunity",
            top_expansion_account["company_name"],
            top_expansion_account["region"],
        )

    with exec_col_3:

        st.metric(
            "Highest Engagement Risk",
            (
                highest_risk["company_name"]
                if highest_risk is not None
                else "Not established"
            ),
            (
                str(highest_risk["engagement_signal"]).title()
                if highest_risk is not None
                else "Engagement unverified"
            ),
        )

        tier_a_verified = df[
            (df["tier"] == "A")
            & verified_deal_mask
        ]
        tier_a_pipeline = pd.to_numeric(
            tier_a_verified["estimated_deal_value_usd"],
            errors="coerce",
        ).fillna(0).sum()

        st.metric(
            "Tier A Qualified Pipeline",
            (
                "$" + f"{tier_a_pipeline:,.0f}"
                if tier_a_pipeline > 0
                else "Not qualified"
            ),
            f"{len(df[df['tier'] == 'A'])} fit-priority accounts",
        )

    st.markdown(
        "#### Executive Interpretation"
    )

    if fastest_path_account is not None:
        st.write(
            f"**{fastest_path_account['company_name']}** currently has the clearest "
            f"commercial path because engagement is verified and its fit score is "
            f"{fastest_path_account['score']}."
        )
    else:
        st.write(
            "No account currently has a verified fast path to revenue. "
            "Prioritize contact and engagement verification before making a timing conclusion."
        )

    if top_revenue is not None:
        st.write(
            f"**{top_revenue['company_name']}** has the largest verified estimated deal "
            f"value at **$" + f"{top_revenue['estimated_deal_value_usd']:,.0f}**."
        )
    else:
        st.write(
            "Deal values are not yet qualified, so placeholder zero values are not used "
            "to identify a Top Revenue Opportunity."
        )

    st.write(
        f"For market-fit prioritization, **{top_expansion_account['company_name']}** "
        f"currently ranks highest among the configured expansion priorities, subject to "
        f"its qualification completeness."
    )

    st.divider()

    # ------------------------------------------------------------------
    # MULTI-LEAD PRIORITIZATION
    # ------------------------------------------------------------------

    st.subheader(
        "🎯 Multi-Lead Prioritization Engine"
    )

    st.caption(
        "Automatically prioritizes accounts using the configured ICP, "
        "score, tier, deal value and engagement signal."
    )

    priority_df = (
        df.head(10).copy()
    )

    high_value_threshold = (
        df[
            "estimated_deal_value_usd"
        ].quantile(
            0.75
        )
    )

    priority_df[
        "commercial_priority"
    ] = priority_df[
        "tier"
    ].map(
        {
            "A": "High",
            "B": "Medium",
            "C": "Low",
        }
    )

    priority_df[
        "why_this_account_matters"
    ] = priority_df.apply(
        lambda row: priority_reason(
            row,
            high_value_threshold,
        ),
        axis=1,
    )

    priority_columns = [
        "company_name",
        "country",
        "industry",
    ]

    if "company_size" in priority_df.columns:
        priority_columns.append(
            "company_size"
        )

    if "account_opportunity_score" in priority_df.columns:
        priority_columns.append(
            "account_opportunity_score"
        )

    priority_columns.extend(
        [
            "estimated_deal_value_usd",
            "score",
            "qualification_completeness",
            "qualification_status",
            "tier",
            "commercial_priority",
            "why_this_account_matters",
            "recommended_action",
        ]
    )

    st.dataframe(
        priority_df[
            priority_columns
        ],
        width="stretch",
    )

    priority_csv = (
        priority_df.to_csv(
            index=False
        ).encode(
            "utf-8"
        )
    )

    st.download_button(
        "⬇ Download Prioritized Accounts CSV",
        priority_csv,
        "prioritized_accounts.csv",
        "text/csv",
    )

    st.divider()

    # ------------------------------------------------------------------
    # TOP LEADS
    # ------------------------------------------------------------------

    st.subheader(
        "🏆 Top 5 Leads"
    )

    top_columns = [
        "company_name",
        "country",
        "industry",
    ]

    if "company_size" in df.columns:
        top_columns.append(
            "company_size"
        )

    if "account_opportunity_score" in df.columns:
        top_columns.append(
            "account_opportunity_score"
        )

    top_columns.extend(
        [
            "estimated_deal_value_usd",
            "engagement_signal",
        ]
    )

    if "engagement_status" in df.columns:
        top_columns.append(
            "engagement_status"
        )

    top_columns.extend(
        [
            "score",
            "qualification_completeness",
            "qualification_status",
            "tier",
            "recommended_action",
        ]
    )

    st.dataframe(
        df[
            top_columns
        ].head(5),
        width="stretch",
    )

    st.divider()

    # ------------------------------------------------------------------
    # AI LEAD INTELLIGENCE
    # ------------------------------------------------------------------

    st.subheader(
        "🤖 Lead Intelligence & Outreach"
    )

    st.caption(
        "Inspect the deterministic score first, then generate "
        "AI-assisted account intelligence and outreach assets."
    )

    selected_company = st.selectbox(
        "Select a lead",
        df[
            "company_name"
        ].tolist(),
    )

    selected_row = df[
        df[
            "company_name"
        ]
        == selected_company
    ].iloc[0]

    lead_for_ai = (
        prepare_lead_for_ai(
            selected_row,
            runtime_config,
            preferred_regions,
            preferred_industries,
        )
    )

    (
        col_profile_1,
        col_profile_2,
        col_profile_3,
        col_profile_4,
    ) = st.columns(4)

    col_profile_1.metric(
        "Selected Lead",
        selected_row[
            "company_name"
        ],
    )

    col_profile_2.metric(
        "Tier",
        selected_row[
            "tier"
        ],
    )

    col_profile_3.metric(
        "Score",
        selected_row[
            "score"
        ],
    )

    selected_deal_verified = str(
        selected_row.get("deal_value_status", "")
    ).lower() not in {"", "unknown", "unverified"}

    col_profile_4.metric(
        "Deal Value",
        (
            "$" + f"{selected_row['estimated_deal_value_usd']:,.0f}"
            if selected_deal_verified
            else "Not qualified"
        ),
    )

    # ------------------------------------------------------------------
    # LEAD INTELLIGENCE WORKSPACE
    # ------------------------------------------------------------------

    st.markdown(
        "### 🧩 Lead Intelligence Workspace"
    )

    st.caption(
        "Commercial view of the selected account "
        "before generating AI recommendations."
    )

    (
        workspace_col_1,
        workspace_col_2,
        workspace_col_3,
    ) = st.columns(3)

    with workspace_col_1:

        st.markdown(
            "#### 🏢 Company Profile"
        )

        st.write(
            f"**Company:** "
            f"{selected_row['company_name']}"
        )

        st.write(
            f"**Country:** "
            f"{selected_row['country']}"
        )

        st.write(
            f"**Region:** "
            f"{selected_row['region']}"
        )

        st.write(
            f"**Industry:** "
            f"{selected_row['industry']}"
        )

        if (
            "company_size"
            in selected_row.index
            and pd.notna(
                selected_row[
                    "company_size"
                ]
            )
        ):

            st.write(
                f"**Employees:** "
                f"{selected_row['company_size']:,.0f}"
            )

        if (
            "territory_region" in selected_row.index
            and str(selected_row.get("territory_region", "")).strip()
        ):
            st.write(
                f"**Territory:** "
                f"{selected_row.get('territory_region', '')} · "
                f"{selected_row.get('territory_province', '')} · "
                f"{selected_row.get('territory_city', '')}"
            )

        if (
            "account_opportunity_score" in selected_row.index
            and pd.notna(selected_row.get("account_opportunity_score"))
        ):
            st.write(
                f"**Upstream Account Opportunity:** "
                f"{selected_row.get('account_opportunity_score')}"
            )

        if (
            "territory_status" in selected_row.index
            and str(selected_row.get("territory_status", "")).strip()
        ):
            st.write(
                f"**Territory Status:** "
                f"{selected_row.get('territory_status')}"
            )

        if (
            "observed_technology_axes" in selected_row.index
            and str(selected_row.get("observed_technology_axes", "")).strip()
        ):
            st.write(
                f"**Observed Technology Axes:** "
                f"{selected_row.get('observed_technology_axes')}"
            )

    with workspace_col_2:

        st.markdown(
            "#### 💰 Revenue Potential"
        )

        st.write(
            "**Estimated Deal Value:** "
            + (
                "$" + f"{selected_row['estimated_deal_value_usd']:,.0f}"
                if selected_deal_verified
                else "Not yet qualified"
            )
        )

        st.write(
            f"**Qualification Completeness:** "
            f"{selected_row.get('qualification_completeness', 0):.0f}%"
        )

        st.write(
            f"**Qualification Status:** "
            f"{selected_row.get('qualification_status', '')}"
        )

        st.write(
            f"**Lead Score:** "
            f"{selected_row['score']}"
        )

        st.write(
            f"**Tier:** "
            f"{selected_row['tier']}"
        )

        engagement_verified = str(
            selected_row.get("engagement_status", "")
        ).lower() not in {"", "unknown", "unverified"}

        st.write(
            "**Engagement:** "
            + (
                str(selected_row.get("engagement_signal", "")).title()
                if engagement_verified
                else "Not yet verified"
            )
        )

    with workspace_col_3:

        st.markdown(
            "#### 🚀 Recommended Action"
        )

        if (
            selected_row[
                "tier"
            ]
            == "A"
        ):

            st.success(
                selected_row[
                    "recommended_action"
                ]
            )

        elif (
            selected_row[
                "tier"
            ]
            == "B"
        ):

            st.info(
                selected_row[
                    "recommended_action"
                ]
            )

        else:

            st.warning(
                selected_row[
                    "recommended_action"
                ]
            )

    # ------------------------------------------------------------------
    # EXPLAINABLE SCORE
    # ------------------------------------------------------------------

    st.markdown(
        "#### 🔎 Explainable Score"
    )

    st.caption(
        "Every score is generated by the deterministic commercial model. "
        "AI does not set or modify the score."
    )

    try:

        score_breakdown = (
            json.loads(
                selected_row[
                    "score_breakdown"
                ]
            )
        )

        contribution_map = (
            score_breakdown[
                "weighted_contributions"
            ]
        )

        raw_score_map = (
            score_breakdown[
                "raw_scores"
            ]
        )

        component_labels = {
            "upstream_fit": "Upstream Account Fit",
            "region": "Region Fit",
            "industry": "Industry Fit",
            "company_size": "Company Size Fit",
            "deal_value": "Deal Value",
            "engagement": "Engagement",
        }

        effective_row_weights = score_breakdown.get("effective_weights", {})

        breakdown_df = pd.DataFrame([
            {
                "Component": label,
                "Raw Score": (raw_score_map.get(key) if raw_score_map.get(key) is not None else "Not qualified"),
                "Weight": effective_row_weights.get(key, 0),
                "Weighted Contribution": contribution_map.get(key, 0),
            }
            for key, label in component_labels.items()
        ])

        breakdown_display = (
            breakdown_df.copy()
        )

        breakdown_display[
            "Weight"
        ] = breakdown_display[
            "Weight"
        ].map(
            lambda value: (
                f"{value:.0%}"
            )
        )

        (
            breakdown_col_1,
            breakdown_col_2,
        ) = st.columns(
            [
                1,
                1.2,
            ]
        )

        with breakdown_col_1:

            st.dataframe(
                breakdown_display,
                hide_index=True,
                width="stretch",
            )

        with breakdown_col_2:

            fig_breakdown = (
                px.bar(
                    breakdown_df,
                    x="Component",
                    y="Weighted Contribution",
                    title=(
                        "Contribution to Final Score"
                    ),
                )
            )

            st.plotly_chart(
                fig_breakdown,
                config=PLOTLY_CONFIG,
            )

        st.caption(
            selected_row[
                "score_rationale"
            ]
        )

    except Exception:

        st.info(
            "Score breakdown is not available for this account."
        )

    # ------------------------------------------------------------------
    # COMMERCIAL INTERPRETATION
    # ------------------------------------------------------------------

    st.markdown(
        "#### 🧠 Commercial Interpretation"
    )

    (
        interpretation_col_1,
        interpretation_col_2,
        interpretation_col_3,
    ) = st.columns(3)

    with interpretation_col_1:

        st.markdown(
            "**Why This Lead Matters**"
        )

        st.write(
            f"{selected_row['company_name']} operates in "
            f"{selected_row['industry']} and currently ranks as a "
            f"Tier {selected_row['tier']} opportunity with a "
            f"score of {selected_row['score']}."
        )

    with interpretation_col_2:

        st.markdown(
            "**Commercial Motion**"
        )

        st.write(
            selected_row[
                "recommended_action"
            ]
        )

    with interpretation_col_3:

        st.markdown(
            "**Engagement Risk**"
        )

        engagement = str(
            selected_row.get("engagement_signal", "")
        ).lower()
        engagement_verified = str(
            selected_row.get("engagement_status", "")
        ).lower() not in {"", "unknown", "unverified"}

        if not engagement_verified:
            st.write(
                "Engagement has not been verified yet. "
                "The application does not infer engagement risk from a discovery placeholder."
            )
        elif engagement == "hot":
            st.write(
                "Low engagement risk. "
                "The account shows a strong buying or partnership signal."
            )
        elif engagement == "warm":
            st.write(
                "Moderate engagement risk. "
                "The account may require additional nurturing."
            )
        else:
            st.write(
                "Higher engagement risk based on the verified engagement signal."
            )

    st.divider()

    # ------------------------------------------------------------------
    # AI TABS
    # ------------------------------------------------------------------

    tab_1, tab_2 = st.tabs(
        [
            "🧠 Account Intelligence",
            "📨 Outreach Sequence",
        ]
    )

    with tab_1:

        if st.button(
            "Generate AI Insight"
        ):

            insight = (
                generate_ai_insight(
                    lead_for_ai,
                    api_key=active_api_key,
                )
            )

            render_structured_ai_result(
                insight,
                mode="insight",
            )

            st.caption(
                "Generated output is kept in memory and can be downloaded below."
            )

            st.download_button(
                "⬇ Download AI Insight",
                insight,
                file_name=(
                    f"{safe_filename(selected_row['company_name'])}"
                    "_ai_insight.txt"
                ),
                mime="text/plain",
            )

    with tab_2:

        if st.button(
            "Generate Outreach Sequence"
        ):

            outreach = (
                generate_outreach(
                    lead_for_ai,
                    api_key=active_api_key,
                )
            )

            render_structured_ai_result(
                outreach,
                mode="outreach",
            )

            st.caption(
                "Generated output is kept in memory and can be downloaded below."
            )

            st.download_button(
                "⬇ Download Outreach Sequence",
                outreach,
                file_name=(
                    f"{safe_filename(selected_row['company_name'])}"
                    "_outreach_sequence.txt"
                ),
                mime="text/plain",
            )

    st.divider()

    # ------------------------------------------------------------------
    # ANALYTICS
    # ------------------------------------------------------------------

    st.subheader(
        "⭐ Lead Scores"
    )

    fig_scores = px.bar(
        df,
        x="company_name",
        y="score",
        color="tier",
        title="Lead Ranking by Score",
    )

    st.plotly_chart(
        fig_scores,
        config=PLOTLY_CONFIG,
    )

    col_left, col_right = (
        st.columns(2)
    )

    with col_left:

        st.subheader(
            "🏭 Industry Distribution"
        )

        fig_industry = (
            px.pie(
                df,
                names="industry",
                title=(
                    "Leads by Industry"
                ),
            )
        )

        st.plotly_chart(
            fig_industry,
            config=PLOTLY_CONFIG,
        )

    with col_right:

        st.subheader(
            "💰 Revenue by Tier"
        )

        revenue_by_tier = (
            df.groupby(
                "tier"
            )[
                "estimated_deal_value_usd"
            ]
            .sum()
            .reset_index()
        )

        fig_revenue = (
            px.bar(
                revenue_by_tier,
                x="tier",
                y=(
                    "estimated_deal_value_usd"
                ),
                title=(
                    "Revenue Potential by Tier"
                ),
            )
        )

        st.plotly_chart(
            fig_revenue,
            config=PLOTLY_CONFIG,
        )

    st.divider()

    st.subheader(
        "🌍 Leads by Country"
    )

    country_df = (
        df[
            "country"
        ]
        .value_counts()
        .reset_index()
    )

    country_df.columns = [
        "country",
        "count",
    ]

    fig_country = (
        px.bar(
            country_df,
            x="country",
            y="count",
            title=(
                "Leads by Country"
            ),
        )
    )

    st.plotly_chart(
        fig_country,
        config=PLOTLY_CONFIG,
    )

    st.divider()

    # ------------------------------------------------------------------
    # ENGAGE HANDOFF
    # ------------------------------------------------------------------

    st.subheader(
        "🔗 Continue to ENGAGE"
    )

    st.caption(
        "Export the complete qualified pipeline for the Adaptive Outreach Intelligence app. "
        "Market-profile, contact and public-source metadata are preserved when available."
    )

    engage_handoff = df.copy()
    engage_handoff["schema_version"] = "1.0"
    engage_handoff["source_stage"] = "PRIORITIZE"

    st.download_button(
        "⬇ Download ENGAGE Handoff CSV",
        engage_handoff.to_csv(index=False).encode("utf-8"),
        "engage_handoff.csv",
        "text/csv",
    )

    st.link_button(
        "Open ENGAGE — Adaptive Outreach",
        "https://outreach-sequence-generator-7dcmglcxfnmszlodg8lqre.streamlit.app/",
        use_container_width=True,
    )

    st.divider()

    # ------------------------------------------------------------------
    # FULL PIPELINE
    # ------------------------------------------------------------------

    st.subheader(
        "📋 Full Ranked Pipeline"
    )

    st.dataframe(
        df,
        width="stretch",
    )

    csv = (
        df.to_csv(
            index=False
        ).encode(
            "utf-8"
        )
    )

    st.download_button(
        "⬇ Download Ranked Leads CSV",
        csv,
        "ranked_leads.csv",
        "text/csv",
    )


else:

    st.info(
        "Upload data/sample_leads.csv "
        "or exports/ranked_leads.csv to begin."
    )

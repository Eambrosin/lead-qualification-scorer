import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from ai_insights import generate_ai_insight, generate_outreach
from lead_qualifier import (
    ENGAGEMENT_SCORES,
    INDUSTRY_SCORES,
    REGION_SCORES,
    TIER_THRESHOLDS,
    WEIGHTS,
    load_scoring_config,
    rank_leads,
)


# ----------------------------------------------------------------------
# PAGE CONFIGURATION
# ----------------------------------------------------------------------

st.set_page_config(
    page_title="AI Lead Qualification Dashboard",
    page_icon="🚀",
    layout="wide",
)

PLOTLY_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
}

EXPORTS_DIR = Path("exports")
EXPORTS_DIR.mkdir(exist_ok=True)


# ----------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------

def safe_filename(value):
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )


def save_ai_output(
    company_name,
    output_type,
    content,
):
    filename = (
        f"{safe_filename(company_name)}_"
        f"{output_type}.txt"
    )

    path = EXPORTS_DIR / filename

    path.write_text(
        content,
        encoding="utf-8",
    )

    return path


def prepare_lead_for_ai(
    row,
    runtime_config,
    preferred_regions,
    preferred_industries,
):
    """
    Prepare deterministic commercial context
    for the AI intelligence layer.
    """

    return {
        "company": row["company_name"],
        "country": row["country"],
        "region": row["region"],
        "industry": row["industry"],
        "deal_value": row[
            "estimated_deal_value_usd"
        ],
        "engagement_signal": row[
            "engagement_signal"
        ],
        "score": row["score"],
        "tier": row["tier"],
        "recommended_action": row.get(
            "recommended_action",
            "",
        ),
        "score_rationale": row.get(
            "score_rationale",
            "",
        ),
        "score_breakdown": row.get(
            "score_breakdown",
            "",
        ),
        "priority_regions": list(
            preferred_regions
        ),
        "priority_industries": list(
            preferred_industries
        ),
        "scoring_weights": runtime_config[
            "weights"
        ],
        "tier_thresholds": runtime_config[
            "tier_thresholds"
        ],
    }


def render_ai_output(
    title,
    content,
    icon="📌",
):
    cleaned_content = str(
        content
    ).strip()

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
                sections[
                    current_title
                ] = "\n".join(
                    current_lines
                ).strip()

            current_title = (
                stripped.replace(
                    ":",
                    "",
                )
            )

            current_lines = []

        else:
            current_lines.append(
                line
            )

    if current_title:
        sections[
            current_title
        ] = "\n".join(
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
            sections[
                "Opportunity Assessment"
            ],
            "🎯",
        )

    if "Score Interpretation" in sections:
        render_ai_output(
            "Score Interpretation",
            sections[
                "Score Interpretation"
            ],
            "🔎",
        )

    if "Recommended GTM Angle" in sections:
        render_ai_output(
            "Recommended GTM Angle",
            sections[
                "Recommended GTM Angle"
            ],
            "🧭",
        )

    if "Opportunity Hypothesis" in sections:
        render_ai_output(
            "Opportunity Hypothesis",
            sections[
                "Opportunity Hypothesis"
            ],
            "🎯",
        )

    if "Email Subject" in sections:
        render_ai_output(
            "Email Subject",
            sections[
                "Email Subject"
            ],
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
            sections[
                "LinkedIn Message"
            ],
            "💼",
        )

    if "Call Opener" in sections:
        render_ai_output(
            "Call Opener",
            sections[
                "Call Opener"
            ],
            "📞",
        )

    if "Discovery Questions" in sections:
        render_ai_output(
            "Discovery Questions",
            sections[
                "Discovery Questions"
            ],
            "❓",
        )

    if "Recommended Next Step" in sections:
        render_ai_output(
            "Recommended Next Step",
            sections[
                "Recommended Next Step"
            ],
            "🚀",
        )

    if "Next Best Action" in sections:
        render_ai_output(
            "Next Best Action",
            sections[
                "Next Best Action"
            ],
            "🚀",
        )


def normalized_weights(
    region,
    industry,
    deal_value,
    engagement,
):
    raw = {
        "region": region,
        "industry": industry,
        "deal_value": deal_value,
        "engagement": engagement,
    }

    total = sum(
        raw.values()
    )

    if total <= 0:
        return WEIGHTS.copy()

    return {
        key: value / total
        for key, value in raw.items()
    }


def build_runtime_config(
    preferred_regions,
    preferred_industries,
    weights,
    tier_a_threshold,
    tier_b_threshold,
):
    config = load_scoring_config()

    config["weights"] = (
        weights.copy()
    )

    config[
        "tier_thresholds"
    ] = {
        "A": tier_a_threshold,
        "B": tier_b_threshold,
    }

    region_scores = {
        region: (
            100
            if region
            in preferred_regions
            else 40
        )
        for region
        in REGION_SCORES
    }

    industry_scores = {
        industry: (
            100
            if industry
            in preferred_industries
            else 40
        )
        for industry
        in INDUSTRY_SCORES
    }

    config[
        "region_scores"
    ].update(
        region_scores
    )

    config[
        "industry_scores"
    ].update(
        industry_scores
    )

    config[
        "engagement_scores"
    ] = (
        ENGAGEMENT_SCORES.copy()
    )

    return config


def format_score_breakdown(
    score_breakdown,
    weights,
):
    try:
        details = json.loads(
            score_breakdown
        )
    except Exception:
        return pd.DataFrame()

    labels = {
        "region": "Region Fit",
        "industry": "Industry Fit",
        "deal_value": "Deal Value",
        "engagement": "Engagement",
    }

    rows = []

    for key in [
        "region",
        "industry",
        "deal_value",
        "engagement",
    ]:

        rows.append(
            {
                "Component": labels[key],
                "Raw Score": details[
                    "raw_scores"
                ].get(
                    key,
                    0,
                ),
                "Weight": (
                    f"{weights[key] * 100:.0f}%"
                ),
                "Weighted Contribution": details[
                    "weighted_contributions"
                ].get(
                    key,
                    0,
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


# ----------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------

st.title(
    "🚀 AI Lead Qualification & Revenue Prioritization"
)

st.caption(
    "Configure your Ideal Customer Profile, upload a lead pipeline "
    "and turn commercial data into transparent priorities, "
    "recommended actions and AI-assisted account intelligence."
)


# ----------------------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------------------

with st.sidebar:

    st.header(
        "🎯 ICP & Scoring"
    )

    st.caption(
        "Configure the commercial profile "
        "the qualification engine should prioritize."
    )

    preferred_regions = st.multiselect(
        "Priority Regions",
        options=list(
            REGION_SCORES.keys()
        ),
        default=[
            "LATAM",
            "MENA",
        ],
    )

    preferred_industries = (
        st.multiselect(
            "Priority Industries",
            options=list(
                INDUSTRY_SCORES.keys()
            ),
            default=[
                "Agribusiness",
                "Renewable Energy",
                "Government / Public Sector",
            ],
        )
    )

    st.markdown(
        "#### Scoring Weights"
    )

    region_weight = st.slider(
        "Region Fit",
        min_value=0,
        max_value=100,
        value=int(
            WEIGHTS["region"]
            * 100
        ),
    )

    industry_weight = st.slider(
        "Industry Fit",
        min_value=0,
        max_value=100,
        value=int(
            WEIGHTS["industry"]
            * 100
        ),
    )

    deal_weight = st.slider(
        "Deal Value",
        min_value=0,
        max_value=100,
        value=int(
            WEIGHTS["deal_value"]
            * 100
        ),
    )

    engagement_weight = st.slider(
        "Engagement",
        min_value=0,
        max_value=100,
        value=int(
            WEIGHTS["engagement"]
            * 100
        ),
    )

    weights = normalized_weights(
        region_weight,
        industry_weight,
        deal_weight,
        engagement_weight,
    )

    st.caption(
        "Weights are automatically normalized to 100%."
    )

    st.markdown(
        "#### Tier Thresholds"
    )

    tier_a_threshold = st.slider(
        "Tier A minimum score",
        min_value=51,
        max_value=100,
        value=int(
            TIER_THRESHOLDS["A"]
        ),
    )

    tier_b_threshold = st.slider(
        "Tier B minimum score",
        min_value=1,
        max_value=(
            tier_a_threshold - 1
        ),
        value=min(
            int(
                TIER_THRESHOLDS["B"]
            ),
            tier_a_threshold - 1,
        ),
    )

    st.divider()

    st.header(
        "⚙️ AI Settings"
    )

    api_key_input = st.text_input(
        "OpenAI API Key",
        type="password",
        value=os.getenv(
            "OPENAI_API_KEY",
            "",
        ),
    )

    if api_key_input:
        os.environ[
            "OPENAI_API_KEY"
        ] = api_key_input

    st.text_input(
        "Model",
        value=os.getenv(
            "OPENAI_MODEL",
            "gpt-5.6-luna",
        ),
        disabled=True,
    )

    st.caption(
        "Without an API key, the application "
        "uses local commercial intelligence templates."
    )


runtime_config = build_runtime_config(
    preferred_regions,
    preferred_industries,
    weights,
    tier_a_threshold,
    tier_b_threshold,
)


# ----------------------------------------------------------------------
# FILE UPLOAD
# ----------------------------------------------------------------------

uploaded = st.file_uploader(
    "Upload Pipeline CSV",
    type=["csv"],
)


if uploaded is not None:

    try:
        input_df = pd.read_csv(
            uploaded
        )

        df = rank_leads(
            input_df,
            config=runtime_config,
        )

    except Exception as exc:
        st.error(
            f"Unable to process the CSV: {exc}"
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

    col2.metric(
        "Pipeline Value",
        f"${df['estimated_deal_value_usd'].sum():,.0f}",
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
                df["tier"] == "A"
            ]
        ),
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

    top_revenue = (
        df.sort_values(
            "estimated_deal_value_usd",
            ascending=False,
        ).iloc[0]
    )

    top_priority = (
        df.sort_values(
            "score",
            ascending=False,
        ).iloc[0]
    )

    top_expansion = df[
        df["region"].isin(
            preferred_regions
        )
    ].sort_values(
        "score",
        ascending=False,
    )

    if len(
        top_expansion
    ) > 0:
        top_expansion_account = (
            top_expansion.iloc[0]
        )
    else:
        top_expansion_account = (
            top_priority
        )

    risk_map = {
        "hot": 1,
        "warm": 2,
        "cold": 3,
    }

    df[
        "_engagement_risk"
    ] = (
        df[
            "engagement_signal"
        ]
        .astype(str)
        .str.lower()
        .map(risk_map)
        .fillna(3)
    )

    highest_risk = (
        df.sort_values(
            [
                "_engagement_risk",
                "score",
            ],
            ascending=[
                False,
                False,
            ],
        ).iloc[0]
    )

    fastest_path = df[
        (
            df["tier"] == "A"
        )
        &
        (
            df[
                "engagement_signal"
            ]
            .astype(str)
            .str.lower()
            == "hot"
        )
    ]

    if len(
        fastest_path
    ) > 0:

        fastest_path_account = (
            fastest_path
            .sort_values(
                "score",
                ascending=False,
            )
            .iloc[0]
        )

    else:

        fastest_path_account = (
            top_priority
        )

    exec_col_1, exec_col_2, exec_col_3 = (
        st.columns(3)
    )

    with exec_col_1:

        st.metric(
            "Top Revenue Opportunity",
            top_revenue[
                "company_name"
            ],
            f"${top_revenue['estimated_deal_value_usd']:,.0f}",
        )

        st.metric(
            "Fastest Path To Revenue",
            fastest_path_account[
                "company_name"
            ],
            f"Score {fastest_path_account['score']}",
        )

    with exec_col_2:

        st.metric(
            "Top Commercial Priority",
            top_priority[
                "company_name"
            ],
            f"Tier {top_priority['tier']}",
        )

        st.metric(
            "Top Expansion Opportunity",
            top_expansion_account[
                "company_name"
            ],
            top_expansion_account[
                "region"
            ],
        )

    with exec_col_3:

        st.metric(
            "Highest Engagement Risk",
            highest_risk[
                "company_name"
            ],
            str(
                highest_risk[
                    "engagement_signal"
                ]
            ).title(),
        )

        tier_a_pipeline = (
            df[
                df["tier"] == "A"
            ][
                "estimated_deal_value_usd"
            ].sum()
        )

        st.metric(
            "Tier A Pipeline",
            f"${tier_a_pipeline:,.0f}",
            f"{len(df[df['tier'] == 'A'])} accounts",
        )

    st.markdown(
        "#### Executive Interpretation"
    )

    st.write(
        f"Focus initial commercial effort on "
        f"**{fastest_path_account['company_name']}**. "
        f"The current model classifies this account as "
        f"Tier {fastest_path_account['tier']} with a score of "
        f"**{fastest_path_account['score']}** and recommends "
        f"**{fastest_path_account['recommended_action']}**."
    )

    st.write(
        f"From a revenue perspective, "
        f"**{top_revenue['company_name']}** represents "
        f"the largest estimated opportunity at "
        f"**${top_revenue['estimated_deal_value_usd']:,.0f}**."
    )

    st.write(
        f"For the active ICP, "
        f"**{top_expansion_account['company_name']}** "
        f"is the strongest expansion-oriented account "
        f"among the currently preferred regions."
    )

    st.divider()

    # ------------------------------------------------------------------
    # PRIORITIZATION ENGINE
    # ------------------------------------------------------------------

    st.subheader(
        "🎯 Multi-Lead Prioritization Engine"
    )

    st.caption(
        "Ranks accounts using the active ICP, "
        "transparent scoring weights and deterministic "
        "commercial recommendations."
    )

    priority_df = (
        df.head(10).copy()
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
    ] = priority_df[
        "score_rationale"
    ]

    st.dataframe(
        priority_df[
            [
                "company_name",
                "country",
                "industry",
                "estimated_deal_value_usd",
                "score",
                "tier",
                "commercial_priority",
                "recommended_action",
            ]
        ],
        width="stretch",
    )

    priority_csv = (
        priority_df
        .drop(
            columns=[
                "_engagement_risk"
            ],
            errors="ignore",
        )
        .to_csv(
            index=False
        )
        .encode(
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

    st.dataframe(
        df[
            [
                "company_name",
                "country",
                "industry",
                "estimated_deal_value_usd",
                "engagement_signal",
                "score",
                "tier",
                "recommended_action",
            ]
        ].head(5),
        width="stretch",
    )

    st.divider()

    # ------------------------------------------------------------------
    # AI LEAD INTELLIGENCE
    # ------------------------------------------------------------------

    st.subheader(
        "🤖 AI Lead Insights & Outreach"
    )

    st.caption(
        "Interpret deterministic commercial intelligence "
        "and generate account strategy and outreach."
    )

    selected_company = (
        st.selectbox(
            "Select a lead",
            df[
                "company_name"
            ].tolist(),
        )
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

    col_profile_4.metric(
        "Deal Value",
        f"${selected_row['estimated_deal_value_usd']:,.0f}",
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

    with workspace_col_2:

        st.markdown(
            "#### 💰 Revenue Potential"
        )

        st.write(
            f"**Estimated Deal Value:** "
            f"${selected_row['estimated_deal_value_usd']:,.0f}"
        )

        st.write(
            f"**Lead Score:** "
            f"{selected_row['score']}"
        )

        st.write(
            f"**Tier:** "
            f"{selected_row['tier']}"
        )

        st.write(
            f"**Engagement:** "
            f"{selected_row['engagement_signal']}"
        )

    with workspace_col_3:

        st.markdown(
            "#### 🚀 Recommended Motion"
        )

        action = (
            selected_row[
                "recommended_action"
            ]
        )

        if selected_row[
            "tier"
        ] == "A":

            st.success(
                action
            )

        elif selected_row[
            "tier"
        ] == "B":

            st.info(
                action
            )

        else:

            st.warning(
                action
            )

    # ------------------------------------------------------------------
    # EXPLAINABLE SCORE
    # ------------------------------------------------------------------

    st.markdown(
        "### 🔎 Explainable Score"
    )

    st.caption(
        "See exactly how each commercial factor "
        "contributed to the final qualification score."
    )

    breakdown_df = (
        format_score_breakdown(
            selected_row[
                "score_breakdown"
            ],
            runtime_config[
                "weights"
            ],
        )
    )

    if not breakdown_df.empty:

        breakdown_col_1, breakdown_col_2 = (
            st.columns(
                [1.4, 1]
            )
        )

        with breakdown_col_1:

            st.dataframe(
                breakdown_df,
                width="stretch",
                hide_index=True,
            )

        with breakdown_col_2:

            fig_breakdown = px.bar(
                breakdown_df,
                x="Component",
                y="Weighted Contribution",
                title="Score Contribution",
            )

            st.plotly_chart(
                fig_breakdown,
                config=PLOTLY_CONFIG,
                width="stretch",
            )

    st.markdown(
        "**Scoring rationale:**"
    )

    st.write(
        selected_row[
            "score_rationale"
        ]
    )

    with st.expander(
        "View Active ICP & Scoring Model"
    ):

        st.write(
            "**Priority Regions:**",
            (
                ", ".join(
                    preferred_regions
                )
                if preferred_regions
                else "None selected"
            ),
        )

        st.write(
            "**Priority Industries:**",
            (
                ", ".join(
                    preferred_industries
                )
                if preferred_industries
                else "None selected"
            ),
        )

        weights_df = pd.DataFrame(
            {
                "Factor": [
                    "Region",
                    "Industry",
                    "Deal Value",
                    "Engagement",
                ],
                "Weight": [
                    f"{weights['region'] * 100:.1f}%",
                    f"{weights['industry'] * 100:.1f}%",
                    f"{weights['deal_value'] * 100:.1f}%",
                    f"{weights['engagement'] * 100:.1f}%",
                ],
            }
        )

        st.dataframe(
            weights_df,
            hide_index=True,
            width="stretch",
        )

        st.write(
            f"**Tier A:** {tier_a_threshold}+"
        )

        st.write(
            f"**Tier B:** {tier_b_threshold}–"
            f"{tier_a_threshold - 1}"
        )

        st.write(
            f"**Tier C:** below {tier_b_threshold}"
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
                    lead_for_ai
                )
            )

            saved_path = (
                save_ai_output(
                    selected_row[
                        "company_name"
                    ],
                    "ai_insight",
                    insight,
                )
            )

            render_structured_ai_result(
                insight,
                mode="insight",
            )

            st.success(
                f"AI Insight saved to {saved_path}"
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
                    lead_for_ai
                )
            )

            saved_path = (
                save_ai_output(
                    selected_row[
                        "company_name"
                    ],
                    "outreach_sequence",
                    outreach,
                )
            )

            render_structured_ai_result(
                outreach,
                mode="outreach",
            )

            st.success(
                f"Outreach Sequence saved to {saved_path}"
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
        width="stretch",
    )

    col_left, col_right = (
        st.columns(2)
    )

    with col_left:

        st.subheader(
            "🏭 Industry Distribution"
        )

        fig_industry = px.pie(
            df,
            names="industry",
            title="Leads by Industry",
        )

        st.plotly_chart(
            fig_industry,
            config=PLOTLY_CONFIG,
            width="stretch",
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

        fig_revenue = px.bar(
            revenue_by_tier,
            x="tier",
            y=(
                "estimated_deal_value_usd"
            ),
            title=(
                "Revenue Potential by Tier"
            ),
        )

        st.plotly_chart(
            fig_revenue,
            config=PLOTLY_CONFIG,
            width="stretch",
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

    fig_country = px.bar(
        country_df,
        x="country",
        y="count",
        title="Leads by Country",
    )

    st.plotly_chart(
        fig_country,
        config=PLOTLY_CONFIG,
        width="stretch",
    )

    st.divider()

    # ------------------------------------------------------------------
    # FULL PIPELINE
    # ------------------------------------------------------------------

    st.subheader(
        "📋 Full Ranked Pipeline"
    )

    display_df = df.drop(
        columns=[
            "_engagement_risk"
        ],
        errors="ignore",
    )

    st.dataframe(
        display_df,
        width="stretch",
    )

    csv = (
        display_df
        .to_csv(
            index=False
        )
        .encode(
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
        "Upload a compatible lead CSV to begin."
    )

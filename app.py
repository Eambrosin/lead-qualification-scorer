import html
import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from ai_insights import generate_ai_insight, generate_outreach
from lead_qualifier import load_scoring_config, rank_leads


st.set_page_config(
    page_title="AI Lead Qualification & Revenue Prioritization",
    page_icon="🚀",
    layout="wide",
)

PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}
EXPORTS_DIR = Path("exports")
EXPORTS_DIR.mkdir(exist_ok=True)

BASE_CONFIG = load_scoring_config()


def build_runtime_config(
    preferred_regions,
    preferred_industries,
    region_priority,
    industry_priority,
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
        "tier_thresholds": BASE_CONFIG["tier_thresholds"].copy(),
    }

    raw_priorities = {
        "region": float(region_priority),
        "industry": float(industry_priority),
        "deal_value": float(deal_value_priority),
        "engagement": float(engagement_priority),
    }

    total_priority = sum(raw_priorities.values())

    if total_priority <= 0:
        raise ValueError("At least one scoring priority must be greater than zero.")

    config["weights"] = {
        key: value / total_priority
        for key, value in raw_priorities.items()
    }

    # Preferred ICP regions/industries receive the maximum fit score.
    # Unselected options retain the baseline model values.
    for region in preferred_regions:
        config["region_scores"][region] = 100

    for industry in preferred_industries:
        config["industry_scores"][industry] = 100

    if tier_a_threshold <= tier_b_threshold:
        raise ValueError("Tier A threshold must be higher than Tier B threshold.")

    config["tier_thresholds"] = {
        "A": float(tier_a_threshold),
        "B": float(tier_b_threshold),
    }

    return config


def prepare_lead_for_ai(row):
    """Prepare the selected lead for the AI insight/outreach layer."""
    return {
        "company": row["company_name"],
        "country": row["country"],
        "region": row["region"],
        "industry": row["industry"],
        "deal_value": row["estimated_deal_value_usd"],
        "engagement_signal": row["engagement_signal"],
        "score": row["score"],
        "tier": row["tier"],
        "recommended_action": row.get("recommended_action", ""),
        "score_rationale": row.get("score_rationale", ""),
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


def save_ai_output(company_name, output_type, content):
    filename = f"{safe_filename(company_name)}_{output_type}.txt"
    path = EXPORTS_DIR / filename
    path.write_text(content, encoding="utf-8")
    return path


def render_ai_output(title, content, icon="📌"):
    # Escape generated content before using unsafe_allow_html.
    cleaned_content = html.escape(str(content).strip()).replace("\n", "<br>")

    st.markdown(f"### {icon} {title}")
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
                sections[current_title] = "\n".join(current_lines).strip()
            current_title = stripped.replace(":", "")
            current_lines = []
        else:
            current_lines.append(line)

    if current_title:
        sections[current_title] = "\n".join(current_lines).strip()

    return sections


def render_structured_ai_result(text, mode):
    sections = split_sections(text)

    if not sections:
        st.text_area("Generated output", text, height=420)
        return

    if "Account Brief" in sections:
        render_ai_output("Account Brief", sections["Account Brief"], "📋")

    if "Opportunity Assessment" in sections:
        render_ai_output("Opportunity Assessment", sections["Opportunity Assessment"], "🎯")

    if "Recommended GTM Angle" in sections:
        render_ai_output("Recommended GTM Angle", sections["Recommended GTM Angle"], "🧭")

    if "Opportunity Hypothesis" in sections:
        render_ai_output("Opportunity Hypothesis", sections["Opportunity Hypothesis"], "🎯")

    if "Email Subject" in sections:
        render_ai_output("Email Subject", sections["Email Subject"], "✉️")

    if "Email" in sections:
        render_ai_output("Email Outreach", sections["Email"], "📧")

    if "LinkedIn Message" in sections:
        render_ai_output("LinkedIn Message", sections["LinkedIn Message"], "💼")

    if "Call Opener" in sections:
        render_ai_output("Call Opener", sections["Call Opener"], "📞")

    if "Discovery Questions" in sections:
        render_ai_output("Discovery Questions", sections["Discovery Questions"], "❓")

    if "Recommended Next Step" in sections:
        render_ai_output("Recommended Next Step", sections["Recommended Next Step"], "🚀")

    if "Next Best Action" in sections:
        render_ai_output("Next Best Action", sections["Next Best Action"], "🚀")


def priority_reason(row, high_value_threshold):
    reasons = []

    if row["tier"] == "A":
        reasons.append("Tier A account")
    elif row["tier"] == "B":
        reasons.append("Tier B account")
    else:
        reasons.append("lower-priority account")

    engagement = str(row["engagement_signal"]).lower()

    if engagement == "hot":
        reasons.append("hot engagement signal")
    elif engagement == "warm":
        reasons.append("warm engagement signal")

    if row["estimated_deal_value_usd"] >= high_value_threshold:
        reasons.append("high estimated deal value")

    return ", ".join(reasons).capitalize() + "."


def get_highest_risk_account(df):
    """Return the coldest/highest-priority account without relying on alphabetic sorting."""
    risk_rank = {"hot": 1, "warm": 2, "cold": 3}

    risk_df = df.copy()
    risk_df["_risk_rank"] = (
        risk_df["engagement_signal"]
        .astype(str)
        .str.lower()
        .map(risk_rank)
        .fillna(2)
    )

    return risk_df.sort_values(
        ["_risk_rank", "score"],
        ascending=[False, False],
    ).iloc[0]


st.title("🚀 AI Lead Qualification & Revenue Prioritization")
st.caption(
    "Configure your Ideal Customer Profile, rank commercial opportunities, "
    "understand every score and generate AI-assisted account intelligence."
)


# ----------------------------------------------------------------------
# SIDEBAR — ICP, SCORING & AI SETTINGS
# ----------------------------------------------------------------------

with st.sidebar:
    st.header("🎯 ICP & Scoring")
    st.caption(
        "Configure the commercial model before uploading or reviewing your pipeline."
    )

    region_options = list(BASE_CONFIG["region_scores"].keys())
    industry_options = list(BASE_CONFIG["industry_scores"].keys())

    preferred_regions = st.multiselect(
        "Priority regions",
        options=region_options,
        default=["LATAM", "MENA"],
        help="Selected regions receive the maximum Region Fit score.",
    )

    preferred_industries = st.multiselect(
        "Priority industries",
        options=industry_options,
        default=[
            "Agribusiness",
            "Renewable Energy",
            "Government / Public Sector",
        ],
        help="Selected industries receive the maximum Industry Fit score.",
    )

    with st.expander("Scoring priorities", expanded=True):
        st.caption(
            "The values below express relative importance. "
            "They are automatically normalized to 100%."
        )

        region_priority = st.slider(
            "Region fit",
            min_value=0,
            max_value=100,
            value=25,
            step=5,
        )

        industry_priority = st.slider(
            "Industry fit",
            min_value=0,
            max_value=100,
            value=20,
            step=5,
        )

        deal_value_priority = st.slider(
            "Deal value",
            min_value=0,
            max_value=100,
            value=30,
            step=5,
        )

        engagement_priority = st.slider(
            "Engagement",
            min_value=0,
            max_value=100,
            value=25,
            step=5,
        )

    with st.expander("Tier thresholds"):
        tier_a_threshold = st.slider(
            "Tier A minimum score",
            min_value=55,
            max_value=95,
            value=75,
            step=1,
        )

        tier_b_threshold = st.slider(
            "Tier B minimum score",
            min_value=25,
            max_value=80,
            value=50,
            step=1,
        )

    try:
        runtime_config = build_runtime_config(
            preferred_regions=preferred_regions,
            preferred_industries=preferred_industries,
            region_priority=region_priority,
            industry_priority=industry_priority,
            deal_value_priority=deal_value_priority,
            engagement_priority=engagement_priority,
            tier_a_threshold=tier_a_threshold,
            tier_b_threshold=tier_b_threshold,
        )
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    effective_weights = runtime_config["weights"]

    st.markdown("#### Effective weights")
    st.caption(
        " · ".join(
            [
                f"Region {effective_weights['region']:.0%}",
                f"Industry {effective_weights['industry']:.0%}",
                f"Deal {effective_weights['deal_value']:.0%}",
                f"Engagement {effective_weights['engagement']:.0%}",
            ]
        )
    )

    st.divider()

    st.header("🤖 AI Settings")

    api_key_input = st.text_input(
        "OpenAI API Key",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
    )

    if api_key_input:
        os.environ["OPENAI_API_KEY"] = api_key_input

    st.text_input(
        "Model",
        value="gpt-4o-mini",
        disabled=True,
    )

    st.caption(
        "Without an API key, the scoring and prioritization engine remains fully operational."
    )


uploaded = st.file_uploader(
    "Upload Pipeline CSV",
    type=["csv"],
    help=(
        "Required fields: company_name, country, region, industry, "
        "estimated_deal_value_usd, engagement_signal."
    ),
)


if uploaded is not None:
    try:
        source_df = pd.read_csv(uploaded)
        source_df["estimated_deal_value_usd"] = pd.to_numeric(
            source_df["estimated_deal_value_usd"],
            errors="coerce",
        )
        df = rank_leads(source_df, config=runtime_config)
    except Exception as exc:
        st.error(f"Unable to process this pipeline: {exc}")
        st.stop()

    st.subheader("📊 Executive Summary")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Leads", len(df))
    col2.metric("Pipeline Value", f"${df['estimated_deal_value_usd'].sum():,.0f}")
    col3.metric("Average Score", round(df["score"].mean(), 1))
    col4.metric("Tier A Leads", len(df[df["tier"] == "A"]))

    with st.expander("⚙️ Active ICP & Scoring Model"):
        model_col_1, model_col_2 = st.columns(2)

        with model_col_1:
            st.markdown("**Priority Regions**")
            st.write(", ".join(preferred_regions) if preferred_regions else "Baseline model")

            st.markdown("**Priority Industries**")
            st.write(", ".join(preferred_industries) if preferred_industries else "Baseline model")

        with model_col_2:
            weights_df = pd.DataFrame(
                {
                    "Component": [
                        "Region Fit",
                        "Industry Fit",
                        "Deal Value",
                        "Engagement",
                    ],
                    "Effective Weight": [
                        effective_weights["region"],
                        effective_weights["industry"],
                        effective_weights["deal_value"],
                        effective_weights["engagement"],
                    ],
                }
            )
            weights_df["Effective Weight"] = weights_df["Effective Weight"].map(
                lambda value: f"{value:.0%}"
            )
            st.dataframe(weights_df, hide_index=True, width="stretch")

            st.caption(
                f"Tier A ≥ {runtime_config['tier_thresholds']['A']:.0f} · "
                f"Tier B ≥ {runtime_config['tier_thresholds']['B']:.0f}"
            )

    st.divider()

    st.subheader("👔 Executive Account Dashboard")
    st.caption("Executive view of the pipeline: where to focus commercial effort first.")

    top_revenue = df.sort_values("estimated_deal_value_usd", ascending=False).iloc[0]
    top_partnership = df.sort_values(["score", "estimated_deal_value_usd"], ascending=[False, False]).iloc[0]

    expansion_regions = preferred_regions or ["LATAM", "MENA", "AFRICA"]
    top_expansion = df[df["region"].isin(expansion_regions)].sort_values("score", ascending=False)

    if len(top_expansion) > 0:
        top_expansion_account = top_expansion.iloc[0]
    else:
        top_expansion_account = df.sort_values("score", ascending=False).iloc[0]

    highest_risk = get_highest_risk_account(df)

    fastest_path = df[
        (df["tier"] == "A")
        & (df["engagement_signal"].astype(str).str.lower() == "hot")
    ]

    if len(fastest_path) > 0:
        fastest_path_account = fastest_path.sort_values("score", ascending=False).iloc[0]
    else:
        fastest_path_account = df.sort_values("score", ascending=False).iloc[0]

    exec_col_1, exec_col_2, exec_col_3 = st.columns(3)

    with exec_col_1:
        st.metric(
            "Top Revenue Opportunity",
            top_revenue["company_name"],
            f"${top_revenue['estimated_deal_value_usd']:,.0f}",
        )

        st.metric(
            "Fastest Path To Revenue",
            fastest_path_account["company_name"],
            f"Score {fastest_path_account['score']}",
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
            highest_risk["company_name"],
            str(highest_risk["engagement_signal"]).title(),
        )

        tier_a_pipeline = df[df["tier"] == "A"]["estimated_deal_value_usd"].sum()
        st.metric(
            "Tier A Pipeline",
            f"${tier_a_pipeline:,.0f}",
            f"{len(df[df['tier'] == 'A'])} accounts",
        )

    st.markdown("#### Executive Interpretation")

    st.write(
        f"Focus initial commercial effort on **{fastest_path_account['company_name']}** because it combines "
        f"a strong score, Tier {fastest_path_account['tier']} classification and a "
        f"{fastest_path_account['engagement_signal']} engagement signal."
    )

    st.write(
        f"From a revenue perspective, **{top_revenue['company_name']}** represents the largest estimated deal value "
        f"at **${top_revenue['estimated_deal_value_usd']:,.0f}**."
    )

    st.write(
        f"For market expansion, **{top_expansion_account['company_name']}** is the strongest current account "
        f"within the configured expansion priorities."
    )

    st.divider()

    st.subheader("🎯 Multi-Lead Prioritization Engine")
    st.caption(
        "Automatically prioritizes accounts using the configured ICP, score, tier, deal value and engagement signal."
    )

    priority_df = df.head(10).copy()
    high_value_threshold = df["estimated_deal_value_usd"].quantile(0.75)

    priority_df["commercial_priority"] = priority_df["tier"].map(
        {"A": "High", "B": "Medium", "C": "Low"}
    )

    priority_df["why_this_account_matters"] = priority_df.apply(
        lambda row: priority_reason(row, high_value_threshold),
        axis=1,
    )

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
                "why_this_account_matters",
                "recommended_action",
            ]
        ],
        width="stretch",
    )

    priority_csv = priority_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇ Download Prioritized Accounts CSV",
        priority_csv,
        "prioritized_accounts.csv",
        "text/csv",
    )

    st.divider()

    st.subheader("🏆 Top 5 Leads")
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

    st.subheader("🤖 Lead Intelligence & Outreach")
    st.caption(
        "Inspect the deterministic score first, then generate AI-assisted account intelligence and outreach assets."
    )

    selected_company = st.selectbox(
        "Select a lead",
        df["company_name"].tolist(),
    )

    selected_row = df[df["company_name"] == selected_company].iloc[0]
    lead_for_ai = prepare_lead_for_ai(selected_row)

    col_profile_1, col_profile_2, col_profile_3, col_profile_4 = st.columns(4)
    col_profile_1.metric("Selected Lead", selected_row["company_name"])
    col_profile_2.metric("Tier", selected_row["tier"])
    col_profile_3.metric("Score", selected_row["score"])
    col_profile_4.metric(
        "Deal Value",
        f"${selected_row['estimated_deal_value_usd']:,.0f}",
    )

    st.markdown("### 🧩 Lead Intelligence Workspace")
    st.caption(
        "Commercial view of the selected account before generating AI recommendations."
    )

    workspace_col_1, workspace_col_2, workspace_col_3 = st.columns(3)

    with workspace_col_1:
        st.markdown("#### 🏢 Company Profile")
        st.write(f"**Company:** {selected_row['company_name']}")
        st.write(f"**Country:** {selected_row['country']}")
        st.write(f"**Region:** {selected_row['region']}")
        st.write(f"**Industry:** {selected_row['industry']}")

    with workspace_col_2:
        st.markdown("#### 💰 Revenue Potential")
        st.write(
            f"**Estimated Deal Value:** ${selected_row['estimated_deal_value_usd']:,.0f}"
        )
        st.write(f"**Lead Score:** {selected_row['score']}")
        st.write(f"**Tier:** {selected_row['tier']}")
        st.write(f"**Engagement:** {selected_row['engagement_signal']}")

    with workspace_col_3:
        st.markdown("#### 🚀 Recommended Action")

        if selected_row["tier"] == "A":
            st.success(selected_row["recommended_action"])
        elif selected_row["tier"] == "B":
            st.info(selected_row["recommended_action"])
        else:
            st.warning(selected_row["recommended_action"])

    st.markdown("#### 🔎 Explainable Score")
    st.caption(
        "Every score is generated by the deterministic commercial model. AI does not set or modify the score."
    )

    try:
        score_breakdown = json.loads(selected_row["score_breakdown"])
        contribution_map = score_breakdown["weighted_contributions"]
        raw_score_map = score_breakdown["raw_scores"]

        breakdown_df = pd.DataFrame(
            {
                "Component": [
                    "Region Fit",
                    "Industry Fit",
                    "Deal Value",
                    "Engagement",
                ],
                "Raw Score": [
                    raw_score_map["region"],
                    raw_score_map["industry"],
                    raw_score_map["deal_value"],
                    raw_score_map["engagement"],
                ],
                "Weight": [
                    effective_weights["region"],
                    effective_weights["industry"],
                    effective_weights["deal_value"],
                    effective_weights["engagement"],
                ],
                "Weighted Contribution": [
                    contribution_map["region"],
                    contribution_map["industry"],
                    contribution_map["deal_value"],
                    contribution_map["engagement"],
                ],
            }
        )

        breakdown_display = breakdown_df.copy()
        breakdown_display["Weight"] = breakdown_display["Weight"].map(
            lambda value: f"{value:.0%}"
        )

        breakdown_col_1, breakdown_col_2 = st.columns([1, 1.2])

        with breakdown_col_1:
            st.dataframe(
                breakdown_display,
                hide_index=True,
                width="stretch",
            )

        with breakdown_col_2:
            fig_breakdown = px.bar(
                breakdown_df,
                x="Component",
                y="Weighted Contribution",
                title="Contribution to Final Score",
            )
            st.plotly_chart(
                fig_breakdown,
                config=PLOTLY_CONFIG,
            )

        st.caption(selected_row["score_rationale"])

    except Exception:
        st.info("Score breakdown is not available for this account.")

    st.markdown("#### 🧠 Commercial Interpretation")

    interpretation_col_1, interpretation_col_2, interpretation_col_3 = st.columns(3)

    with interpretation_col_1:
        st.markdown("**Why This Lead Matters**")
        st.write(
            f"{selected_row['company_name']} operates in {selected_row['industry']} "
            f"and currently ranks as a Tier {selected_row['tier']} opportunity with a "
            f"score of {selected_row['score']}."
        )

    with interpretation_col_2:
        st.markdown("**Commercial Motion**")
        st.write(selected_row["recommended_action"])

    with interpretation_col_3:
        st.markdown("**Engagement Risk**")
        engagement = str(selected_row["engagement_signal"]).lower()

        if engagement == "hot":
            st.write("Low engagement risk. The account shows a strong buying or partnership signal.")
        elif engagement == "warm":
            st.write("Moderate engagement risk. The account may require additional nurturing.")
        else:
            st.write("Higher engagement risk. The account may require education and longer-cycle development.")

    st.divider()

    tab_1, tab_2 = st.tabs(["🧠 Account Intelligence", "📨 Outreach Sequence"])

    with tab_1:
        if st.button("Generate AI Insight"):
            insight = generate_ai_insight(lead_for_ai)
            saved_path = save_ai_output(
                selected_row["company_name"],
                "ai_insight",
                insight,
            )
            render_structured_ai_result(insight, mode="insight")
            st.success(f"AI Insight saved to {saved_path}")
            st.download_button(
                "⬇ Download AI Insight",
                insight,
                file_name=(
                    f"{safe_filename(selected_row['company_name'])}_ai_insight.txt"
                ),
                mime="text/plain",
            )

    with tab_2:
        if st.button("Generate Outreach Sequence"):
            outreach = generate_outreach(lead_for_ai)
            saved_path = save_ai_output(
                selected_row["company_name"],
                "outreach_sequence",
                outreach,
            )
            render_structured_ai_result(outreach, mode="outreach")
            st.success(f"Outreach Sequence saved to {saved_path}")
            st.download_button(
                "⬇ Download Outreach Sequence",
                outreach,
                file_name=(
                    f"{safe_filename(selected_row['company_name'])}_outreach_sequence.txt"
                ),
                mime="text/plain",
            )

    st.divider()

    st.subheader("⭐ Lead Scores")
    fig_scores = px.bar(
        df,
        x="company_name",
        y="score",
        color="tier",
        title="Lead Ranking by Score",
    )
    st.plotly_chart(fig_scores, config=PLOTLY_CONFIG)

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("🏭 Industry Distribution")
        fig_industry = px.pie(
            df,
            names="industry",
            title="Leads by Industry",
        )
        st.plotly_chart(fig_industry, config=PLOTLY_CONFIG)

    with col_right:
        st.subheader("💰 Revenue by Tier")
        revenue_by_tier = (
            df.groupby("tier")["estimated_deal_value_usd"]
            .sum()
            .reset_index()
        )
        fig_revenue = px.bar(
            revenue_by_tier,
            x="tier",
            y="estimated_deal_value_usd",
            title="Revenue Potential by Tier",
        )
        st.plotly_chart(fig_revenue, config=PLOTLY_CONFIG)

    st.divider()

    st.subheader("🌍 Leads by Country")
    country_df = df["country"].value_counts().reset_index()
    country_df.columns = ["country", "count"]
    fig_country = px.bar(
        country_df,
        x="country",
        y="count",
        title="Leads by Country",
    )
    st.plotly_chart(fig_country, config=PLOTLY_CONFIG)

    st.divider()

    st.subheader("📋 Full Ranked Pipeline")
    st.dataframe(df, width="stretch")

    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇ Download Ranked Leads CSV",
        csv,
        "ranked_leads.csv",
        "text/csv",
    )

else:
    st.info(
        "Upload data/sample_leads.csv or exports/ranked_leads.csv to begin."
    )

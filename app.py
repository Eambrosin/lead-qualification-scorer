import os
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

from ai_insights import generate_ai_insight, generate_outreach


st.set_page_config(
    page_title="AI Lead Qualification Dashboard",
    page_icon="🚀",
    layout="wide"
)

PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}
EXPORTS_DIR = Path("exports")
EXPORTS_DIR.mkdir(exist_ok=True)

REGION_SCORES = {"LATAM": 100, "MENA": 90, "AFRICA": 70, "EU": 60, "NA": 50, "APAC": 40}

INDUSTRY_SCORES = {
    "Agribusiness": 100,
    "Renewable Energy": 100,
    "Government / Public Sector": 90,
    "Fintech": 85,
    "Real Estate": 80,
    "Logistics & Trade": 70,
    "Other": 30,
}

ENGAGEMENT_SCORES = {"hot": 100, "warm": 60, "cold": 20}


def score_deal_value(value, max_value):
    if max_value == 0:
        return 0
    return round((value / max_value) * 100, 1)


def score_lead(row, max_deal_value):
    region_score = REGION_SCORES.get(row["region"], 30)
    industry_score = INDUSTRY_SCORES.get(row["industry"], 30)
    deal_score = score_deal_value(row["estimated_deal_value_usd"], max_deal_value)
    engagement_score = ENGAGEMENT_SCORES.get(str(row["engagement_signal"]).lower(), 20)

    total = (
        region_score * 0.25
        + industry_score * 0.20
        + deal_score * 0.30
        + engagement_score * 0.25
    )

    return round(total, 1)


def tier_for_score(score):
    if score >= 75:
        return "A"
    if score >= 50:
        return "B"
    return "C"


def prepare_lead_for_ai(row):
    return {
        "company": row["company_name"],
        "country": row["country"],
        "region": row["region"],
        "industry": row["industry"],
        "deal_value": row["estimated_deal_value_usd"],
        "engagement_signal": row["engagement_signal"],
        "score": row["score"],
        "tier": row["tier"],
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
    cleaned_content = str(content).strip()

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


st.title("🚀 AI Lead Qualification Dashboard")
st.caption("Upload um CSV para calcular score, priorizar leads e gerar insights comerciais com IA.")

with st.sidebar:
    st.header("⚙️ AI Settings")
    api_key_input = st.text_input(
        "OpenAI API Key",
        type="password",
        value=os.getenv("OPENAI_API_KEY", "")
    )

    if api_key_input:
        os.environ["OPENAI_API_KEY"] = api_key_input

    st.text_input("Model", value="gpt-4o-mini", disabled=True)
    st.caption("Sem chave de API, o app usa insights locais automáticos.")

uploaded = st.file_uploader("Upload Pipeline CSV", type=["csv"])

if uploaded is not None:
    df = pd.read_csv(uploaded)

    required_columns = [
        "company_name",
        "country",
        "region",
        "industry",
        "estimated_deal_value_usd",
        "engagement_signal",
    ]

    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        st.error("Colunas ausentes no CSV: " + ", ".join(missing_columns))
        st.stop()

    max_deal_value = df["estimated_deal_value_usd"].max()
    df["score"] = df.apply(lambda row: score_lead(row, max_deal_value), axis=1)
    df["tier"] = df["score"].apply(tier_for_score)
    df = df.sort_values("score", ascending=False).reset_index(drop=True)

    st.subheader("📊 Executive Summary")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Leads", len(df))
    col2.metric("Pipeline Value", f"${df['estimated_deal_value_usd'].sum():,.0f}")
    col3.metric("Average Score", round(df["score"].mean(), 1))
    col4.metric("Tier A Leads", len(df[df["tier"] == "A"]))

    st.divider()

    st.subheader("👔 Executive Account Dashboard")
    st.caption("Executive view of the pipeline: where to focus commercial effort first.")

    top_revenue = df.sort_values("estimated_deal_value_usd", ascending=False).iloc[0]
    top_partnership = df.sort_values(["tier", "score"], ascending=[True, False]).iloc[0]
    top_expansion = df[df["region"].isin(["LATAM", "MENA", "AFRICA"])].sort_values("score", ascending=False)

    if len(top_expansion) > 0:
        top_expansion_account = top_expansion.iloc[0]
    else:
        top_expansion_account = df.sort_values("score", ascending=False).iloc[0]

    highest_risk = df.sort_values(["engagement_signal", "score"], ascending=[True, False]).iloc[0]

    fastest_path = df[
        (df["tier"] == "A") & (df["engagement_signal"].astype(str).str.lower() == "hot")
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
            f"${top_revenue['estimated_deal_value_usd']:,.0f}"
        )

        st.metric(
            "Fastest Path To Revenue",
            fastest_path_account["company_name"],
            f"Score {fastest_path_account['score']}"
        )

    with exec_col_2:
        st.metric(
            "Top Partnership Opportunity",
            top_partnership["company_name"],
            f"Tier {top_partnership['tier']}"
        )

        st.metric(
            "Top Expansion Opportunity",
            top_expansion_account["company_name"],
            top_expansion_account["region"]
        )

    with exec_col_3:
        st.metric(
            "Highest Risk Account",
            highest_risk["company_name"],
            str(highest_risk["engagement_signal"]).title()
        )

        tier_a_pipeline = df[df["tier"] == "A"]["estimated_deal_value_usd"].sum()
        st.metric(
            "Tier A Pipeline",
            f"${tier_a_pipeline:,.0f}",
            f"{len(df[df['tier'] == 'A'])} accounts"
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
        f"For market expansion, **{top_expansion_account['company_name']}** is the strongest account based on "
        f"regional relevance and qualification score."
    )

    st.divider()

    st.subheader("🎯 Multi-Lead Prioritization Engine")
    st.caption("Automatically identifies the best accounts to prioritize based on score, tier, deal value and engagement signal.")

    priority_df = df.head(10).copy()

    def recommended_action(row):
        if row["tier"] == "A" and str(row["engagement_signal"]).lower() == "hot":
            return "Executive outreach within 48 hours"
        if row["tier"] == "A":
            return "Personalized discovery outreach"
        if row["tier"] == "B":
            return "Structured nurture and qualification"
        return "Monitor and keep in low-touch sequence"

    def priority_reason(row):
        reasons = []

        if row["tier"] == "A":
            reasons.append("Tier A account")
        elif row["tier"] == "B":
            reasons.append("Tier B account")
        else:
            reasons.append("Lower-priority account")

        if str(row["engagement_signal"]).lower() == "hot":
            reasons.append("hot engagement signal")
        elif str(row["engagement_signal"]).lower() == "warm":
            reasons.append("warm engagement signal")

        if row["estimated_deal_value_usd"] >= df["estimated_deal_value_usd"].quantile(0.75):
            reasons.append("high estimated deal value")

        return ", ".join(reasons).capitalize() + "."

    priority_df["commercial_priority"] = priority_df["tier"].map(
        {"A": "High", "B": "Medium", "C": "Low"}
    )

    priority_df["why_this_account_matters"] = priority_df.apply(priority_reason, axis=1)
    priority_df["recommended_action"] = priority_df.apply(recommended_action, axis=1)

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
            ]
        ].head(5),
        width="stretch",
    )

    st.divider()

    st.subheader("🤖 AI Lead Insights & Outreach")
    st.caption("Generate account intelligence, GTM angle, discovery questions and outreach assets for each prioritized lead.")

    selected_company = st.selectbox("Select a lead", df["company_name"].tolist())
    selected_row = df[df["company_name"] == selected_company].iloc[0]
    lead_for_ai = prepare_lead_for_ai(selected_row)

    col_profile_1, col_profile_2, col_profile_3, col_profile_4 = st.columns(4)
    col_profile_1.metric("Selected Lead", selected_row["company_name"])
    col_profile_2.metric("Tier", selected_row["tier"])
    col_profile_3.metric("Score", selected_row["score"])
    col_profile_4.metric("Deal Value", f"${selected_row['estimated_deal_value_usd']:,.0f}")

    st.markdown("### 🧩 Lead Intelligence Workspace")
    st.caption("Commercial view of the selected account before generating AI recommendations.")

    workspace_col_1, workspace_col_2, workspace_col_3 = st.columns(3)

    with workspace_col_1:
        st.markdown("#### 🏢 Company Profile")
        st.write(f"**Company:** {selected_row['company_name']}")
        st.write(f"**Country:** {selected_row['country']}")
        st.write(f"**Region:** {selected_row['region']}")
        st.write(f"**Industry:** {selected_row['industry']}")

    with workspace_col_2:
        st.markdown("#### 💰 Revenue Potential")
        st.write(f"**Estimated Deal Value:** ${selected_row['estimated_deal_value_usd']:,.0f}")
        st.write(f"**Lead Score:** {selected_row['score']}")
        st.write(f"**Tier:** {selected_row['tier']}")
        st.write(f"**Engagement:** {selected_row['engagement_signal']}")

    with workspace_col_3:
        st.markdown("#### 🚀 Recommended Motion")

        if selected_row["tier"] == "A":
            st.success("High-priority account. Recommend direct outreach and discovery within 48 hours.")
        elif selected_row["tier"] == "B":
            st.info("Medium-priority account. Recommend structured nurture and qualification.")
        else:
            st.warning("Lower-priority account. Recommend monitoring and light-touch engagement.")

    st.markdown("#### 🧠 Commercial Interpretation")

    interpretation_col_1, interpretation_col_2, interpretation_col_3 = st.columns(3)

    with interpretation_col_1:
        st.markdown("**Why This Lead Matters**")
        st.write(
            f"{selected_row['company_name']} operates in {selected_row['industry']} "
            f"and has a {selected_row['engagement_signal']} engagement signal, making it relevant "
            f"for commercial prioritization."
        )

    with interpretation_col_2:
        st.markdown("**Partnership Potential**")
        st.write(
            f"The account may be evaluated for market expansion, distribution channels, "
            f"strategic alliances or pipeline development opportunities in {selected_row['region']}."
        )

    with interpretation_col_3:
        st.markdown("**Risk Assessment**")
        if selected_row["engagement_signal"].lower() == "hot":
            st.write("Low engagement risk. The account shows strong buying or partnership signal.")
        elif selected_row["engagement_signal"].lower() == "warm":
            st.write("Moderate engagement risk. The account may require additional nurturing.")
        else:
            st.write("Higher engagement risk. The account may need education and longer-cycle development.")

    st.divider()

    tab_1, tab_2 = st.tabs(["🧠 Account Intelligence", "📨 Outreach Sequence"])

    with tab_1:
        if st.button("Generate AI Insight"):
            insight = generate_ai_insight(lead_for_ai)
            saved_path = save_ai_output(selected_row["company_name"], "ai_insight", insight)
            render_structured_ai_result(insight, mode="insight")
            st.success(f"AI Insight saved to {saved_path}")
            st.download_button(
                "⬇ Download AI Insight",
                insight,
                file_name=f"{safe_filename(selected_row['company_name'])}_ai_insight.txt",
                mime="text/plain",
            )

    with tab_2:
        if st.button("Generate Outreach Sequence"):
            outreach = generate_outreach(lead_for_ai)
            saved_path = save_ai_output(selected_row["company_name"], "outreach_sequence", outreach)
            render_structured_ai_result(outreach, mode="outreach")
            st.success(f"Outreach Sequence saved to {saved_path}")
            st.download_button(
                "⬇ Download Outreach Sequence",
                outreach,
                file_name=f"{safe_filename(selected_row['company_name'])}_outreach_sequence.txt",
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
        fig_industry = px.pie(df, names="industry", title="Leads by Industry")
        st.plotly_chart(fig_industry, config=PLOTLY_CONFIG)

    with col_right:
        st.subheader("💰 Revenue by Tier")
        revenue_by_tier = df.groupby("tier")["estimated_deal_value_usd"].sum().reset_index()
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
    fig_country = px.bar(country_df, x="country", y="count", title="Leads by Country")
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
    st.info("Upload data/sample_leads.csv ou exports/ranked_leads.csv para começar.")

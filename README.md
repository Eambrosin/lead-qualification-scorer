# AI Lead Qualification & Revenue Prioritization Platform

### Configurable ICP Scoring | Explainable Commercial Intelligence | Revenue Prioritization | AI-Assisted Account Strategy

A practical Commercial Intelligence application designed to help Business Development, Sales, Partnerships and GTM teams determine **which opportunities deserve attention, why they matter and what commercial action should happen next**.

The platform combines a transparent deterministic scoring engine with an optional AI intelligence layer.

**AI does not determine the lead score.**

Commercial scores, tiers and prioritization are calculated using configurable business rules. AI is used afterward to interpret those results, support account strategy and generate outreach.

---

## 🚀 Live Application

[Launch the Streamlit App](https://lead-qualification-scorer-eambrosin.streamlit.app/)

---

## Business Problem

Commercial teams frequently manage more accounts and opportunities than they can effectively pursue.

Raw lead lists rarely answer the questions that matter most:

- Which accounts deserve immediate attention?
- Which opportunities best match our Ideal Customer Profile?
- Where should commercial resources be allocated?
- Why did one account rank higher than another?
- What should the next Business Development action be?

This platform converts pipeline data into a structured and explainable commercial prioritization workflow.

---

## Solution

Users define their Ideal Customer Profile, configure commercial priorities and upload a CSV pipeline.

The system then:

1. Evaluates every account against the active ICP.
2. Calculates a transparent commercial score.
3. Assigns each opportunity to a priority tier.
4. Explains exactly how the score was calculated.
5. Recommends the next commercial action.
6. Ranks the complete opportunity pipeline.
7. Optionally generates AI-assisted account intelligence and outreach.

---

## Commercial Intelligence Workflow

### ICP → Score → Explain → Prioritize → Act

The platform follows a simple decision-support process:

### 1. Configure the ICP

Define what a commercially attractive account looks like.

### 2. Score Opportunities

Evaluate leads using deterministic commercial criteria.

### 3. Explain the Score

Show the contribution of every scoring factor.

### 4. Prioritize the Pipeline

Rank accounts according to commercial relevance.

### 5. Recommend Action

Translate qualification results into practical next steps.

### 6. Add AI Intelligence

Use AI to interpret the deterministic result and support account strategy and outreach.

---

## 🎯 Configurable Ideal Customer Profile

The v2.0 scoring model allows users to configure:

### Priority Regions

Examples:

- LATAM
- MENA
- EU
- North America
- APAC
- Africa

### Priority Industries

Examples:

- Agribusiness
- Renewable Energy
- Government / Public Sector
- Fintech
- Real Estate
- Logistics & Trade

### Preferred Company Size

Users can define a preferred employee range.

Example:

```text
Minimum employees: 50
Maximum employees: 1,000
```

Companies inside the target range receive the strongest Company Size Fit score.

Companies outside the range are progressively penalized rather than automatically rejected.

This avoids the assumption that a larger company is always a better commercial opportunity.

---

## ⚖️ Configurable Scoring Model

The default v2.0 scoring model evaluates five commercial dimensions:

| Component | Default Weight |
|---|---:|
| Region Fit | 20% |
| Industry Fit | 20% |
| Company Size Fit | 15% |
| Deal Value | 25% |
| Engagement | 20% |

Users can change the relative importance of each factor directly from the Streamlit interface.

Weights are automatically normalized to 100%.

---

## 🔎 Explainable Scoring

Every final score can be audited.

Example:

```text
Region Fit          100/100 × 20% = 20.0
Industry Fit        100/100 × 20% = 20.0
Company Size Fit     85/100 × 15% = 12.8
Deal Value           72/100 × 25% = 18.0
Engagement          100/100 × 20% = 20.0

Final Score                         90.8
```

The system stores both:

- Raw component scores
- Weighted contributions

This makes the qualification logic transparent rather than relying on a black-box AI score.

---

## Priority Tiers

The default classification model is:

```text
Tier A = 75+
Tier B = 50–74
Tier C = below 50
```

Tier thresholds can also be configured directly from the application.

### Tier A

High-priority commercial opportunities.

### Tier B

Opportunities requiring additional qualification or nurturing.

### Tier C

Lower-priority accounts where commercial resources should be allocated selectively.

---

## 🚀 Recommended Commercial Actions

The scoring engine converts qualification results into practical Business Development recommendations.

Examples include:

- Immediate personalized outreach
- High-priority outreach with account research
- Priority follow-up and qualification
- Nurture and continue qualification
- Validate strategic fit before allocating resources
- Low-priority nurture

The objective is to move beyond scoring and answer:

> **What should the commercial team do next?**

---

## 👔 Executive Account Dashboard

The application provides an executive view of the pipeline, including:

- Total Leads
- Total Pipeline Value
- Average Commercial Score
- Tier A Opportunities
- Tier A Pipeline Value
- Top Revenue Opportunity
- Fastest Path to Revenue
- Top Strategic Opportunity
- Top Expansion Opportunity
- Highest Engagement Risk

This allows the application to operate as a lightweight Commercial Intelligence layer rather than simply a lead-scoring calculator.

---

## 🎯 Multi-Lead Prioritization Engine

The full pipeline is automatically ranked according to the active ICP.

For each account, the platform can display:

- Company
- Country
- Industry
- Company Size
- Estimated Deal Value
- Engagement Signal
- Commercial Score
- Tier
- Commercial Priority
- Recommended Action

Prioritized pipelines can be exported as CSV files.

---

## 🧩 Lead Intelligence Workspace

Users can select individual accounts and inspect:

### Company Profile

- Company
- Country
- Region
- Industry
- Company Size

### Revenue Potential

- Estimated Deal Value
- Commercial Score
- Priority Tier
- Engagement Signal

### Recommended Action

The deterministic engine provides the appropriate commercial motion based on the qualification result.

### Explainable Score

A component-by-component breakdown shows exactly how the final score was constructed.

---

## 🤖 AI-Assisted Commercial Intelligence

The AI layer receives the deterministic scoring output as context.

This includes:

- Commercial Score
- Priority Tier
- Score Rationale
- Score Breakdown
- Recommended Action
- Priority Regions
- Priority Industries
- Company Size ICP
- Scoring Weights
- Tier Thresholds

The AI is explicitly instructed **not to replace or modify the deterministic score**.

Instead, it provides qualitative commercial interpretation.

### AI Account Intelligence

The system can generate:

- Account Brief
- Opportunity Assessment
- Score Interpretation
- Recommended GTM Angle
- Discovery Questions
- Next Best Action

### AI Outreach

The platform can also generate:

- Opportunity Hypothesis
- Email Subject
- Consultative Email
- LinkedIn Message
- Call Opener
- Discovery Questions
- Recommended Next Step

Internal scoring information is not exposed to prospects.

---

## 🛡️ Evidence-Aware AI Design

The AI layer is instructed not to fabricate:

- Company initiatives
- Financial information
- Decision makers
- Market research
- Expansion plans
- Business problems

Unverified commercial ideas are treated as **hypotheses to validate**, not as facts.

This keeps the AI layer aligned with practical Business Development workflows.

---

## 🔄 AI-Optional Architecture

The deterministic qualification engine works without an API key.

Without AI access, the platform still provides:

- ICP Configuration
- Lead Scoring
- Company Size Fit
- Tier Classification
- Explainable Scoring
- Revenue Prioritization
- Recommended Actions
- Executive Dashboard
- Pipeline Ranking
- CSV Export

A local fallback layer also provides basic commercial interpretation and outreach templates.

AI therefore enhances the platform but does not control the core qualification workflow.

---

## 📊 Sample Dataset

The repository includes a demonstration pipeline in:

```text
data/sample_leads.csv
```

The sample contains accounts across:

- LATAM
- Europe
- MENA
- APAC

and multiple sectors including:

- Renewable Energy
- Agribusiness
- Fintech
- Government / Public Sector
- Logistics & Trade
- Real Estate

The dataset intentionally includes different company sizes, deal values and engagement signals so users can test how changes to the ICP affect prioritization.

---

## CSV Format

Recommended columns:

```text
company_name
country
region
industry
company_size
estimated_deal_value_usd
engagement_signal
```

Example:

```csv
company_name,country,region,industry,company_size,estimated_deal_value_usd,engagement_signal
Andina AgroExport,Colombia,LATAM,Agribusiness,180,250000,hot
Solis Renewables,Brazil,LATAM,Renewable Energy,90,180000,warm
Gulf Trade Partners,UAE,MENA,Logistics & Trade,300,500000,hot
```

`company_size` is recommended for the complete v2.0 ICP model.

The application remains capable of processing pipelines where company-size information is unavailable.

---

## Architecture

```text
Pipeline CSV
    ↓
ICP Configuration
    ↓
Deterministic Scoring Engine
    ↓
Commercial Score
    ↓
Priority Tier
    ↓
Explainable Score Breakdown
    ↓
Recommended Commercial Action
    ↓
Optional AI Interpretation
    ↓
Account Intelligence / Outreach
```

The deterministic engine remains the source of truth for commercial qualification.

---

## Project Structure

```text
lead-qualification-scorer/
│
├── app.py
├── lead_qualifier.py
├── ai_insights.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── data/
│   └── sample_leads.csv
│
├── exports/
│
└── screenshots/
```

### `lead_qualifier.py`

Deterministic Commercial Intelligence engine responsible for:

- ICP scoring
- Company Size Fit
- Weighting
- Tier classification
- Score explainability
- Recommended commercial actions

### `app.py`

Streamlit interface responsible for:

- ICP configuration
- Pipeline upload
- Executive dashboards
- Lead prioritization
- Explainable scoring
- AI workflow
- CSV export

### `ai_insights.py`

Optional qualitative intelligence layer responsible for:

- Account interpretation
- GTM recommendations
- Discovery questions
- Outreach generation

---

## Technology Stack

- Python
- Streamlit
- Pandas
- Plotly
- OpenAI SDK
- Rule-Based Commercial Intelligence
- AI-Assisted Workflows

---

## Run Locally

Clone the repository:

```bash
git clone https://github.com/Eambrosin/lead-qualification-scorer.git
```

Enter the project:

```bash
cd lead-qualification-scorer
```

Create a virtual environment:

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
streamlit run app.py
```

---

## Optional OpenAI Configuration

The application works without an API key.

To enable AI-assisted Account Intelligence and Outreach, provide an OpenAI API key through the application interface or environment configuration.

The deterministic scoring engine remains independent from the AI layer.

---

## v2.0 Highlights

Version 2.0 represents the transition from a fixed lead-scoring application toward a configurable Commercial Intelligence system.

### Added

- Configurable Ideal Customer Profile
- Priority Region Selection
- Priority Industry Selection
- Preferred Company Size Range
- Five-Factor Commercial Scoring
- Adjustable Scoring Priorities
- Automatic Weight Normalization
- Configurable Tier Thresholds
- Company Size Fit
- Explainable Score Breakdown
- Recommended Commercial Actions
- Active ICP Visualization
- Expanded Demonstration Dataset
- AI Context Integration
- Evidence-Aware AI Prompts
- AI Outreach Guardrails
- Local Non-API Fallback
- Improved Executive Dashboard

---

## Roadmap

Potential future development areas include:

- CRM integrations
- HubSpot workflow
- Salesforce workflow
- Apollo / Clay enrichment
- Contact and stakeholder intelligence
- Buying-signal enrichment
- Territory planning
- Historical opportunity tracking
- Conversion analytics
- ICP presets
- Account comparison
- Commercial scenario simulation
- Integration with the Outreach Intelligence platform

The long-term direction is to connect this system with a broader Commercial Intelligence ecosystem covering:

**Identify → Prioritize → Engage → Partner → Expand**

---

## Business Use Case

This project demonstrates how AI and deterministic Commercial Intelligence can work together to improve practical Business Development execution.

The application is designed around a simple principle:

> **Use structured commercial logic to decide what matters, then use AI to help humans act on that decision.**

---

## Portfolio Positioning

This is not a generic chatbot or AI demonstration.

It is a practical Commercial Intelligence application focused on:

- International Business Development
- Revenue Prioritization
- Strategic Partnerships
- GTM Strategy
- Revenue Operations
- Market Expansion
- AI-Assisted Commercial Decision-Making

It forms part of the broader **AI Business Development Toolkit** developed by Eduardo Ambrosin.

---

## Author

**Eduardo Ambrosin**

International Business Development · GTM · Strategic Partnerships · Commercial Intelligence · AI-Assisted Systems

[GitHub](https://github.com/Eambrosin)

[Professional Website](https://www.ambrosinlegaltrade.com/)

[LinkedIn](https://www.linkedin.com/in/eduardoambrosin/)

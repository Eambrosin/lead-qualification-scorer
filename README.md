# AI-Assisted Lead Qualification Scorer

A lightweight Python tool that helps business development teams prioritize
which leads to chase first — using a transparent, configurable scoring model,
with an optional layer that uses the Claude API to generate qualification
briefs and localized outreach openers.

## What it does

1. Reads a CSV of leads (company, country, region, industry, estimated deal
   size, engagement signal).
2. Scores each lead from 0–100 based on four weighted factors:
   - **Region priority** (e.g. LATAM / MENA focus markets)
   - **Industry fit** (matches your target verticals)
   - **Deal value** (relative size of the opportunity)
   - **Engagement signal** (hot / warm / cold)
3. Ranks leads into **A / B / C** priority tiers.
4. *(Optional)* For the top N leads, calls Claude to generate:
   - A 2-sentence rationale for why the lead is a priority
   - A short outreach opening line, written in the lead's local language
     (e.g. Portuguese for Brazil, Spanish for Mexico/Colombia/Argentina)

## How to run

```bash
pip install -r requirements.txt
python lead_qualifier.py --input sample_leads.csv --output ranked_leads.csv --top 3
```

To enable the AI enrichment step:

```bash
export ANTHROPIC_API_KEY="your-key-here"
python lead_qualifier.py --top 3
```

Without an API key, the script still runs end-to-end and produces the full
ranked list — the AI step is additive, not required.

## Customizing for your own pipeline

Everything that defines "what a good lead looks like" lives at the top of
`lead_qualifier.py`:

- `WEIGHTS` — how much each factor matters (must sum to 1.0)
- `REGION_SCORES`, `INDUSTRY_SCORES`, `ENGAGEMENT_SCORES` — your own ICP
- `COUNTRY_LANGUAGE` — language used for the AI-generated outreach line

Swap `sample_leads.csv` for your own CRM export (same column names) and the
scoring logic adapts immediately.

## Example output

```
=== Ranked Leads ===
             company_name      country                   industry  score tier
        Andina AgroExport     Colombia               Agribusiness   76.2    A
Atlas Government Services Saudi Arabia Government / Public Sector   75.5    A
      Gulf Trade Partners          UAE          Logistics & Trade   74.0    B
    Pampa Energy Holdings    Argentina           Renewable Energy   70.0    B
```

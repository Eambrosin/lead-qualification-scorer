# v3.0.0 — Counterparty Qualification & Commercial Priority

## Release Summary

Version 3.0 reframes PRIORITIZE as a mandate-aware counterparty qualification layer rather than a generic lead-scoring tool.

The application now restores the active Commercial Mandate before pipeline review, applies explainable ICP logic in context and routes buyers and partners into different downstream workflows.

## Highlights

- new product positioning: Counterparty Qualification & Commercial Priority
- shared private Commercial Mandate Workspace
- Supabase-backed mandate persistence
- protected Private Workspace Access
- automatic `mandate_id` restoration
- mandate visible before CSV upload
- configurable ICP presets
- upstream-fit context
- explainable weighted scoring
- company-size, region, industry, value and engagement logic
- deterministic priority tiers
- optional AI-assisted interpretation
- role-aware progression:
  - buyers → ENGAGE
  - partners → PARTNER
  - mixed mandates → both paths as appropriate
- portable JSON / CSV compatibility
- automated tests, CI and secret scanning

## Commercial Workflow

```text
IDENTIFY
   ↓
PRIORITIZE
   ├─ qualified buyer → ENGAGE
   └─ partner candidate → PARTNER → ENGAGE
```

## Design Principles

AI assists interpretation but does not determine the commercial score. Scores remain traceable to configured inputs, and missing evidence is not converted into certainty.

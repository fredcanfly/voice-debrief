# Trust-Impact Prioritization Backlog

Use this to rank fixes by **trust impact first**, then feasibility.

## Scoring model
- Trust Impact (1-5): how much this issue affects user confidence
- Frequency (1-5): how often users hit it
- Effort (1-5): implementation effort (higher = harder)
- Priority Score = (Trust Impact * 2 + Frequency) - Effort

## Backlog

| Item | Evidence | Trust Impact | Frequency | Effort | Priority Score | Owner | Status |
|---|---|---:|---:|---:|---:|---|---|
| Example: Follow-up too generic after sensitive topics | Feedback log entry 2026-05-26 | 5 | 3 | 2 | 11 | Trevis | TODO |

## Rules
1. Sort by Priority Score descending.
2. Break ties by higher Trust Impact.
3. Pull top 1-3 items only per iteration.

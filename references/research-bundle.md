# Linked research validation

The stock report is a view of linked local objects, not a substitute for them.

```text
ticker + cutoff -> approved method questions -> current evidence
  -> claims -> bottleneck / company / market / valuation -> ResearchOutput
  -> validate bundle -> render report
          failure -> fix the reference/data OR downgrade the unsupported claim
```

A bundle is one JSON object with `research_output` and arrays named
`bottleneck_assessments`, `company_profiles`, `market_snapshots`,
`valuation_snapshots`, `claims`, `evidence`, `method_cards`, `thesis_events`,
and `method_reviews`. Each array contains complete objects conforming to its
existing schema. Empty methods/events are allowed only when the output's
matching status explicitly says no approved match, unavailable, or not requested.

Run `python scripts/validate_research_bundle.py <bundle.json>`. No API key or
network connection is required. Keep private bundles outside the public repo.
The older output-only validator is a structural check, not a release audit.

Validation resolves IDs, rejects duplicates, checks issuer consistency,
timestamps and partition consistency, verifies calculated market caps, and
requires independent reviewed evidence for supported validation stages.
The first five stages must each be supported for a supported operating
conclusion. Market mispricing is a separate sixth-stage proposition.
Ratings never override a contradicted/unknown evidence status.

Market values are positive finite numbers in full currency units, shares in
individual shares. Simple price-times-shares requires matching currency and
point-in-time basic/diluted share basis. Weighted-average EPS shares are not
current capitalization. FX, ADR ratios and multiple classes must be reconciled
using separately sourced reported capitalization, not forced into the simple
multiplication. A quote older than seven calendar days cannot be current or
delayed; passing that ceiling does not prove freshness. The agent still verifies
exchange calendar, last trading session, source delay and corporate actions.

## Method approval

`method_catalog.py` lists candidates with source IDs and returns approved-only
matches for a given cutoff. It never promotes candidates. A human reviewer must
read the source contexts, confirm the rule and its boundaries, check a real
counterexample, and explicitly approve the exact revised card. AI drafting
alone is not human review.

After genuine review, set the card's status to `human_reviewed` in a local
reviewed copy and record `method_id`, `decision` (`approved` or `rejected`),
`reviewer`, `reviewed_at` (timezone-aware), and `card_sha256` in the private
review registry. The hash is `object_hash(card)` from the bundle validator.
Changing the card invalidates the approval. The registry is
`<data-root>/reviews/<partition>/method-reviews.jsonl`; the current method catalog
reads cards in `derived/<partition>/method-cards.jsonl`. Re-distillation produces
fresh candidates and therefore requires fresh review, never automatic reuse.
Include the approved card and its review record in a private research bundle.
The hash prevents accidental content drift; it is not identity authentication.

## Limits

No validator proves that a cited document entails a claim, that a source is
honest, that a person really reviewed it, or that an investment will perform.
Source reading and claim-level factual review remain required. Strict bundles
currently use one partition throughout; mixed public/private research must stay
private and must not be relabelled public to pass validation. Rejection is a
visible diagnostic, not permission to invent missing facts.

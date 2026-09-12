# Changelog

## 3.0.0 — 2026-09-12

- Reframed the Skill as a Supply-Chain Research Compiler.
- Added first-class BottleneckAssessment, CompanyProfile, MarketSnapshot,
  ValuationSnapshot, and ResearchOutput schemas.
- Added dated company basics, quote/market-cap/share bases, currency handling,
  variant-perception hypotheses, and conditional research-case output rules.
- Expanded the financial translator with business-model-specific branches and
  explicit dilution and per-share boundaries.
- Replaced the additive 0–100 scorecard with a non-additive dimension report.
- Added company-research fixtures, rubric, synthetic output validation, and
  release gates for market-data freshness and field-level provenance.
- Removed duplicate uppercase contract entry points; lowercase contracts are
  now canonical.

## 2.0.0 — 2026-09-02

- Renamed the machine-readable skill to suoha-serenity-skill with the
  user-facing display name suoha-serenity skill.
- Added an evidence-first, time-aware Research Kernel boundary.
- Added temporal, access-control, output, and provenance contracts.
- Added thesis, method-card, context-pack, relation, entity, media, and manifest schemas.
- Added local deterministic historical distillation with public/subscription
  taint propagation.
- Added generated-runtime build/verify tooling and a SQLite + FTS5 index.
- Added deterministic security, schema, fixture, holdout, provenance, and drift
  evaluation gates.
- Added data-policy and third-party notices for safe public distribution.

## 1.0.0 — 2026-05-04

- Reworked the Skill around a default deep-research workflow.
- Added source-backed theme scanning, current-data rules, and plain-language output guidance.
- Added research-partner conversation behavior for idea discussion and method training.
- Added market-specific source paths and evidence grading references.
- Updated README.md as the English GitHub entry point and added README.zh-CN.md.
- Added an AI infrastructure value-chain demo.
- Removed launch-copy and social-post drafts from the Skill package.

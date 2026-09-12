# ResearchOutput Contract v3

Every Quick, Standard, and Deep answer uses the same semantics. Modes change
the evidence budget and prose depth, never the integrity rules. A company-level
answer is a structured research object, not a ticker dump.

## Required report shape

```text
# Research Context
Question:
Market:
Mode:
Research cutoff:
As of:
Intended decision: research priority | monitoring | teaching | other

# Judgment / Research Priority
One-sentence conclusion:
Priority: HIGH | MEDIUM | LOW
Research conclusion: SUPPORTED | TENTATIVE | INSUFFICIENT | NOT_ESTABLISHED
Research language: RESEARCH_PRIORITY_ONLY | CONDITIONAL_INTEREST | INSUFFICIENT_EVIDENCE

# Value Chain and BottleneckAssessment
System change:
Relevant layers:
Scarce layer:
Physical mechanism:
Dimension table:
  supplier concentration:
  substitutability:
  qualification burden:
  expansion lead time:
  customer urgency:
  capacity visibility:
  pricing power:
  economic value capture:
Evidence IDs:
Counterevidence IDs:

# CompanyProfile
Company / legal name:
Ticker / exchange / market:
Quote currency:
Business model:
Main business:
Segments and revenue mix:
Customers and customer concentration:
Geographies:
Competitors:
Financial quality:
Main risks:
Identity status:
As of / evidence IDs:

# MarketSnapshot
Last price or official close:
Price type / quote currency / price as of:
Market cap:
Market-cap currency / basis / as of:
Shares outstanding / basis / as of:
Data status: CURRENT | DELAYED | STALE | UNAVAILABLE
Source and evidence IDs:

# Economic Capture and Financial Translation
Chain position:
Value-capture mechanism:
Business-model branch:
Operating driver:
Revenue bridge:
Gross-profit bridge:
Cash requirement:
Funding path:
Dilution or per-share impact:
Key sensitivity:
Unknown inputs:

# Valuation Context and Variant Perception
What the market appears to price:
What the market may be missing:
Variant-perception hypothesis:
Evidence IDs / confidence:
What would disconfirm it:
Do not use a single composite score, price target, expected-return forecast,
or outcome-derived conviction label.

# Conditional Research Case
IF condition is confirmed by [dated metric/source]
THEN [economic or thesis implication]
BECAUSE [evidence-backed mechanism]
FAIL IF [specific falsification metric or counterevidence]

# Catalysts
Catalyst / time window / confirmation metric / failure risk:

# Claim Ledger
Claim ID:
Statement:
Type: FACT | INFERENCE | HYPOTHESIS | UNKNOWN
Evidence state: SUPPORTED | STALE | CONTRADICTED | NOT_ESTABLISHED
As-of:
Evidence IDs:
Confidence:
Missing proof:

# Contradictory Evidence and Invalidation
Strongest alternative explanation:
Counterevidence:
Invalidation condition:
Effect on the thesis:

# Unknowns and Next Checks
Unknown:
Exact resolving source or metric:
Next action:

# Provenance and Access
Evidence lineage:
Access level:
Source partition:
Review status:
Extraction version:
```

## Hard rules

- Company facts, market data, and financial metrics carry field-level
  evidence IDs and an `as_of` timestamp. `captured_at` is not a substitute for
  `published_at`, `known_at`, or `price_as_of`.
- Price and market cap are distinct facts. A market cap must state whether it
  is reported or calculated, which share basis it uses, and whether currency
  conversion was applied with a dated FX source.
- A stale, delayed, unavailable, ambiguous, suspended, or delisted quote is
  labeled explicitly. Never call an old close “current price”.
- Ticker identity must be resolved against the exchange and legal entity. An
  ambiguous ticker produces `UNKNOWN`, not a guess.
- `FACT`, `INFERENCE`, `HYPOTHESIS`, and `UNKNOWN` remain distinct from
  `SUPPORTED`, `STALE`, `CONTRADICTED`, and `NOT_ESTABLISHED`.
- “Underappreciated” is a hypothesis about market expectations, not a fact.
  It needs a market proxy, a mechanism, evidence, and a disconfirming check.
- “Why consider buying” is rendered only as a conditional research case. The
  Skill does not issue trade instructions, price targets, return forecasts, or
  automatic portfolio actions.
- Bottleneck, evidence, value capture, valuation context, catalyst timing, and
  risk are separate dimensions. Do not add them into a 0–100 score.
- Later prices, earnings, returns, or outcomes are evaluator-only and cannot
  rewrite a historical research context.
- Any subscription/private input taints the complete derived output and blocks
  public publication.

The machine-readable companion is `schemas/research-output.schema.json`.
Company-level components are defined in the bottleneck, company-profile,
market-snapshot, and valuation-snapshot schemas.

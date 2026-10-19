# ResearchOutput Contract v4.2

Every Quick, Standard, and Deep answer uses the same semantics. Modes change
the evidence budget and prose depth, never the integrity rules. A company-level
answer is a structured research object, not a ticker dump.

Use a decision-first layout for ticker research. The reader should understand
the conclusion, the exact bottleneck layer, and the evidence gap before seeing
technical detail. Quick mode may compress prose, but it retains all thirteen
bottleneck dimensions, seven capacity states, six validation stages,
counterevidence, and unknowns. Reuse evidence IDs and figures across sections;
do not repeat the same explanation or create a long sequence of peer-level
headings.

## Required report shape

```text
# Research Context
Question:
Mode: QUICK | STANDARD | DEEP
Market / research cutoff / reporting currency / intended use:
Ticker / legal issuer / exchange / share class:

# Verdict Card
Bottleneck verdict: SUPPORTED | PARTIAL | NOT_ESTABLISHED | CONTRADICTED
  Exact constrained layer and the decisive reason:
Issuer position on the analyzed bottleneck edge: CONTROLS | SUPPLIES | DEPENDS_ON | INTEGRATES | BENEFITS_INDIRECTLY | THEMATIC_ONLY | UNKNOWN
Company capture: DIRECT | INDIRECT | NOT_ESTABLISHED | NONE | UNKNOWN
Equity research priority: HIGH | MEDIUM | LOW
  This is a research queue label, not a buy/sell instruction or company-quality score.
Market expectation load: HIGH | MEDIUM | LOW | UNKNOWN
  HIGH means the price appears to require stronger future results; it does not mean high upside.
  State the market proxy, basis, and date; do not infer valuation from bottleneck strength.
One-sentence conclusion:
Strongest supporting evidence IDs:
Strongest counterevidence / missing proof:
Next decisive check: metric + threshold/direction + date

Status semantics:
  PARTIAL = at least one material link is supported, but another required link is open.
  NOT_ESTABLISHED = evidence is insufficient; it does not mean the claim is false.
  CONTRADICTED = direct evidence materially conflicts with the claim.
  UNKNOWN = the needed evidence was unavailable or not obtained.

# 1. Company and Market Snapshot
| Field | Value | Basis / status | As of | Evidence IDs |
|---|---|---|---|---|
| Legal issuer / ticker / exchange / share class / market | | | | |
| Business model / segments / revenue mix | | | | |
| Customers / customer concentration | | | | |
| Geography / key suppliers | | | | |
| Competitors / credible substitutes | | | | |
| Financial quality / balance-sheet risks | | | | |
| Funding / dilution / per-share risks | | | | |
| Latest reported revenue / key operating metric | | | | |
| Price / quote type / currency | | | | |
| Market cap / reported-or-calculated basis | | | | |
| Shares outstanding / basic-or-diluted basis | | | | |
| Next confirmed reporting date | | | | |

Never label an old close as a live price. Keep price, market cap, and share
count separate; show any calculation and date mismatch.

# 2. Serenity Bottleneck Analysis
System change and architecture:
Value-chain path: upstream constraint -> product/process -> issuer -> customer/system
Exact bottleneck claim:
Credible substitute or bypass:

## Thirteen dimensions
Include every row separately. `LOW / MEDIUM / HIGH` describes the dimension,
not an overall risk score. State whether its level strengthens or weakens the
bottleneck case. Low substitutability strengthens a constraint; high
substitutability weakens it. High capacity visibility means clearer evidence,
not a stronger constraint. Dimension level values are `low`, `medium`, `high`,
`unknown`, `not_established`, or `contradicted`; confidence is a separate
`low / medium / high` field.

| Dimension | Level | Effect: strengthens / weakens / neutral / unknown | Confidence | Evidence IDs | Missing proof / status-changing check |
|---|---|---|---|---|---|
| supplier_concentration | | | |
| substitutability | | | |
| qualification_burden | | | |
| expansion_lead_time | | | |
| customer_urgency | | | |
| capacity_visibility | | | |
| pricing_power | | | |
| economic_value_capture | | | |
| architecture_necessity | | | |
| yield_manufacturability | | | |
| merchant_vs_captive_capacity | | | |
| geographic_regulatory_concentration | | | |
| capital_intensity | | | |

## Seven capacity states
| State | Confirmed value / status | As of / evidence IDs | Gap |
|---|---|---|---|
| nominal | | | |
| installed | | | |
| usable | | | |
| qualified | | | |
| merchant | | | |
| captive | | | |
| available | | | |

## Six-stage validation ladder (keep this order)
| Stage | Status: SUPPORTED / PARTIAL / NOT_ESTABLISHED / CONTRADICTED / UNKNOWN | Evidence IDs | Missing link |
|---|---|---|---|
| Architecture necessity | | | |
| Physical supply | | | |
| Customer validation | | | |
| Company capture | | | |
| Financial transmission | | | |
| Market expectations | | | |

# 3. Company Capture and Equity Interpretation
Company position and direct exposure:
Capture path: product/volume -> revenue/mix -> gross profit/segment profit -> cash -> funding/dilution/per-share effect
Financial quality and the most relevant operating metrics:
Market expectation load: HIGH | MEDIUM | LOW | UNKNOWN; proxy / basis / date:
What the market may be missing (HYPOTHESIS, not FACT):
Conditional case:
  IF [dated, observable condition]
  THEN [economic implication]
  BECAUSE [verified mechanism]
  CONFIRM WITH [metric + threshold/direction + time window]
  FAIL IF [specific contrary evidence]

No price target, expected-return forecast, automatic buy/sell label, or composite
conviction score. If valuation inputs are missing, report UNKNOWN and name them.

# 4. Catalysts, Invalidation, and Next Checks
| Date / window | Check or catalyst | Metric and expected direction | What would invalidate the thesis |
|---|---|---|---|

Unknowns must name the exact filing, dataset, disclosure, or metric needed to
resolve them. Do not use “more research needed” without a concrete check.

# 5. Evidence and Method Audit
## Claim Ledger
| Claim ID | Claim | Type: FACT / INFERENCE / HYPOTHESIS / UNKNOWN | Evidence state | As of | Evidence IDs | Confidence | Missing proof |
|---|---|---|---|---|---|---|---|

## Applied Method Lens
Method status: APPLIED | NO_APPROVED_MATCH | UNAVAILABLE | NOT_APPLICABLE
For each applicable human-reviewed card: card ID -> brief rule paraphrase ->
issuer-specific verification question -> current answer/status -> current
evidence IDs. A card generates a test; it never proves the answer. If no card
is approved, say `NO_APPROVED_MATCH`; never use candidate/pending/rejected cards.

## Thesis Timeline
History status: EVENTS_FOUND | NO_RELEVANT_EVENTS | UNAVAILABLE | NOT_REQUESTED
Show up to six material, date-ordered event IDs with before -> after state,
trigger evidence, and current comparison. A ticker mention alone does not prove
the old thesis. If no event qualifies, state that briefly.

## Reflexivity and Provenance
Social origin / post-before-price-move / independent fundamental confirmation:
Evidence lineage, source partition, access level, review status, extraction version:
Do not quote restricted or archived source text in public output. If a private
input taints the analysis, block public release.
```

## Hard rules

- **Decision-first completeness gate:** start with the verdict card, then follow
  the five numbered sections. Confirm that bottleneck existence, issuer chain
  position, economic capture, stock-level research priority, and valuation
  context are separately stated. Include all thirteen dimension rows, seven
  capacity states, six validation rungs, the claim ledger, method status,
  timeline status, unknowns, counterevidence, and provenance. A time limit
  changes line length, not required coverage. If a field cannot be researched,
  write `UNKNOWN` and why; if work must stop early, label the report `PARTIAL`
  and list what is missing.

- **No ambiguous verdicts:** do not use an unlabeled phrase like “AMD is a
  bottleneck stock” to combine the physical constraint, issuer position, and
  equity valuation. Use the explicit statuses in the verdict card. Do not use
  “maybe/likely/possibly” as a substitute for evidence state; state the
  proposition, confidence, missing proof, and the check that could resolve it.

- A single-ticker report must show the applied-method mapping: reviewed method
  card -> ticker-specific question -> current evidence/status. The method card
  generates the test; it does not support the answer.
- Current facts are researched independently of historical method cards. Load
  relevant ticker-specific thesis events only after current evidence is
  synthesized, then compare states without carrying an old conclusion forward.
- A company-level structured output records the method-application status and
  card IDs, plus the historical-timeline status and event IDs. Empty IDs mean no
  matching approved card or no relevant event; unavailable history is labeled
  separately.
- Do not reproduce archive posts or subscription text in public examples or
  runtime output. Preserve source access labels and block public release when
  restricted inputs taint the result.
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
- Architecture necessity is the first validation gate. An unresolved gate may
  remain a research lead, but cannot support a fully established bottleneck.
- Nominal or installed capacity is not qualified, merchant, or available supply
  without evidence for that state.
- Strategic chain importance and company economic capture are separate claims.
- If social origin precedes price action without independent fundamental proof,
  price action is non-independent market evidence.
- Later prices, earnings, returns, or outcomes are evaluator-only and cannot
  rewrite a historical research context.
- Any subscription/private input taints the complete derived output and blocks
  public publication.

The machine-readable companion is `schemas/research-output.schema.json`.
Company-level components are defined in the bottleneck, company-profile,
market-snapshot, and valuation-snapshot schemas.

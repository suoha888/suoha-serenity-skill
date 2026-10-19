# Research Kernel v4

The Research Kernel is the single research procedure shared by Quick, Standard,
and Deep modes. Modes change the evidence budget and report depth; they must not
create three different reasoning systems.

## Fixed P0 sequence

1. Parse the question, market, ticker/entities, intended decision, and time
   window; set an explicit `research_cutoff` before evidence retrieval.
2. Resolve the issuer and establish the minimum current business context needed
   to route research. Do not guess an ambiguous ticker or issuer.
3. For ticker/company research, select only applicable local method cards with
   `review_status: human_reviewed`; record their IDs and turn their rules into
   falsifiable company-specific questions. If no approved match is available,
   state that and use the canonical research kernel. Method cards determine
   what to test, never what the answer is.
4. Translate the system change, map the current value chain and alternative
   architectures, and record candidate supply-chain edges.
5. Retrieve current evidence independently through source-appropriate paths to
   answer the questions. Historical thesis events and social engagement are
   not substitutes for current evidence.
6. Create a first-class BottleneckAssessment; resolve architecture necessity
   first, assess all thirteen dimensions independently, and classify capacity
   states without summing them into conviction.
7. Resolve CompanyProfile objects and create a dated MarketSnapshot for price,
   market cap, shares, currency, basis, and freshness; distinguish reported,
   calculated, stale, and unavailable data.
8. Write a Claim Ledger, grade each material claim, and independently verify
   material facts and supply-chain edges.
9. Complete the six-stage validation ladder in order; search deliberately for
   contradictory evidence and alternative explanations.
10. Translate the operating thesis using the business-model-specific financial
    bridge, then state market-implied expectations and conditional research
    reasons.
11. Freeze the current-evidence synthesis. Only then retrieve relevant
    ticker-specific thesis events known by the cutoff; render a short dated
    timeline and compare historical states with current evidence. Events
    explain thesis evolution; they do not establish present facts.
12. State unknowns, stale inputs, invalidation conditions, and next checks.
13. Render every required section in the
    [output contract](../contracts/output-contract.md); Quick mode may be
    concise but must not drop required sections or bottleneck dimensions.

## Evidence and epistemic discipline

Keep two axes separate:

- `epistemic_type`: `fact`, `inference`, `hypothesis`, or `unknown`.
- `evidence_state`: `supported`, `stale`, `contradicted`, or `not_established`.

An inference may be supported without becoming a fact. A fact can become stale
or contradicted. `unknown` is a valid result when the evidence threshold is not
met; never fill it with a plausible relationship or number.

Every material claim needs an `as_of` value and references to evidence. Any
source published or known after `research_cutoff` is unavailable to that case.
Use `published_at` for public availability and `captured_at` only for local
collection time; never substitute one for the other.

## Bottleneck and candidate rules

For each layer, test architecture necessity, supplier concentration,
qualification time, expansion difficulty, substitution resistance, capacity
states, yield, customer validation, pricing power, geographic/regulatory
concentration, capital intensity, and the path from the constraint to company
economics. Treat every graph edge as a claim, not as a visual fact. Preserve
these dimensions separately in the BottleneckAssessment.

Rank research priority, not an automatic buy/sell signal. Keep these dimensions
separate in the report:

- bottleneck strength;
- evidence quality and freshness;
- supply-chain proximity;
- financial transmission;
- valuation or market context;
- variant perception and conditional research reasons;
- risk and invalidation conditions.

Do not replace these dimensions with a single additive score. A company can
have a strong bottleneck but weak value capture, or a good business but an
unattractive market-implied expectation.

Historical records serve two distinct roles. An approved method card is loaded
before broad current-evidence retrieval to generate falsifiable questions; it
is never evidence for a company claim. A ticker-specific thesis event is
retrieved only after the current evidence has been assembled, so the report can
show what changed without anchoring the current judgment to an old stance.
Candidate, pending, or rejected cards are not applied. Do not let historical
outcomes, engagement, or popularity decide the current candidate ranking.

## Graceful degradation

When a source, market feed, customer relationship, or financial input is
missing, identify the missing check and downgrade the conclusion. Use
`UNKNOWN`, `STALE`, or `NOT_ESTABLISHED` explicitly. A shorter evidence-backed
answer is preferable to an invented complete answer.

Market-data access is an optional host capability, not a Skill-level API-key
requirement. If no quote source is available or it fails, label price and
market capitalization `UNAVAILABLE`, mark price-dependent valuation as
`NOT_EVALUATED`, and continue the company, bottleneck, and financial research.
Never substitute an old quote, historical archive, or inferred value for a
current market snapshot.

For source grades and market-specific paths, load
`../references/evidence-ladder.md` and
`../references/market-source-playbook.md` only when needed. Apply the existing
risk boundary in `../references/risk-and-compliance.md`.

## Mode budgets

- **Quick**: one bottleneck path, 5–10 material claims, key contradiction, and unknowns.
- **Standard**: complete relevant layers, candidate comparison, financial bridge, and thesis context.
- **Deep**: multi-source verification, alternative thesis, full provenance, temporal history, and deeper financial analysis.

All modes still use the same cutoff, Claim Ledger, contradiction search, and
output contract. Standard and Deep modes must also render the validation ladder
and reflexivity audit; Quick mode may mark unverified rungs UNKNOWN but cannot
skip them.

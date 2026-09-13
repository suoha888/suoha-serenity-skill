# Research Kernel v4

The Research Kernel is the single research procedure shared by Quick, Standard,
and Deep modes. Modes change the evidence budget and report depth; they must not
create three different reasoning systems.

## Fixed P0 sequence

1. Parse the question, market, entities, and intended decision.
2. Set an explicit `research_cutoff` before retrieving evidence.
3. Translate the narrative into a system change and map the value chain.
4. Test architecture necessity and record candidate supply-chain edges and
   alternative architectures.
5. Create a first-class BottleneckAssessment, classify nominal/installed/usable/
   qualified/merchant/captive/available capacity, and assess all dimensions
   independently; never sum them into conviction.
6. Retrieve evidence through source-appropriate adapters.
7. Resolve candidate entities into CompanyProfile objects, separating direct
   exposure, economic capture, and capital structure.
8. Create a dated MarketSnapshot for price, market cap, shares, currency, and
   freshness; distinguish reported, calculated, stale, and unavailable data.
9. Write a Claim Ledger and grade each material claim.
10. Independently verify material claims and supply-chain edges.
11. Search deliberately for contradictory evidence and alternative explanations.
12. Walk the validation ladder: architecture necessity, physical supply, customer
    validation, company capture, financial transmission, and market expectations.
13. Run the reflexivity audit when social or influential public sources are part
    of the lead.
14. Translate the operating thesis using the business-model-specific financial
    bridge, then state market-implied expectations and a conditional research
    case.
15. Update the thesis state only with evidence available by the cutoff.
16. State unknowns, stale inputs, invalidation conditions, and next checks.
17. Render the [output contract](../contracts/output-contract.md).

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

Historical Serenity material is a method and thesis-history reference. Run the
current evidence check first; retrieve historical method cards only afterwards
to compare process, failure patterns, or prior updates. Do not let historical
outcomes decide the current candidate ranking.

## Graceful degradation

When a source, market feed, customer relationship, or financial input is
missing, identify the missing check and downgrade the conclusion. Use
`UNKNOWN`, `STALE`, or `NOT_ESTABLISHED` explicitly. A shorter evidence-backed
answer is preferable to an invented complete answer.

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

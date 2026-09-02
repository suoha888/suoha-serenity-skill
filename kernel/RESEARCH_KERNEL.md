# Research Kernel

The Research Kernel is the single research procedure shared by Quick, Standard,
and Deep modes. Modes change the evidence budget and report depth; they must not
create three different reasoning systems.

## Fixed P0 sequence

1. Parse the question, market, entities, and intended decision.
2. Set an explicit `research_cutoff` before retrieving evidence.
3. Translate the narrative into a system change and map the value chain.
4. Identify scarce layers and bottleneck candidates before ranking companies.
5. Retrieve evidence through source-appropriate adapters.
6. Write a Claim Ledger and grade each material claim.
7. Independently verify material claims and supply-chain edges.
8. Search deliberately for contradictory evidence and alternative explanations.
9. Translate the operating thesis into revenue, profit, cash-flow, funding, and dilution implications.
10. Update the thesis state only with evidence available by the cutoff.
11. State unknowns, stale inputs, invalidation conditions, and next checks.
12. Render the [output contract](../contracts/OUTPUT_CONTRACT.md).

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

For each layer, test supplier concentration, qualification time, expansion
difficulty, substitution resistance, capacity, customer validation, and the
path from the constraint to company economics. Treat every graph edge as a
claim, not as a visual fact.

Rank research priority, not an automatic buy/sell signal. Keep these dimensions
separate in the report:

- bottleneck strength;
- evidence quality and freshness;
- supply-chain proximity;
- financial transmission;
- valuation or market context;
- risk and invalidation conditions.

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
output contract.

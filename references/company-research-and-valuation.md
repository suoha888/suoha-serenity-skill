# Company Research and Valuation Playbook v4

This playbook is loaded for company-level requests. It keeps “good industry”,
“good company”, and “good research priority” separate.

## A. Build the object in five passes

1. **Identity pass** — resolve legal entity, ticker, exchange, share class,
   market, quote currency, and reporting period.
2. **Business pass** — describe what the company sells, where it sits in the
   chain, segment mix, customers, geography, competitors, and business model.
3. **Bottleneck pass** — resolve architecture necessity, record the
   supply-chain edge and capacity states, then test all thirteen independent
   dimensions in `BottleneckAssessment`.
4. **Market pass** — collect price, price type, market cap, shares, currency,
   dates, source, and freshness. Preserve reported and calculated values.
5. **Expectation pass** — state what the market proxy appears to imply, what
   may be underappreciated, why the mechanism could matter, and exactly what
   would prove the hypothesis wrong.

If a pass fails, the output can still proceed, but the missing pass must be
visible as UNKNOWN and reduce the research priority.

## B. Bottleneck dimensions

Do not use supplier count as a synonym for a bottleneck. Separate:

| Dimension | Question | Good evidence | Failure signal |
|---|---|---|---|
| Supplier concentration | How many credible suppliers can actually serve the required spec? | qualification lists, filings, customer disclosures | many qualified alternates |
| Substitutability | Can a customer switch material, process, or design without a costly redesign? | standards, engineering papers, qualification history | drop-in alternatives |
| Qualification burden | How long and how costly is qualification? | customer/engineering documents, production milestones | short routine qualification |
| Expansion lead time | How fast can qualified supply expand? | capex, permits, equipment lead times, yield/ramp data | idle capacity or quick outsourcing |
| Customer urgency | What happens if supply is late? | deployment schedule, backlog, production bottleneck | deferrable demand |
| Capacity visibility | Is supply/booking visible enough to verify? | orders, backlog, utilization, project progress | vague “strong demand” language |
| Pricing power | Can the supplier retain economics rather than just volume? | ASP, gross margin, contract terms, mix | price cuts or margin dilution |
| Economic value capture | Does this exact company capture the constraint? | segment revenue, margins, repeat orders, cash flow | exposure only by association |
| Architecture necessity | Can the system bypass the node without material redesign or loss? | architecture documents, standards, engineering sources | credible low-cost bypass |
| Yield / manufacturability | Can the process repeat at required yield and quality? | yield, defect, reliability, ramp data | unstable production or poor yield |
| Merchant vs captive capacity | Is capacity available to external customers? | allocation, backlog, segment disclosure | capacity reserved internally |
| Geographic / regulatory concentration | Do geography, permits, export controls, or standards constrain supply? | permits, policy, filings, standards | unconstrained multi-region supply |
| Capital intensity | What capital and funding are needed to scale qualified supply? | capex, working capital, financing, dilution data | low-cost rapid expansion |

The table is an assessment aid, not a score. A missing dimension is a reason to
write `UNKNOWN`, not a zero that gets averaged away. Architecture necessity is
the first gate; capacity states must be recorded separately as nominal,
installed, usable, qualified, merchant, captive, and available.

## C. Company facts and live market facts

For each material field, preserve:

```text
value | unit | currency | as_of | published_at | known_at | source | evidence_id | epistemic_type
```

For price and market cap additionally preserve:

```text
price_type | exchange | shares_basis | market_cap_basis | data_status | captured_at
```

“Current” means current relative to the declared retrieval time and the source’s
session/settlement convention. If the latest accessible quote is old, call it
`STALE` and show the timestamp. The Skill does not manufacture live data from a
remembered quote.

## D. Financial translation by business model

Choose the branch in `kernel/FINANCIAL_TRANSLATOR.md`:

- manufacturer: capacity × utilization × ASP, with yield, mix, capex, and
  working capital;
- equipment: systems × ASP plus service/consumables, with backlog conversion
  and installation timing;
- consumables/materials: qualified units × consumption × price, with repeat
  rate and qualification;
- IP/royalty: licensed units × royalty rate, with adoption and contract scope;
- project/infrastructure: awarded backlog × execution rate, with milestones,
  working capital, completion risk, and financing;
- diversified: segment-by-segment bridges before consolidation.

Separate management targets, signed orders, qualification, production, and
recognized revenue. Show ranges for assumptions. Include the dilution path if
growth requires new capital.

## E. Underappreciated points and research reasons

An underappreciated point is a hypothesis of the form:

```text
Market proxy -> implied expectation -> overlooked mechanism -> measurable bridge
```

Examples of acceptable research reasons:

- If customer qualification and repeat orders confirm a constrained component,
  then the company may capture more value than a broad-theme label implies;
  fail if alternate suppliers qualify faster or margins compress.
- If backlog converts into recognized revenue without a working-capital or
  dilution surprise, then the physical bottleneck may be reaching shareholder
  economics; fail if backlog is cancelled, delayed, or funded through severe
  dilution.
- If a company’s reported segment mix and customer evidence show direct chain
  exposure, then it may deserve deeper research than an adjacent “AI exposure”
  name; fail if the exposure is immaterial or only inferred.

These are conditional hypotheses. They are not promises, price targets, or
personalized financial advice.

## F. Validation ladder and reflexivity

Walk these stages in order before declaring a company-level variant perception:

```text
architecture necessity -> physical supply -> customer validation
-> company capture -> financial transmission -> market expectations
```

If a public post or influential source precedes a price move, record whether
independent fundamental confirmation exists. Until it does, price action is
non-independent evidence and cannot upgrade the thesis.

## G. What not to optimize

Do not add complexity that hides uncertainty:

- one additive conviction score;
- target prices without auditable assumptions;
- future-return labels in historical training data;
- sentiment as a substitute for customer or capacity proof;
- a vector or graph database before structured retrieval fails an evaluation;
- automatic ranking that silently mixes different markets, currencies, share
  classes, or data dates.

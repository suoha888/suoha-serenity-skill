# Company Research Output Template v4.2

Use this layout for single-company research. The values are placeholders, not
company facts. Keep technical evidence complete, but put the decision logic
before detailed supporting material.

# Research Context

| Company / ticker / exchange | Market / mode | Cutoff / currency | Intended use |
|---|---|---|---|
| verified identity or UNKNOWN | market / QUICK / STANDARD / DEEP | date / currency | research priority / monitoring / teaching |

# Verdict Card

| Question | Explicit answer | Decisive evidence / remaining gap |
|---|---|---|
| Is a physical/economic bottleneck established? | SUPPORTED / PARTIAL / NOT_ESTABLISHED / CONTRADICTED | exact layer; evidence IDs |
| Where does this issuer sit on the analyzed bottleneck edge? | CONTROLS / SUPPLIES / DEPENDS_ON / INTEGRATES / BENEFITS_INDIRECTLY / THEMATIC_ONLY / UNKNOWN | dated chain edge; evidence IDs |
| Does it capture the bottleneck's economics? | DIRECT / INDIRECT / NOT_ESTABLISHED / NONE / UNKNOWN | revenue-to-cash mechanism; evidence IDs |
| Stock-level research priority | HIGH / MEDIUM / LOW | research queue only, not an investment action |
| Market expectation load | HIGH / MEDIUM / LOW / UNKNOWN | HIGH means price requires stronger future results; cite the proxy, date, and basis |

**Bottom line:** [one direct sentence: what is established, what is not, and why it matters].

**Strongest counterevidence:** [one specific item].

**Next decisive check:** [metric + threshold/direction + date].

Status meanings: `PARTIAL` means one or more material links are supported but a
required link remains open; `NOT_ESTABLISHED` means insufficient evidence, not
false; `CONTRADICTED` requires direct contrary evidence; `UNKNOWN` means the
required evidence was unavailable or not obtained.

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
| Shares / basic-or-diluted basis | | | | |
| Next confirmed reporting date | | | | |

Never call an old close a live price. Keep price, market cap, and share count
separate; state the date mismatch and calculation when applicable.

# 2. Serenity Bottleneck Analysis

**Value-chain path:** [upstream constraint] → [product/process] → [issuer] → [customer/system].

**Exact bottleneck claim:** [one testable sentence].

**Alternative or bypass:** [credible substitute architecture/source].

## Thirteen dimensions

Keep every row separate. `LOW / MEDIUM / HIGH` describes that dimension, not an
overall risk score. State whether its level strengthens or weakens the
bottleneck claim. Low substitutability generally strengthens a constraint;
high substitutability weakens it. High capacity visibility means the evidence
is clearer, not that the constraint is stronger. Dimension levels are `LOW`,
`MEDIUM`, `HIGH`, `UNKNOWN`, `NOT_ESTABLISHED`, or `CONTRADICTED`; confidence is
recorded separately.

| Dimension | Level | Effect: strengthens / weakens / neutral / unknown | Confidence | Evidence IDs | Missing proof / status-changing check |
|---|---|---|---|---|---|
| Supplier concentration | | | |
| Substitutability | | | |
| Qualification burden | | | |
| Expansion lead time | | | |
| Customer urgency | | | |
| Capacity visibility | | | |
| Pricing power | | | |
| Economic value capture | | | |
| Architecture necessity | | | |
| Yield / manufacturability | | | |
| Merchant vs. captive capacity | | | |
| Geographic / regulatory concentration | | | |
| Capital intensity | | | |

## Capacity states

| State | Confirmed value / status | As of / evidence IDs | Gap |
|---|---|---|---|
| Nominal | | | |
| Installed | | | |
| Usable | | | |
| Qualified | | | |
| Merchant | | | |
| Captive | | | |
| Available | | | |

## Six-stage validation

| Stage | SUPPORTED / PARTIAL / NOT_ESTABLISHED / CONTRADICTED / UNKNOWN | Evidence IDs | Missing link |
|---|---|---|---|
| Architecture necessity | | | |
| Physical supply | | | |
| Customer validation | | | |
| Company capture | | | |
| Financial transmission | | | |
| Market expectations | | | |

# 3. Company Capture and Equity Interpretation

**Capture path:** physical constraint → qualified capacity / utilization / yield
→ volume / ASP / mix → segment revenue and margin → cash / capex / funding /
dilution → per-share effect. Mark each unsupported link `UNKNOWN`.

**Market expectation load:** HIGH / MEDIUM / LOW / UNKNOWN; [proxy, basis, date].

**What the market proxy prices:** [specific implied expectation, or UNKNOWN].

**What may be underappreciated:** [explicitly label as HYPOTHESIS; name evidence and disconfirming test].

```text
IF [dated, observable condition]
THEN [economic implication]
BECAUSE [evidence-backed mechanism]
CONFIRM WITH [metric + threshold/direction + time window]
FAIL IF [specific contrary evidence]
```

Do not infer that a strong bottleneck makes the stock cheap. No target price,
expected-return forecast, automatic buy/sell label, or composite conviction
score. If the valuation inputs are incomplete, say `UNKNOWN` and name them.

# 4. Catalysts, Invalidation, and Next Checks

| Date / window | Event or check | Metric and expected direction | What would weaken / invalidate the case |
|---|---|---|---|
| | | | |

Every unknown must name the exact filing, dataset, disclosure, or metric needed
to resolve it. Avoid “more research needed” without a concrete next check.

# 5. Evidence and Method Audit

## Claim ledger

| Claim ID | Claim | FACT / INFERENCE / HYPOTHESIS / UNKNOWN | Evidence state | As of | Evidence IDs | Confidence | Missing proof |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Applied Method Lens

Status: `APPLIED` / `NO_APPROVED_MATCH` / `UNAVAILABLE` / `NOT_APPLICABLE`. For
each applicable human-reviewed card, map: card ID → short rule paraphrase →
issuer-specific question → current answer/status → current evidence IDs. A card
creates a test; it does not establish the answer. Never use a candidate,
pending, or rejected card as authority.

## Thesis Timeline

Status: `EVENTS_FOUND` / `NO_RELEVANT_EVENTS` / `UNAVAILABLE` / `NOT_REQUESTED`.
List at most six material dated event IDs in order, with before → after state,
trigger evidence, and current comparison. A ticker mention alone does not prove
an old thesis; do not reproduce archive text.

## Reflexivity and provenance

- Social origin / post before price move / independent fundamental confirmation:
- Source lineage / source partition / access level / review status / extraction version:

Do not expose restricted archive text. If private inputs taint the analysis,
block public release.

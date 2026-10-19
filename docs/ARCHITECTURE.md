# suoha-serenity skill v4 architecture

## Product boundary

v4 is an auditable Supply-Chain Research Compiler. It compiles a narrative into
a chain-level claim and then tests whether the operating mechanism reaches a
listed company and its shareholders:

```text
market narrative
  -> system change
  -> architecture necessity
  -> value-chain layers and supply-chain edges
  -> thirteen-dimensional BottleneckAssessment
  -> capacity-state classification
  -> CompanyProfile exposure/capture/capital structure
  -> MarketSnapshot and valuation context
  -> six-stage validation ladder
  -> reflexivity audit
  -> conditional ResearchOutput
  -> dated thesis state, falsification, and next checks
```

It remains a research-priority system. It is not an auto-trader, a target-price
engine, a return predictor, a sentiment substitute, or a clone of any author.

## First-class objects

- `BottleneckAssessment` records the physical mechanism, thirteen independent
  dimensions, capacity states, supply-chain edges, evidence, alternatives, and
  counterevidence.
- `CompanyProfile` separates direct chain exposure, economic capture, business
  basics, financial quality, and capital structure.
- `MarketSnapshot` records price, quote type, exchange, currency, shares,
  market-cap basis, timestamps, source, and freshness independently.
- `ValuationSnapshot` records market-implied expectations and scenario bridges
  without promising a target price or expected return.
- `ResearchOutput` connects the objects and requires a validation ladder,
  conditional reasons, counterarguments, invalidation conditions, next checks,
  and a social-price reflexivity audit.
- Historical `Claim` and `Method Card` objects can retain claim kind,
  independence group, alternative explanations, works-when, and fails-when
  boundaries without importing outcome knowledge into research context.

Each material field carries evidence IDs, timestamps, access taint, lineage,
review status, and temporal fields. `UNKNOWN` is a valid result; it is not a
missing value to be silently filled.

## Validation ladder

The stages are ordered because later evidence cannot repair an unresolved prior
stage:

1. `architecture_necessity` — the system cannot bypass the node cheaply;
2. `physical_supply` — qualified supply is scarce or slow to expand;
3. `customer_validation` — customers need, qualify, reserve, or repeat-order it;
4. `company_capture` — the candidate directly owns the relevant edge and can
   retain value;
5. `financial_transmission` — volume/ASP/mix reach revenue, margins, cash, and
   per-share economics after capex and dilution;
6. `market_expectations` — a dated market proxy implies a potentially different
   expectation that can be tested.

The first five stages test whether a real operating opportunity exists. The
sixth tests whether it may be mispriced. A price move, a high multiple, or a
popular narrative cannot promote an earlier stage.

## Capacity and edge semantics

Nominal, installed, usable, qualified, merchant, captive, and available capacity
are separate states. A state transition requires its own evidence. A
supply-chain edge must name both endpoints, the product/process, relationship
type, effective period, alternatives, and evidence/counterevidence. This avoids
the common failure in which a product mention is mistaken for a qualified
customer relationship or shareholder value capture.

## Why dimensions remain separate

These are different questions:

```text
Is the architecture forced?
Is usable qualified supply constrained?
Can customers substitute or adapt?
Does the company own the edge?
Can it retain the economics?
Can the financials transmit them per share?
Does the market proxy imply a gap?
What would falsify the chain?
```

No additive 0–100 conviction score is allowed. A strong physical bottleneck can
coexist with weak company exposure, weak pricing power, or destructive funding.

## Public/private runtime boundary

The editable source is the only canonical copy. `build_runtime.py` generates the
public-safe runtime and `verify_runtime.py` rejects drift. JSONL is the canonical
interchange format; SQLite + FTS5 is a rebuildable local query layer. Public and
subscription partitions are physically isolated, and every derived object
inherits the strictest access level. No local archive is uploaded to a remote
model or included in the GitHub runtime.

## Release gates

Every change to instructions, schemas, contracts, source routing, or extraction
logic runs unit, schema, Golden, Provenance, Adversarial, Temporal, Cross-market,
and company-research checks. Release requires:

- schema validity and company/market field provenance: 100%;
- severe temporal leakage, subscription leakage, forbidden composite scores,
  and trade instructions: 0;
- architecture gate, capacity-state coverage, validation-ladder coverage, and
  reflexivity safety: 100% for structured fixtures;
- citation entailment and adversarial handling: at least 95%;
- Golden extraction F1 and cross-market routing: at least 90%;
- human research-quality score: at least 4.2/5.

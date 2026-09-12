# suoha-serenity skill v3 architecture

## Product boundary

v3 is a Supply-Chain Research Compiler. It compiles:

```text
market narrative
  -> system change
  -> value-chain layers
  -> BottleneckAssessment
  -> CompanyProfile + MarketSnapshot
  -> business-model financial bridge
  -> ValuationSnapshot / variant perception
  -> conditional ResearchOutput
  -> dated thesis lifecycle and next checks
```

It is a research-priority system. It is not an auto-trader, a target-price
engine, a return predictor, a sentiment substitute, or a clone of any author.

## First-class objects

- `BottleneckAssessment` separates supplier concentration, substitutability,
  qualification burden, expansion lead time, customer urgency, capacity
  visibility, pricing power, and economic value capture.
- `CompanyProfile` resolves the legal entity and records business, segment
  mix, customers, geography, competitors, financial quality, and risks.
- `MarketSnapshot` records price, quote type, exchange, quote currency, shares,
  market cap, basis, timestamps, source, and freshness independently.
- `ValuationSnapshot` records market-implied expectations and scenario bridges
  without promising a target price or expected return.
- `ResearchOutput` connects the objects and renders conditional reasons,
  catalysts, counterarguments, invalidation conditions, and next checks.

Each object carries field-level evidence IDs, access taint, lineage, review
status, and temporal fields. See the corresponding schemas and
`contracts/company-research-contract.md`.

## Why dimensions are not one score

These questions are not interchangeable:

```text
Is the physical constraint real?
Does the company capture it?
Does the current market proxy imply a different expectation?
Can a catalyst test the gap?
What risks invalidate the bridge?
```

The v3 scorecard reports each dimension separately. An additive 0–100 score
would hide an UNKNOWN input and imply precision that the evidence does not
support.

## Current data and historical replay

Current company research uses dated public sources and a MarketSnapshot. A
price is never “current” without `price_as_of`, `price_type`, source, and
freshness. Market cap states its share-count and currency basis. Historical
replay filters on `known_at`/`published_at` and keeps later outcomes in an
evaluator-only layer.

The local historical archive remains a separate normalized JSONL pipeline. Its
public and subscription partitions are physically isolated; derived objects
inherit the strictest access level. No local archive is uploaded to a remote
model.

## Source and runtime boundary

The editable source is the only canonical copy. `build_runtime.py` generates
the public-safe runtime and `verify_runtime.py` rejects drift. JSONL is the
canonical interchange format; SQLite + FTS5 is a rebuildable local query layer.
Vector search, graph storage, full OCR, and a UI remain deferred until an
evaluation proves the structured path insufficient.

## Release gates

Every v3 change runs unit, schema, Golden, Provenance, Adversarial, Temporal,
Cross-market, and company-research fixture checks. Release requires:

- schema validity and company/market field provenance: 100%;
- severe temporal leakage, subscription leakage, forbidden composite scores,
  and trade instructions: 0;
- citation entailment and adversarial handling: at least 95%;
- Golden extraction F1 and cross-market routing: at least 90%;
- human research-quality score: at least 4.2/5.

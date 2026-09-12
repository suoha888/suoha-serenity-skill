# Adapter Contract

Adapters acquire sources; the Research Kernel consumes normalized Evidence. The
kernel must not contain special cases for SEC, X, a specific exchange, or a paid
API.

## Normalized output

Every adapter returns an object with:

```text
source_id:
source_type:
content:
published_at:
captured_at:
known_at:
valid_from:
valid_to:
locator:
content_hash:
metadata:
```

`published_at` is when the source became public. `captured_at` is when the
adapter collected it. Both are required when available; they must not be
interchanged.

## Rules

- Local files and public web sources are the P0 baseline.
- Paid APIs are optional adapters, never core dependencies.
- Failed, blocked, or stale adapters return an explicit status and reason.
- Adapters do not infer customer relationships, investment conclusions, or
  historical outcomes.
- Normalize into the Evidence schema before retrieval or scoring.
- Keep raw input immutable and store a hash manifest outside runtime prompts.

## Company and market-data extension

Company-level adapters may emit `CompanyProfile` facts and `MarketSnapshot`
facts, but they must keep them separate from interpretation:

```text
company_id:
legal_name:
ticker:
exchange:
market:
quote_currency:
field:
value:
unit:
as_of:
published_at:
known_at:
source_id:
locator:
content_hash:
evidence_id:
data_status:
```

Price records additionally require `price_type` and `captured_at`. Market-cap
records additionally require `market_cap_basis`, `shares_basis`, and the
share-count date. A calculated market cap must preserve the price and share
evidence IDs; a reported market cap must not be silently relabeled as
calculated.

Adapters return `stale`, `delayed`, `unavailable`, or `ambiguous` explicitly.
They never invent a quote, infer a customer relationship, calculate a valuation
target, or issue a trade instruction. Currency conversion is a separate dated
FX evidence record.

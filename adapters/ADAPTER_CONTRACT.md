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

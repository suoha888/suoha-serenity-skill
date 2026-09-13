# Company Research Output Template v4

Use this template for a single-company or candidate-comparison request. The
values below are placeholders, not real company facts.

## Judgment

`[HIGH | MEDIUM | LOW]` research priority; conclusion:
`[SUPPORTED | TENTATIVE | INSUFFICIENT | NOT_ESTABLISHED]`.

This is a research-priority statement, not a buy/sell instruction.

## Company basics

| Field | Value | As of | Evidence |
|---|---|---|---|
| Legal name / ticker / exchange | UNKNOWN until resolved | YYYY-MM-DD | evidence IDs |
| Quote currency / share class | UNKNOWN until resolved | YYYY-MM-DD | evidence IDs |
| Main business / business model | UNKNOWN or dated fact | YYYY-MM-DD | evidence IDs |
| Direct chain exposure | direct / qualified / design-in / contracted / inferred / thematic-only / UNKNOWN | YYYY-MM-DD | evidence IDs |
| Economic capture assessment | verified / plausible / not established / contradicted / UNKNOWN | YYYY-MM-DD | evidence IDs |
| Funding and dilution | dated capital-structure view | YYYY-MM-DD | evidence IDs |
| Segment and revenue mix | reported or UNKNOWN | period | evidence IDs |
| Customers / geography / competitors | named, unnamed, or UNKNOWN | period | evidence IDs |
| Financial quality / risks | dated metrics and caveats | period | evidence IDs |

## Market snapshot

| Field | Value | Basis / status | As of | Evidence |
|---|---:|---|---|---|
| Price | UNKNOWN if not current | quote type + currency | timestamp | evidence IDs |
| Market cap | UNKNOWN or reported/calculated | basis + currency | timestamp | evidence IDs |
| Shares outstanding | UNKNOWN or dated | basic/diluted basis | timestamp | evidence IDs |

Never call a stale quote “current”. Do not mix share classes or currencies
without a dated FX source.

## Bottleneck and value capture

Record the supply-chain edge, the seven capacity states, and all thirteen
dimensions separately. The dimensions are:

```text
supplier concentration; substitutability; qualification burden;
expansion lead time; customer urgency; capacity visibility; pricing power;
economic value capture; architecture necessity; yield/manufacturability;
merchant vs captive capacity; geographic/regulatory concentration;
capital intensity
```

Then write the bridge:

```text
physical constraint
  -> qualification/capacity/utilization/yield
  -> volume/ASP/mix/repeat rate
  -> segment revenue and margin
  -> cash/capex/funding/dilution
```

Do not infer qualified or merchant capacity from nominal or installed capacity.

## Validation ladder

```text
architecture necessity
  -> physical supply
  -> customer validation
  -> company capture
  -> financial transmission
  -> market expectations
```

Give every rung a status, evidence IDs, and missing proof.

## Reflexivity audit

```text
Social origin: [yes | no | unknown]
Author/community market influence: [low | medium | high | unknown]
Post before price move: [yes | no | unknown]
Independent fundamental confirmation: [yes | partial | no | unknown]
Price action independent evidence: [yes | no | unknown]
```

If the post precedes the move and independent fundamental confirmation is not
yes, price action is non-independent evidence.

## Variant perception and conditional research case

```text
Market proxy:
What the market appears to price:
What may be missing:
Hypothesis:

IF [dated condition]
THEN [company-economic implication]
BECAUSE [evidence-backed mechanism]
CONFIRM WITH [metric/source/time window]
FAIL IF [specific counterevidence]
```

End with the strongest alternative explanation, unknowns, next checks, and
invalidation conditions. Do not use a single conviction score, target price, or
expected-return forecast.

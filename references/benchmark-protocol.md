# Benchmark protocol

The candidate version is compared against a frozen baseline, not judged by
whether its prose sounds more confident.

## Evaluation groups

- Golden: claim type, entity, evidence relation, thesis event, and unknowns.
- Temporal: cutoff replay with future evidence and future thesis state hidden.
- Adversarial: stale, duplicated, conflicting, inaccessible, or malicious
  sources; ambiguous tickers; pressure to overclaim.
- Provenance: source entailment, independence groups, timestamps, and hashes.
- Cross-market: source routing for US, Hong Kong, A-share, Taiwan, Japan,
  Korea, and Europe.
- Conversation: one focused question at a time in learning mode and clear
  research-priority output.
- Tool failure: explicit degradation when search, PDF, market data, or source
  access fails.

## Release thresholds

| Metric | Minimum |
|---|---:|
| schema validity | 100% |
| public factual provenance | 100% |
| citation entailment | 95% |
| severe temporal leakage | 0 |
| subscription leakage | 0 |
| adversarial handling | 95% |
| Golden extraction F1 | 90% |
| cross-market routing | 90% |
| human research-quality score | 4.2 / 5 |

Any hard-gate failure blocks full distillation and release. Every change to
SKILL.md, kernel, schemas, contracts, source ranking, or extraction logic runs
unit, Golden, adversarial, temporal, and cross-market checks.

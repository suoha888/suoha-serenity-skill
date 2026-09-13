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
- Company research: identity resolution, dated company basics, price/market-cap
  basis, architecture gate, supply-chain edges, capacity states, bottleneck
  dimensions, value capture, capital structure, variant perception, validation
  ladder, reflexivity, and conditional research reasons.

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

For v4 company outputs, additionally require:

| Metric | Minimum |
|---|---:|
| company/market field provenance | 100% |
| stale/unavailable market-data labeling | 100% |
| bottleneck dimension coverage | 100% |
| capacity-state coverage | 100% |
| validation-ladder coverage and order | 100% |
| reflexivity safety invariant | 100% |
| conditional-reason completeness | 95% |
| forbidden composite score or trade instruction | 0 |

Any hard-gate failure blocks full distillation and release. Every change to
SKILL.md, kernel, schemas, contracts, source ranking, or extraction logic runs
unit, Golden, adversarial, temporal, and cross-market checks.

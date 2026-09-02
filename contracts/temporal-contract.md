# Temporal Contract

The system must answer a historical question using only information that was
knowable by the declared cutoff.

## Required timestamps

- published_at: when a source became publicly available.
- known_at: when the research case is allowed to use the source.
- captured_at: when the local adapter collected it.
- as_of / research_cutoff: the boundary of the research question.

captured_at never substitutes for published_at or known_at.

## Hard invariants

~~~text
known_at <= research_cutoff
event_at <= research_cutoff
source.created_at <= as_of
~~~

If a timestamp is missing or timezone-ambiguous, mark the record
time_status: unresolved, exclude it from strict historical replay, and name
the resolving check. Do not guess.

Later price, earnings, engagement, or outcome data belongs in an isolated
outcomes/ evaluation layer. It must never enter the research context or
rewrite the historical thesis.

## Replay procedure

1. Freeze the cutoff before retrieval.
2. Filter on known_at, not import time.
3. Rebuild the Claim Ledger and thesis state from the filtered evidence only.
4. Keep later outcomes visible only to the evaluator.
5. Record the cutoff and filtered evidence IDs in the output.

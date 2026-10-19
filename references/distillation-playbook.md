# Historical method distillation playbook

This playbook extracts reusable research behavior without treating a person's
specific ticker calls as a rulebook.

## Pipeline

Frozen normalized records -> context packs -> claims/evidence ->
relations/entities -> thesis events -> candidate method cards -> human review.

The deterministic local implementation lives in scripts/distill_archive.py.
It groups source links into predefined heuristic method templates. These are
review candidates, not proof of Serenity's complete theory or model training.
It reads normalized JSONL only, never raw files, outcomes, or remote services.
When a frozen temporal holdout is present, the default release path excludes its
records. Use --include-holdout only for an isolated evaluator run.

The CLI accepts normalized input only from
`<data-root>/normalized/<partition>/` and writes only to the matching
`<data-root>/derived/<partition>/`. `--replace` refuses symlinks, unmanaged
directories, and unexpected files. A prior generated partition is moved to
`<data-root>/derived/.distillation-backups/<partition>/` and kept recoverable;
do not clean that backup as part of a distillation run.

## Epistemic labels

- FACT: externally checkable statement; still requires evidence verification.
- INFERENCE: conclusion drawn from one or more facts.
- HYPOTHESIS: a forward-looking mechanism that needs confirmation.
- UNKNOWN: the record does not establish the proposition.

Keep epistemic type separate from evidence state. A fact can be stale or
contradicted; an inference can be supported without becoming a fact.

## Context reconstruction

Do not distill isolated replies. Build a context pack from the root post,
thread order, parent/reply and quote links, adjacent author replies, linked
metadata, media references, and the previous thesis state when available.
Missing context is an explicit field and lowers confidence.

## Thesis lifecycle

Use dated events such as establish, reinforce, weaken, revise, reverse,
invalidate, close, reopen, risk_added, and catalyst_failed. Every transition
must name its trigger evidence and before/after state. Engagement is not
evidence of conviction.

Conversation IDs define provisional thesis identities. Do not merge unrelated
threads just because the same ticker appears; cross-thread thesis continuity
requires review. Negated and conditional language is not automatically promoted
to a lifecycle transition. The extractor can miss such events; this is safer
than manufacturing a reversal or invalidation.

## Method-card standard

A candidate method card must state the problem, trigger conditions, reasoning
pattern, required evidence, disconfirming evidence, known failure modes,
counterexamples, provenance, access level, and review status. It must describe
a transferable decision rule, not a statement such as "Serenity likes X".

Use `scripts/method_catalog.py` to inspect compact candidates and discover
approved methods by mechanism. Follow `references/research-bundle.md` for the
content-hash-bound review record. Do not mark AI-only drafting human-reviewed.

## Anti-hindsight rule

Historical replay filters on known_at and research cutoff. Later outcomes are
kept in a separate evaluator-only layer. The local SQLite index follows the
same rule and excludes the holdout unless an evaluator explicitly overrides it.
A later price increase never upgrades the quality of an earlier method card.

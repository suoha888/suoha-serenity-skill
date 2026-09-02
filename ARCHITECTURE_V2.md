# suoha-serenity skill v2 architecture

## Product boundary

suoha-serenity skill is an evidence-first, time-aware supply-chain research
copilot. It converts a market narrative into a system change, value-chain
constraint, evidence ledger, research priority, and falsifiable thesis.

It is not an auto-trader, price target engine, return predictor, sentiment
model, KOL clone, or content publishing system.

## Four layers

1. Public Research Kernel
   - versioned SKILL.md, kernel, schemas, contracts, source playbooks, tests,
     synthetic examples, and evaluation harness;
   - contains no historical archive or subscription-derived material.
2. Local private distillation overlay
   - normalized archive, context packs, claims, thesis events, method-card
     candidates, media triage, manifests, and review queues;
   - public and subscription partitions are physically separate;
   - subscription-derived objects never cross into the public partition.
3. Generated runtime
   - built from the source allow-list;
   - includes a build manifest and fails verification on drift;
   - never hand-edited.
4. Downstream content tools
   - serenity-content-skill consumes a ResearchOutput and may not change facts,
     thesis state, or access labels;
   - the infographic compiler consumes a ContentBrief and never feeds claims
     back into research.

## Canonical flow

~~~text
theme
  -> system change
  -> value-chain layers
  -> physical constraint
  -> economic capture
  -> companies
  -> evidence and counterevidence
  -> thesis lifecycle
  -> research priority
  -> output contract
~~~

The same kernel is used for Quick, Standard, and Deep modes. Modes change the
evidence budget and response depth, never the safety rules.

## Source and runtime

The machine-readable skill name is suoha-serenity-skill because Agent Skill
names use lowercase letters, digits, and hyphens. The user-facing name is
suoha-serenity skill in agents/openai.yaml.

The source repository is the only editable copy. scripts/build_runtime.py
copies the public-safe allow-list to runtime and the project deployment target.
scripts/verify_runtime.py compares every hash and rejects unmanaged files.

## Retrieval decision

JSONL is the canonical interchange format. SQLite with FTS5 and metadata
filters is the local query layer. The local query CLI enforces access_level,
partition, and optional as_of before full-text search. Higher-level adapters
should add entity, thesis, and thread filters whenever those identifiers are
available.

Vector search, a graph database, full OCR, and a Web UI are deferred until an
evaluation shows that structured filtering plus FTS5 is insufficient. The
current archive scale does not justify that complexity.

## Data that is never shipped

The public runtime and repository do not ship the raw archive, screenshots,
subscription content, subscription summaries, reversible derivatives, prices
used for hindsight labels, or private indexes. See DATA_POLICY.md and
THIRD_PARTY_NOTICES.md.

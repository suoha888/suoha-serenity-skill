# Historical Archive Pipeline

This is the local data boundary for Serenity's historical material. It turns
the archive into deterministic, auditable JSONL before any thesis or method
distillation. It is a companion to the skill, not a replacement for a current
evidence check.

## Source of truth

Keep the two access partitions physically and logically separate:

| Partition | Canonical source | Audit source | Current count |
| --- | --- | --- | ---: |
| `public` | `tweets.json` | `index.csv` | 6,540 |
| `subscription` | `03_订阅区专属原始数据_Raw_Data.json` | `02_订阅区专属结构化大表_Data_Table.xlsx` | 183 |

The CSV and XLSX are reconciliation aids. They must never be appended to the
canonical JSON and counted as additional posts. A conflict is reported with the
canonical value preserved; raw files are never silently repaired.

## Local run order

Run these commands from the project root. The default source path is the
archive supplied for this project, but pass `--source-root` for another copy.

```powershell
python scripts/serenity/01_inventory.py --source-root "C:\Users\KALOS\Desktop\serenity历史推文收集"
python scripts/serenity/02_reconcile.py --source-root "C:\Users\KALOS\Desktop\serenity历史推文收集"
python scripts/serenity/03_normalize.py --source-root "C:\Users\KALOS\Desktop\serenity历史推文收集"
python scripts/serenity/05_freeze_temporal_holdout.py
python scripts/serenity/04_build_sample.py
python scripts/serenity/06_validate_pipeline.py
```

The first command hashes every source file and writes
`data/serenity/manifests/raw-manifest.json`. By default the source archive is
registered in place rather than duplicated. `--copy-raw-metadata` makes a
verified local mirror of the four metadata files; it does not copy media.

## Normalized record boundary

Each normalized record keeps `created_at` (the post's publication time) and
`captured_at` (the archive collection time) separately. It also keeps the raw
timestamp, `time_status`, `record_hash`, source file hash, source record ID,
reply/conversation relations, media metadata, and `access_level`.

The machine-readable boundary is
`schemas/normalized-post.schema.json`; fields recovered from the CSV index that
are absent from canonical public JSON live under an explicitly labelled `audit`
object and do not overwrite canonical fields.

Any object derived from at least one subscription record inherits
`access_level: subscription`. A summary, Claim, Thesis Event, or Method Card
does not become public merely because it was rewritten by a model.

## Pilot and temporal gate

`pilot-500.jsonl` is a deterministic stratified sample, normally 450 public and
50 subscription records. It covers time, post shape, replies/quotes, and
engagement variation; it must not be selected by likes, later prices, or final
returns. The temporal holdout is frozen before method-card extraction. Its
records are after the declared cutoff and must not overlap the pilot training
set.

The P1 gate requires zero critical issues, complete source traceability, no raw
hash changes, no partition cross-contamination, at least 99% resolved
timestamps with unresolved values explicit, and zero holdout leakage.

## Deliberately deferred

Do not add RAG/vector storage, full OCR, synthetic training data, return labels,
UI dashboards, or a graph database at this stage. After the pilot gate, add
entity extraction, thread reconstruction, thesis-event candidates, and method
cards as separate derived layers with source IDs, `max_source_created_at`,
`pipeline_version`, and propagated access level.

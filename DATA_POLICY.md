# Data policy

## Purpose

This project provides code and research methodology. It does not redistribute
the historical archive used to test the local pipeline.

Version 3 also defines a public-safe company research contract. Company facts,
quotes, market caps, shares, financial metrics, and valuation context are
field-level evidence objects; they are not a license to redistribute third-party
data or to present a stale quote as current.

## Data classes

| Class | Examples | Repository/runtime |
|---|---|---:|
| public | project-authored code, schemas, synthetic fixtures, public URLs | allowed when rights are clear |
| third-party-public | public posts, screenshots, images, filings | reference by locator; do not bulk redistribute |
| subscription | exclusive posts, images, and derivatives | local only |
| private | user files, notes, credentials, private research | local only |
| synthetic | invented fixtures with no copied third-party payload | allowed |
| outcome | later prices, returns, later earnings used for evaluation | isolated evaluator only |

Publicly viewable does not mean MIT-licensed. The repository license applies
only to material the project has the right to license.

## Local processing

The historical pipeline reads the supplied archive locally, records file and
record hashes, and writes normalized JSONL and derived objects under the local
data root. It does not upload the archive or call a remote model.

All derived objects inherit the strictest input access level. There is no
combined public/subscription file. Any object with unresolved provenance is
marked pending or unknown rather than silently promoted.

## Publication checklist

Before publishing a change, confirm:

- no raw archive or image dump is present;
- no subscription or private text is present;
- no reversible derivative exposes exclusive content;
- fixtures are synthetic or rights-cleared;
- links and trademarks are described in THIRD_PARTY_NOTICES.md;
- evaluation outputs contain no later-outcome labels in research context.
- company/market fields include source, as_of, quote/share/market-cap basis,
  and an explicit stale or unavailable status when applicable;
- no output contains a single composite conviction score, target-price promise,
  expected-return forecast, or automatic trade instruction.

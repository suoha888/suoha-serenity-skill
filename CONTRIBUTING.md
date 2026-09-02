# Contributing to suoha-serenity skill

Contributions should make evidence, time boundaries, source routing, failure
handling, or research communication more reliable. Keep the project
methodology-focused and independent.

## Never submit

- raw public or subscription archives;
- subscription text, screenshots, summaries, or reversible derivatives;
- private notes, credentials, API keys, wallet data, or personal information;
- unauthorized images, copied articles, or third-party datasets;
- code that accesses brokers, wallets, hidden network endpoints, or secrets;
- automatic buy/sell commands, return promises, or hindsight labels.

## Required for methodology changes

Every new rule or extraction behavior must include:

- a clear reason and known failure mode;
- a synthetic example or fixture;
- provenance and temporal implications;
- a regression test or evaluation case;
- documentation of any schema or output-contract change.

Social or KOL material is lead generation, not independent proof. Company
claims should route to primary filings, exchange documents, company IR,
transcripts, regulators, standards, project documents, patents, or credible
trade sources.

## Local checks

Run from the skill source directory:

~~~powershell
python scripts/validate_skill.py . --strict
Get-ChildItem scripts -Filter *.py -File | ForEach-Object { python -m py_compile $_.FullName }
~~~

Run the workspace data checks only against a local data root:

~~~powershell
python scripts/run_evals.py --root . --data-root ..\..\data\serenity
~~~

Do not paste local archive contents into an issue or pull request. Keep
subscription and private outputs outside the public repository.

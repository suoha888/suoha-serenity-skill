# Source-data notice

The published Skill contains this project's research procedure, code, schemas,
contracts, and synthetic evaluation fixtures. It does not bundle raw social
posts, screenshots, subscription text, or private archives.

The MIT license applies only to material the project is authorized to license.
It does not grant rights to external source material that users may analyze
locally. Users remain responsible for respecting the terms, copyright, privacy,
and access controls that apply to their own inputs. Subscription material and
all derived objects must remain in the matching private access boundary and
must not be published as examples, issues, pull requests, or runtime files.

## Social posts

`references/serenity-playbook.md` and examples cite X post IDs as traceable
leads and paraphrase in our own words. No post text is redistributed. X/Twitter
content stays subject to X's terms and its authors' rights.

## Market and filing data

`connectors/live_data.py` fetches quotes, FX rates and regulatory filings at
run time from public endpoints. Nothing it downloads is committed, except the
small dated snapshots under `examples/live/` that illustrate the output
format, plus the dated reference lists under `assets/` (`assets/universe/`
listing codes and names from the CNINFO, HKEXnews and SEC public lists;
`assets/etf-holdings/` from SEC N-PORT; `assets/ticker-truth.json`), which
record their source URLs and `as_of` dates. A-share and Hong Kong statement
figures come from a third-party aggregator (Eastmoney F10) at run time and are
labelled as such; confirm them in the filed report. Those values are
point-in-time, may be delayed, and remain subject to the terms of their
original providers. Company names and tickers are used only
to identify issuers; trademarks belong to their owners.


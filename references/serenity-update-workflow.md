# Serenity update workflow (v6.1)

How to keep the framework current as Serenity publishes new posts, and store
the work on GitHub **without publishing Serenity's text**.

## Two stores, never mixed

| Store | What lives there | Where |
|---|---|---|
| **Private archive** | Full post text (`posts.jsonl`), extracted stance events (`events.jsonl`), folded ledger, review queue | `$SERENITY_PRIVATE_DIR` (default `~/.serenity-private`) — a local folder or a **private** GitHub repo. Never inside this public repo unless the path is git-ignored. |
| **Public skill repo** | Code, schemas, doctrine rule IDs, atlas nodes, case cards **in the maintainer's own words**, post IDs, counts | This repository (GitHub, MIT) |

Why: the posts are Serenity's copyrighted content (and some may be
subscription-only). The skill is a framework distilled *from* them; it cites
post IDs (`x.com/i/status/<id>` can be resolved by anyone with access) and
never republishes the text. Subscription posts never enter public output at
all — not even as summaries.

## Routine update (every few weeks)

~~~bash
export SERENITY_PRIVATE_DIR=~/serenity-private        # or a clone of your private repo

# 1. merge new posts (JSONL with id/text/created_at, a JSON array, or an X archive tweets.js)
python scripts/serenity_update.py ingest new_posts.jsonl
#    -> de-duplicated by post ID, sorted by time; prints added/updated/total/last_post

# 2. re-extract stance events (private) and refresh the PUBLIC manifest (counts only)
python scripts/serenity_update.py refresh
#    -> $SERENITY_PRIVATE_DIR/events.jsonl, assets/serenity-archive-manifest.json

# 3. what changed for the framework? (private review queue)
python scripts/serenity_update.py gaps --since 2026-06-05
#    -> tickers not yet on the atlas, post IDs per doctrine family
#       (pricing_power, capacity_signal, new_chokepoint, dilution_financing, ...)

# 4. maintainer writes OWN-WORDS updates with post IDs:
#    references/serenity-doctrine.md   (new/changed PB-* rule, cite post IDs)
#    references/serenity-case-library.md (new case card)
#    assets/chokepoint-atlas.json      (new node/holder; basis "serenity_lead")
python scripts/atlas.py validate && python scripts/atlas.py render

# 5. leak guard + tests, then commit and push
python scripts/serenity_update.py check            # exit 1 if any public file shares a 12-word run with a post
python -m unittest discover -s tests -q
git add -A && git commit -m "framework: Serenity posts through <date>" && git push
~~~

`python scripts/serenity_update.py install-hook` installs a git pre-push hook
that runs `check` automatically.

The private store can itself be a git repo:

~~~bash
cd ~/serenity-private && git init && git add posts.jsonl events.jsonl && git commit -m "archive through <date>"
git remote add origin git@github.com:<you>/serenity-private.git   # create it as PRIVATE
git push -u origin main
~~~

## Using the update in research

- `python scripts/stance_ledger.py fold $SERENITY_PRIVATE_DIR/events.jsonl --as-of <cutoff> --out $SERENITY_PRIVATE_DIR/ledger.json`
- `python connectors/live_data.py pack <T> --ledger $SERENITY_PRIVATE_DIR/ledger.json --out-dir work/<t>`
- The lens memory block reports `archive_through`. Silence after that date
  is **unknown**, not a sell; silence before it is decay, not a reversal.

## Rules for own-words updates

1. Cite post IDs, not quotes. Paraphrase the *mechanism* (what to check), not
   the sentence. No more than a few consecutive words from any post.
2. A post is a lead about Serenity's public reasoning at a date — never a
   company fact. Company facts come from filings and primary sources.
3. Every new doctrine rule needs at least one post ID and one worked check
   (which number in which filing would confirm or break it).
4. Mark machine-extracted stance events `review_status: machine`; promote to
   `human_reviewed` only after reading the post.
5. Reports keep the framework notice: distilled from Serenity's public posts,
   for backtesting and research, not Serenity's own views, not investment advice.

<p align="center"><img src="assets/brand/hero.png" alt="suoha-serenity skill: Serenity research method as an AI Skill" width="100%"></p>

<p align="center">
  <a href="https://github.com/suoha888/suoha-serenity-skill/releases"><img src="https://img.shields.io/github/v/release/suoha888/suoha-serenity-skill?color=c2410c&label=release" alt="release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-f59e0b" alt="MIT"></a>
  <img src="https://img.shields.io/badge/API%20key-not%20needed-15803d" alt="No API key">
  <br><a href="README.md">中文</a> | English
</p>

**I turned Serenity's research method into an AI Skill**: give it any A-share, Hong Kong or US ticker and it tells you whether the company is a real chokepoint, whether it is worth digging into, how much valuation room is left, and what would show you got it wrong.

The method comes from Serenity ([@aleabitoreddit](https://x.com/aleabitoreddit) on X), an independent AI/semiconductor supply-chain researcher who shares research on X for free — follow Serenity for the original thinking.

## See it once: researching AMD

<p align="center"><img src="assets/brand/demo.gif" alt="Demo: ask the AI to research AMD; it pulls SEC filings, recomputes the numbers and builds a report" width="100%"></p>

<sub>The animation is assembled from the output of one real run on 2026-10-19 (commands, numbers and report are real). It is not a screen recording of any particular AI client. The UI text is Chinese.</sub>

## Start in 3 steps

**① Install with one command** (Git and Python 3.10+, **no API key**)

macOS / Linux:

```bash
git clone https://github.com/suoha888/suoha-serenity-skill.git && cd suoha-serenity-skill && ./install.sh
```

Windows (PowerShell):

```powershell
git clone https://github.com/suoha888/suoha-serenity-skill.git; cd suoha-serenity-skill; .\install.ps1
```

**② Open a Skills-enabled AI client** (Claude Code, Codex, …)

**③ Ask:** `Use suoha-serenity-skill to research AMD (US stock).`

No Git? Click **Code → Download ZIP** on this page, unzip, and run `./install.sh` (Windows: `.\install.ps1`) inside the folder.

## How to use it

| Ask your AI | You get |
|---|---|
| Use suoha-serenity-skill to research AMD | A full report: verdict, chokepoint map, three gates, red flags, evidence |
| Use suoha-serenity-skill to check 600519, conclusion first | A health check: what is normal, what to watch, any red flags |
| Use suoha-serenity-skill to research Tencent (00700)'s chokepoints | Same for Hong Kong: official filings + chokepoint judgment |
| Use suoha-serenity-skill to explain Serenity's chokepoint theory | Key rules + historical cases |

Or from the command line:

```bash
python suoha.py check AAPL       # health check in seconds
python suoha.py research AMD     # pull official data and build a research pack
python suoha.py resolve Tencent  # look up a ticker by name
```

## A real report (AMD, 2026-10-19)

**① Verdict first: tier, one-liner and a 30-second summary**

<img src="assets/brand/shot-1.png" alt="AMD report: verdict and summary" width="100%">

**② Chokepoint map and the three gates**

<img src="assets/brand/shot-2.png" alt="AMD report: chokepoint map and gates" width="100%">

**③ Red flags and evidence: every number traces to an official filing**

<img src="assets/brand/shot-3.png" alt="AMD report: red flags and evidence" width="100%">

Full report: [examples/amd-serenity-report.html](examples/amd-serenity-report.html) (download and open in a browser) · [Markdown](examples/amd-serenity-report.md)

## What it does

- **Research any stock** — pulls official data (SEC, CNINFO, HKEXnews, plus Japan, Korea and Taiwan exchanges), applies the chokepoint framework and gives the conclusion first, then the evidence.
- **Company health check** — routed by company type (bank, insurer, broker, property, general), each item with formula and threshold: ✅ normal, 👀 watch, 🚩 red flag.
- **Learn the theory** — distilled from 7,153 public posts: 14 laws, 19 chapters (including when a thesis is realized or broken) and 35+ historical cases with an outcome review, plus 22 cases where he publicly admitted being wrong or early (each mapped to the rule it teaches), each tagged with its source post ID (no post text).
- **Chokepoint atlas** — 10 supply chains and 46 nodes (now including AI compute rental and space); look up any ticker to see its position, upstream and peers.
- **Numbers you can re-check** — every number is recomputed by script; missing or stale evidence is blocked; 200+ automated tests.

More: [Guide (Chinese)](docs/GUIDE.md) · [FAQ](docs/FAQ.md) · [Changelog](docs/CHANGELOG.md) · [Report a problem](https://github.com/suoha888/suoha-serenity-skill/issues/new?template=field-test.yml)

## Author and notice

Designed and maintained by **梭哈.AI** ([@suoha_AI](https://x.com/suoha_AI) on X).

**Method source: Serenity** ([@aleabitoreddit](https://x.com/aleabitoreddit))
Known to fans as "白毛股神" (the white-haired stock wizard), Serenity is an independent AI/semiconductor supply-chain researcher focused on finding critical supply-chain bottlenecks and mapping hyperscaler supply chains, and shares research on X for free. Every rule and case here comes from Serenity's public posts; this repo only holds our own paraphrases and post IDs — look up the originals on Serenity's profile.

This is an unofficial project with no affiliation with or endorsement by Serenity. The method is distilled from Serenity's (@aleabitoreddit) public posts and cites post IDs only, never post text. Reports are generated by the framework and do not represent Serenity's own views. For research only; not investment advice. License: [MIT](LICENSE).

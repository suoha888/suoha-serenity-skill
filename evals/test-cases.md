# Manual Acceptance Scenarios

Each scenario lists a prompt and the observable behaviour a reviewer should
check. Automated gates live in `scripts/run_evals.py`; these cover judgement
and tone that scripts cannot score.

## S1 — Mainland theme scan

```text
用 suoha-serenity-skill 扫一遍 A 股 AI 半导体链，挑 5 家最值得继续深挖的公司。
```

Pass when the answer:

- orders supply-chain layers first and names the layer that saturates first;
- separates layers with different economics (accelerators, EDA/IP, memory and
  interconnect, front-end tools, materials, packaging/test, optics, PCB/CCL);
- demotes at least one crowded layer and explains why;
- cites mainland primary disclosures (periodic reports, inquiry-letter replies,
  investor Q&A platforms, tender results, project filings) with dates;
- gives each name a tier, the constrained input, the key proof and a falsifier;
- labels itself an initial pass when fewer than ~25 sources were read.

## S2 — Claim stress test

```text
这家公司说自己是 CPO 核心供应商，用 suoha-serenity-skill 验一验。
```

Pass when the answer pins the exact layer, tests qualification, design wins,
capacity, revenue share and substitutes, and names the evidence that would
overturn the claim.

## S3 — Momentum pressure

```text
一个大号刚点名这只小票，现在冲进去行不行？
```

Pass when the answer runs the red-flag checklist in
`references/risk-and-compliance.md`, refuses order wording, and still offers a
concrete research path.

## S4 — Porting a thesis across venues

```text
把 AI 光通信这条线搬到港股和日股，先说该去哪里找一手资料。
```

Pass when Hong Kong routes cover HKEXnews, placings, connected transactions and
mainland exposure, Japan routes cover TDnet, 決算短信, segment data and JPY
sensitivity, and the differences are explained plainly.

## S5 — Coaching

```text
用 Serenity 框架训练我，一次只问一个问题。
```

Pass when each turn asks exactly one question, walks the stage ladder in
`references/serenity-dialogue-protocol.md`, and grades the user's answers.

## S6 — Plain-language explainer

```text
用 suoha-serenity-skill 说说先进封装设备为什么可能值得看，口语一点，别写报告。
```

Pass when the view comes first, jargon is minimal, and the answer closes with
what to check next and what would weaken the view.

## S7 — Single-ticker lens

```text
用 suoha-serenity-skill 研究 $MU，先给结论，再给证据。
```

Pass when a live pack is pulled, every number in the report is produced by
`serenity_lens.py compute`, `validate` and `verify_report.py` pass, and the
footer carries the framework notice.

# suoha-serenity skill — Starter Prompts

Copy a prompt, replace the brackets, and send it. Every prompt below produces
either a lens report (🟢/🟡/🔴 tier, recomputed numbers, falsifiers) or a
dialogue, depending on the section.

## 1. One ticker, full lens (default)

```text
用 suoha-serenity-skill 研究 $[TICKER]，先给结论，再给证据。
```

```text
Run suoha-serenity-skill on $[TICKER]: live data pack, chokepoint map,
recomputed valuation, point-in-time Serenity stance if available, tier and
falsifiers, then the HTML report.
```

## 2. Theme → chokepoint → names

```text
用 suoha-serenity-skill 扫一遍 [主题，如 HBM4 / CPO / 先进封装]：
先画供应链分层，指出最先饱和的那一层，再列出握住这一层的公司，
每家写清楚被卡的是什么、证据是哪份文件、什么情况会让它降级。
```

## 3. Venue-specific scans

```text
用 suoha-serenity-skill 看 A 股 [主题]。一手来源优先：定期报告、临时公告、
问询函回复、互动易问答、中标公示、环评与项目备案；重点核对应收/存货/现金流和融资摊薄。
```

```text
用 suoha-serenity-skill 看港股 [主题]，先过滤流通性、配售与可转债、关联交易，
再谈卡点和估值。
```

```text
Use suoha-serenity-skill on [Taiwan / Japan / Korea] names in [theme]. Use the
venue's own disclosure system (MOPS monthly revenue, TDnet, DART) and state the
share class and currency of every number.
```

## 4. Stress-test a claim

```text
[公司] 自称是 [产品] 的核心供应商。用 suoha-serenity-skill 拆穿或证实它：
客户导入、认证进度、产能、收入占比、替代供应商，各给一条可核验证据。
```

## 5. Head-to-head

```text
Compare [A], [B], [C] with suoha-serenity-skill. Keep bottleneck strength,
evidence quality, value capture, valuation, timing and risk as separate
readings — no combined score — and say which one holds the scarcer layer.
```

## 6. "What did Serenity say, and when?"

```text
用 suoha-serenity-skill 的立场账本查 $[TICKER]：截至 [日期] Serenity 的
立场、最近一次动作和帖子 ID，以及之后的 D1/D7/D30 表现。
```

## 7. Sparring and coaching

```text
用 suoha-serenity-skill 陪我推 [主题/公司]。别写报告，每轮一句判断 + 一个最关键的问题。
```

```text
Coach me through the Serenity framework on [theme], one stage per turn, and
grade my answer at each stage.
```

## 8. Keep the private archive fresh

```text
用 suoha-serenity-skill 把我新导出的帖子并进本地档案，然后告诉我有哪些标的的立场变了。
```

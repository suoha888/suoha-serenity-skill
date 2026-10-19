# Serenity 报告模板（v5）

> 报告不手写：先产出 SerenityLens JSON，`compute` → `validate` → `render_report.py` → `verify_report.py`。本模板说明每节写什么、对应哪个字段，供 agent 组织内容。

| # | 区块（section id） | 写什么 | 来源字段 |
|---|---|---|---|
| 0 | 结论 `verdict` | 分级（green/amber/red）+ 一句话：卡在哪里、谁绕不开、为什么市场还没算进去 | `research_tier`、`one_liner` |
| 0 | 30 秒看懂 `thirty-sec` | ≤700 字：需求锚 → 卡点 → 估值 → 最大风险 → 分级理由 | `thirty_second_summary`、`tier_reason`、`rerate_triggers` |
| 1 | 资本开支确定性 `capex` | 谁付钱、多少、何时，附证据 | `capex_certainty` |
| 2 | 卡点地图 `chain` | ≥3 层，含上游；标出研究对象和未上市节点 | `chain_map` |
| 2 | 卡点中的卡点 `chokepoint` | 一个节点 + 确定程度 + 原型命中 | `chokepoint_of_chokepoint`、`archetype_hits` |
| 3 | 三道闸门 `gates` | 真瓶颈 / 前机构 / 便宜且去风险 | `gates` |
| 4 | 估值不对称 `valuation` | 现价×股本；bear/base/bull 假设与隐含值（脚本计算）；TAM 与可比 | `valuation` |
| 5 | 先行信号 `signals` | 确认/否定条件 + 下次检查日期；OSINT 线索 | `leading_signals`、`osint_leads` |
| 6 | Serenity 记忆 `memory` | 时点一致的提及时间线（帖子 ID + 自写摘要） | `serenity_memory` |
| 7 | 按 Serenity 框架会怎么看 `serenity-view` | 会不会关注、为什么、引用哪些 PB 规则 | `serenity_view` |
| 8 | 红旗 `red-flags` | veto/downgrade/watch 与是否触发 | `red_flags` |
| 9 | 红队 `red-team` | 4 问 + 更优替代 + 最大杀点 | `red_team` |
| 10 | 证伪 `falsification` | ≥1 条机器可检（指标/运算符/阈值/日期） | `falsification` |
| — | 证据 `evidence` | 每条证据的标题、定位、发布时间 | `evidence` |
| — | 免责 `disclaimer` | 必须含“非投资建议” | `disclaimer` |

完整示例：`examples/amd-serenity-lens.json` → `examples/amd-serenity-report.md` / `.html`。

# Micron Technology, Inc.（MU）· Serenity 框架卡点透镜

<!-- section:verdict -->
> **🟡 观察/等触发** · MU 是 HBM/先进 DRAM 这个“现在进行时”卡点的三家持有者之一，10-K 首次披露约 1,340 亿美元剩余履约义务和多年 take-or-pay；但市值已近 1 万亿美元、毛利率 86.8% 处在历史极值，框架下是 amber：瓶颈真实，信息差已基本消失。
> 截止 2026-10-18 · 类型 `upstream_material` · 市值 994.34B USD（2026-10-16）

<!-- section:thirty-sec -->
## 30 秒看懂
截至 2026-10-16 收盘 878.84 美元，计算市值约 9,943 亿美元，较 52 周高点回撤 30%，一年涨 334%。FY26 Q4（期末 2026-09-03）收入 542 亿美元，同比 +379%、环比 +31%，毛利率 86.8%（同比 +42pp），营业利润率 80.7%，净现金约 406 亿美元。10-K 写明战略客户协议为 take-or-pay、多年期、约定可强制执行的数量，价格多数有上下限，剩余履约义务约 1,340 亿美元（其中 130 亿已为合同负债），并收取客户押金和信用证。这是 ARC-SUPER-SUPPLIER 的教科书信号，周期折价理应收窄；但按 TTM 7.5 倍、按单季年化约 4.6 倍 P/S，市场已在为“峰值后回落”定价。第一个证伪数字：下一份 10-Q 的季度毛利率低于 70%。

**分级理由：** 真瓶颈闸门通过、无稀释、合同可见度高；但前机构闸门失败、利润率在历史极值，无法给 green。

**重估触发条件：** 10-Q 中 RPO 和合同负债继续上升；2027 年合同价格带下限公开或被分析师确认；HBM4 在主要加速器平台的份额数据

<!-- section:live-data -->
## 0. 实时数据
- 快照：`examples/live/mu-pack-2026-10-18/snapshots/MU.json` · 取数 2026-10-18T04:43:33Z · 来源 data.sec.gov, news.google.com, query1.finance.yahoo.com, www.sec.gov

<!-- section:doctrine -->
## 框架定位（Doctrine）
| 维度 | 判断 | 说明 |
|---|---|---|
| 框架适配 | 卡点 · 部分 | MU 持有 HBM/先进 DRAM 卡点（三家寡头之一），合同证据支持 PB-FIT-01；但规模与覆盖度让它接近价格锚（PB-FIT-02），框架适配为 partial。（PB-FIT-01, PB-FIT-02） |
| 瓶颈状态 | 正在卡 · material | 实时财务（+379% 收入、86.8% 毛利率）与 10-K take-or-pay 条款共同确认图谱的 now 状态。 [E-LIVE-FIN] [E-LIVE-DOC-01] |
| 阶段 | 量产爬坡 | 收入环比 +30.8%，10-Q 称新签战略协议在期后继续执行，仍处放量阶段。 [E-LIVE-FIN] [E-LIVE-DOC-02] |
| 纯度 | 未知（unknown） | 10-K 按业务单元分部，未单列 HBM 收入；10-Q 有按技术（DRAM/NAND）拆分，可补读后再估纯度。 |
| 风险档 | 重估 | PB-STYLE-03 |

<!-- section:variant -->
## 差异化观点
- **市场共识**：价格回撤 30%、媒体讨论“为何继续下跌”，单季年化约 4.6 倍 P/S：市场按传统存储周期为峰值后回落定价。 [E-LIVE-QUOTE] [E-LIVE-NEWS-03] [E-LIVE-NEWS-05]
- **我们的看法**：约 1,340 亿美元 RPO 相当于 1 倍 TTM 收入已被 take-or-pay 锁定；即便价格回落到带下沿，FY27 收入不低于 1,500 亿美元，周期折价应小于市场隐含的水平。
- **为什么市场可能错**：PB-VP-07, PB-VP-04
- **市场何时会看到**：下一份 10-Q（约 2026 年 12 月下旬）披露 RPO 与合同负债变化时。
- **第一个证伪数字**：`MU quarterly gross margin pct < 70`（2027-01-15 前检查）
- **档案之后的变化**：本示例演示未接入私有 ledger 时的处理（Serenity 记忆为 unavailable，不推测其立场）。研究日之前的一手变化：MU 10-K（2026-10-09）首次给出约 1,340 亿美元 RPO 与 take-or-pay 条款，是研究时最重要的新事实。

<!-- section:capex -->
## 1. 资本开支确定性
- 需求来源：`hyperscaler_commercial`
- 需求方是 AI 数据中心客户：10-K 称战略客户协议为多年期 take-or-pay、数量可强制执行，RPO 约 1,340 亿美元并伴随押金/信用证，需求确定性来自合同而不只是指引。 [E-LIVE-DOC-01] [E-LIVE-DOC-02]

<!-- section:chain -->
## 2. 卡点地图：AI 存储（HBM / NAND / 遗留 DRAM）
- **下游对照**：NVIDIA `NVDA`：AI 加速器，HBM 主要买方（未在 10-K 中点名）；AMD `AMD`：AI 加速器，HBM 买方
- **上游材料/代工**：**Micron Technology, Inc.** `MU`：HBM / 先进 DRAM 三家持有者之一（与 SK hynix、三星同层），向 AI 加速器供应 HBM；000660.KS `000660.KS`：同层（图谱）；005930.KS `005930.KS`：同层（图谱）
- **跨主题根节点**：存储工序设备与 IP `VECO`：上游节点（图谱状态 filling）；HBM 压缩成型 `6315.T`：上游节点（图谱状态 monopoly_not_bottleneck）

<!-- section:chokepoint -->
**卡点中的卡点**（hypothesis）：HBM 键合、成型与测试设备（VECO / 6315.T / ONTO 所在节点） — HBM 扩产的上游约束更可能在 TSV/混合键合、压缩成型与测试设备，而非晶圆本身；地图把这些列为 filling / monopoly_not_bottleneck，尚未用一手数据确认。 

| 卡点原型 | 命中 | 理由 |
|---|---|---|
| ARC-SUPER-SUPPLIER | yes | 10-K：多年 take-or-pay、可强制执行数量、价格上下限、客户押金与信用证、RPO 约 1,340 亿美元——符合“超级乙方”的 LTA + 预付款 + 价格下限三件套。  |

<!-- section:gates -->
## 3. 三道闸门
- 🔒 真瓶颈：✅ 通过 — 收入同比 +379%、毛利率 86.8%，且客户愿意签 take-or-pay 并预付押金锁定数量，属于产能受限而非需求受限（PB-CAP-04、PB-SIG-07）。 [E-LIVE-FIN] [E-LIVE-DOC-01]
- 👁️ 前机构：❌ 不过 — 计算市值约 9,943 亿美元，2026 年有多份大型被动机构 13G/13G/A，媒体覆盖密集；信息差窗口已关闭。 [E-LIVE-QUOTE] [E-LIVE-SHARES] [E-LIVE-SEC-07] [E-LIVE-SEC-08]
- 💰 便宜且去风险：◐ 部分 — TTM P/S 7.5 倍、单季年化约 4.6 倍，净现金约 406 亿美元、无稀释（股本一年 +0.8%）；但利润率处在历史极值，合同价格带下限未披露。 [E-LIVE-QUOTE] [E-LIVE-SHARES] [E-LIVE-FIN]

<!-- section:valuation -->
## 4. 估值不对称（尺子：`chokepoint_comparable`）
现价 878.84 USD × 股本 1,131,423,212 = 市值 994.34B USD [E-LIVE-QUOTE] [E-LIVE-SHARES]

| 情景（假设） | 期限 | 收入 | 倍数 | 隐含市值 | 隐含每股 | 相对现价 | 叙事 |
|---|---|---|---|---|---|---|---|
| bear | 2y | 120.00B USD | 4.0x ps | 480.00B USD | 424.24 | -51.7% | 价格回落到合同价格带下沿、HBM 份额被 SK hynix 挤压，两年后收入约 1,200 亿美元、按周期股 4 倍 P/S 定价。 |
| base | 2y | 200.00B USD | 5.0x ps | 1.00T USD | 883.84 | +0.6% | take-or-pay 锁定的数量兑现、价格温和回落，两年后收入约 2,000 亿美元（低于当前单季年化 2,170 亿），按 5 倍 P/S。 |
| bull | 2y | 260.00B USD | 5.5x ps | 1.43T USD | 1263.89 | +43.8% | HBM4 放量叠加长期协议把周期折价移除，收入约 2,600 亿美元，按 5.5 倍 P/S（仍低于当前 TTM 倍数）。 |

> 情景是“要成立需要什么”的假设推演，不是目标价、收益预测或交易建议。

<!-- section:signals -->
## 5. 先行信号（不等财报）
- **DRAM / HBM 合同价（季度谈判结果）**（spot_price）— 确认：2027 年合同价持平或上调；否定：合同价环比下跌超过 15%
- **SK hynix 与三星季度存储毛利率**（peer_earnings）— 确认：同行毛利率维持 70% 以上；否定：同行率先出现毛利率环比下滑 5pp 以上
- **MU 10-Q 剩余履约义务与合同负债**（filing）— 确认：RPO 高于 1,340 亿美元；否定：RPO 下降或合同被重新谈判

<!-- section:memory -->
## 6. Serenity 公开言论记录（时点）
状态：`unavailable`

No Serenity stance ledger supplied (--ledger). Silence in this pack is not a view.

<!-- section:serenity-view -->
## 7. 按 Serenity 框架会怎么看
框架是否关注：**maybe** — 按 Serenity 框架：HBM/DRAM 是“现在进行时”的材料瓶颈，MU 的 take-or-pay 符合超级乙方；但框架偏好前机构、低覆盖的上游，万亿市值的 MU 更像链条锚点和指标，alpha 应往上游设备/材料找。（规则：PB-FIT-01, PB-LAW-08, PB-SIG-07, PB-VP-07）

<!-- section:next-hop -->
## 下一跳候选（研究线索，非推荐）
| 代码 | 名称 | 关系 | 节点 | 理由 | 依据 | 先验证 |
|---|---|---|---|---|---|---|
| `VECO` | Veeco | 上游 | 存储工序设备与 IP | 10-K 自述部分材料/设备单一来源；Veeco 在 HBM 相关沉积/键合工序是地图上的 filling 节点，需用其 10-Q 确认订单。 | Serenity 公开线索 | python connectors/live_data.py snapshot VECO |
| `RMBS` | Rambus | 上游 | 存储工序设备与 IP | HBM/DDR5 接口 IP 与芯片按出货量收费，存储放量直接传导，需核实 HBM4 相关收入占比。 | Serenity 公开线索 | python connectors/live_data.py snapshot RMBS |
| `ONTO` | Onto Innovation | 上游 | 存储工序设备与 IP | HBM 堆叠带来更多量测检测步骤，需从其 10-Q 读先进封装/存储客户占比。 | Serenity 公开线索 | python connectors/live_data.py snapshot ONTO |

<!-- section:red-flags -->
## 8. 红旗筛查
- [watch] beneficial_owner_filings：**yes** — 2026 年有 13G（4-30）与 13G/A（5-14）；对万亿市值公司这是被动持仓披露，不是“机构发现”信号。 [E-LIVE-SEC-07] [E-LIVE-SEC-08]
- [watch] insider_form4_activity：**unknown** — 雷达显示有 Form 4 活动，本示例未逐份分类交易代码（P/S/A）；用于交易前必须核实是否存在公开市场买入。 
- [watch] going_concern_exhibit_only：**no** — 全文检索 4 条 going concern 命中全部在附件（主文档 0/4），属于合同/融资附件文本，不是公司自身持续经营警告。 [E-LIVE-DOC-01]
- [watch] supply_concentration：**yes** — 10-K 称部分材料、零部件和服务只有少数或单一来源——MU 依赖上游单一来源，而不是自己是单一来源，这指向下一跳。 [E-LIVE-DOC-01]
- [watch] capacity_language：**yes** — take-or-pay 约定“可强制执行的数量”，说明客户在抢产能；需在下一份 10-Q 跟踪 RPO 与合同负债是否继续增长。 [E-LIVE-DOC-01] [E-LIVE-DOC-02]

<!-- section:red-team -->
## 9. 红队：杀死这个判断的最短路径
1. 为什么可能不是真瓶颈？三家同时扩产，2027–2028 年新产能释放后 DRAM 可能重回过剩，现在的“卡点”只是周期顶点。
2. 为什么可能不变现？价格带上限意味着涨价被合同封顶；高毛利可能被资本开支吞噬，自由现金流不及利润。
3. 市场是否已定价？近 1 万亿美元市值、一年涨 334%，大部分超级周期已被定价；回撤 30% 说明市场在交易“峰值”。
4. 更优替代：`000660.KS` — SK hynix HBM 份额领先，按即期汇率 TTM P/S 约 4.8 倍，低于 MU 的 7.5 倍；但需处理韩股流动性与汇率。

**最大杀点：** 下一份 10-Q 披露 RPO 下降或客户重新谈判价格带，说明 take-or-pay 并没有锁住价格。

<!-- section:falsification -->
## 10. 证伪条件
- 下一份 10-Q 季度毛利率低于 70% `机器可检: MU quarterly gross margin pct < 70`（检查：2027-01-15）（PB-EXIT-03）
- 下一份 10-Q 披露的剩余履约义务低于 1,000 亿美元 `机器可检: MU remaining performance obligations USD < 100000000000.0`（检查：2027-01-15）（PB-EXIT-10）

<!-- section:evidence -->
## 证据
- [E-LIVE-QUOTE] MU quote 878.84 USD (NasdaqGS) — https://query1.finance.yahoo.com/v8/finance/chart/MU?range=1y&interval=1d（2026-10-16，market_data）
- [E-LIVE-SHARES] Shares outstanding 1,131,423,212 as of 2026-10-02 (sec_companyfacts) — https://data.sec.gov/api/xbrl/companyfacts/CIK0000723125.json（2026-10-02，filing）
- [E-LIVE-FIN] Latest quarterly revenue 54,229,000,000 USD (period end 2026-09-03); TTM 133188000000; YoY 379.27%; GM 86.76% — https://data.sec.gov/api/xbrl/companyfacts/CIK0000723125.json（2026-09-03，filing）
- [E-LIVE-SEC-01] 10-K filed 2026-10-09 — https://www.sec.gov/Archives/edgar/data/723125/000072312526000023/mu-20260903.htm（2026-10-09，filing）
- [E-LIVE-SEC-02] 10-Q filed 2026-06-25 — https://www.sec.gov/Archives/edgar/data/723125/000072312526000015/mu-20260528.htm（2026-06-25，filing）
- [E-LIVE-SEC-03] 8-K filed 2026-09-30 (results of operations, exhibits) — https://www.sec.gov/Archives/edgar/data/723125/000072312526000018/mu-20260930.htm（2026-09-30，filing）
- [E-LIVE-SEC-04] 8-K filed 2026-08-26 (officer/director change, exhibits) — https://www.sec.gov/Archives/edgar/data/723125/000110465926101067/tm2624017d1_8k.htm（2026-08-26，filing）
- [E-LIVE-SEC-05] 8-K filed 2026-06-24 (results of operations, exhibits) — https://www.sec.gov/Archives/edgar/data/723125/000072312526000013/mu-20260624.htm（2026-06-24，filing）
- [E-LIVE-SEC-06] 8-K filed 2026-06-09 (officer/director change, exhibits) — https://www.sec.gov/Archives/edgar/data/723125/000110465926071845/tm2617112d1_8k.htm（2026-06-09，filing）
- [E-LIVE-SEC-07] SCHEDULE 13G/A filed 2026-05-14 — https://www.sec.gov/Archives/edgar/data/723125/000142284926000099/xslSCHEDULE_13G_X02/primary_doc.xml（2026-05-14，filing）
- [E-LIVE-SEC-08] SCHEDULE 13G filed 2026-04-30 — https://www.sec.gov/Archives/edgar/data/723125/000210011926000795/xslSCHEDULE_13G_X02/primary_doc.xml（2026-04-30，filing）
- [E-LIVE-NEWS-01] [lead] Micron Stock’s Drop Triggers ‘Buy the Dip’ Calls. No One’s Listening. - Barron's — https://news.google.com/rss/articles/CBMieEFVX3lxTE8xSUt3YVV0N3FhRFU4cTItNHB3UTJyMHUwY1NCbERhVG90SmVFcHowWnFLNUJRY2wzLXpaSHZyRzNKejBva3B0aEdRVnpqQ0V0NXIyUWpxWHhHRU94WWFkdDdOT1BreHhvU2RFV3Q0b0RYZzczT1JSTA?oc=5（2026-10-16，news）
- [E-LIVE-NEWS-02] [lead] Micron Technology (MU) Pledges $50 Million For US Memory Research - Yahoo Finance — https://news.google.com/rss/articles/CBMilwFBVV95cUxOUTRveEp4eXNGNEt1RWloSEVnUlQzX19zRHEtRkdQREotZlJFVFZWeGdmMldMbG55cndOdGtlWEVqNk90MHE5OTc4cmdPZW5JYWg4QTFRWTlITTZZMmF6ZDUybVJ2M1FfYTZuWVVNQ1dpV2lRT2tzYlhpYzVPUEltcEJvVnAwdENLTlk4QlRXeVZySW1YWHhJ?oc=5（2026-10-16，news）
- [E-LIVE-NEWS-03] [lead] Here is What to Know Beyond Why Micron Technology, Inc. (MU) is a Trending Stock - Yahoo Finance — https://news.google.com/rss/articles/CBMinwFBVV95cUxQOFM1NW9lT1EwakNaTm5XNGplZjd2em1JVVJTdFFiczllMEoxMDNidnNXWUd1a1FfNVdncU5QUzdadWRHaGxnY0w3UUZwRzlYT01jRHRWY3lYVkZtbnBYdGZPbFNSVFBSeEFMb2dYXy10V1dqc0FHTFRvdHRPbDlzdmdROHo2Mmw3UE8tVUl0ZW5tUFE0TThYZUdyemdNSHM?oc=5（2026-10-16，news）
- [E-LIVE-NEWS-04] [lead] Micron Is Down 23% From Its High. History Suggests This Is What Happens Next. - The Motley Fool — https://news.google.com/rss/articles/CBMimAFBVV95cUxOTkRqNGdUd3dpWFZOOTNkRkVzanIxZU8zTEsxcmRGVEhoTUFBWTc3X2tvaUkwYWtTd05TN2ttUk5fN3FjTi1tM2toU1laQ1J6QVpObk1PYU84T3ZRSklDcG45TjZFaFN1c2RnVExhNHNYVmg1V0JscVJfdk9BRkEtODQ0cERfb0FUVXkwQTVqZEFjX0FveDNfbQ?oc=5（2026-10-16，news）
- [E-LIVE-NEWS-05] [lead] I Just Bought Micron Stock. Here's Why - Yahoo Finance — https://news.google.com/rss/articles/CBMimwFBVV95cUxQdDZvT3I1OXpUN3hwS2xocHdoem9qeUdPeWlINnIwV2JtTVY0TzFiZVlGMlh6SWtKZnRlZTBmd0VDWFM4Q3oxcFo4NnBaX2pWWjBCMkRFZmlmNW03UzJtNnN2Yl9JMUktRHZqa3hrNFNGS2hkc2dvU2FQS2dBSlhLUEdhSmQ1eHZHVEFnVERtdTFId1dvMzVmY3hDWQ?oc=5（2026-10-15，news）
- [E-LIVE-NEWS-06] [lead] Why Is Micron Stock Still Dropping? - The Motley Fool — https://news.google.com/rss/articles/CBMigwFBVV95cUxPVTBMeGcxaEdOLURGdzdyaHBJalRfckoxOE5lUXoyMGVSaFNmMVRkTFU4a2V1ZkdpZ1FRZ1RCdk5CSG0wSTBxNms4d21kOXNjWko2NEhjYVZieEo0c25KU2d6bjk5WmZhYWdnWk1NU1VOeHlCSUZlaEpnT2xqYlVPdnA3UQ?oc=5（2026-10-15，news）
- [E-LIVE-DOC-01] 10-K filed 2026-10-09 (primary document) — https://www.sec.gov/Archives/edgar/data/723125/000072312526000023/mu-20260903.htm（2026-10-09，filing）
- [E-LIVE-DOC-02] 10-Q filed 2026-06-25 (primary document) — https://www.sec.gov/Archives/edgar/data/723125/000072312526000015/mu-20260528.htm（2026-06-25，filing）

审计层：research_output `research:mu-2026-10-18`，bundle 校验 未运行

<!-- section:disclaimer -->
---
⚠️ 框架声明：本 skill 根据 Serenity 公开发布的内容提炼研究框架，用于回测与研究分析；报告由框架生成，不代表 Serenity 本人观点，亦非投资建议。

<!-- serenity-lens lens_id=lens:mu-2026-10-18 sha256=b65f2574068985f4aba2cce8f638e8585220a71626ae2a429123bf9a52c5067a -->

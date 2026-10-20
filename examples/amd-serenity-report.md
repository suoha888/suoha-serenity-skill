# Advanced Micro Devices, Inc.（AMD）· Serenity 框架卡点透镜

<!-- section:verdict -->
> **🟡 观察/等触发** · AMD 是 AI 加速器唯一成规模的 GPU 第二来源，Data Center 收入同比 +107%，但它本身不是卡点：先进制程全靠 TSMC，市值约 8956 亿美元、P/E 139 倍，三道闸门只过半道，列为 amber（观察）。
> 截止 2026-10-19 · 类型 `fabless_designer` · 市值 895.58B USD（2026-10-19）

<!-- section:thirty-sec -->
## 30 秒看懂
截至 2026-10-19，AMD 股价 548.6 美元，市值约 8956 亿美元，一年涨约 117%。Q2（截至 2026-06-27）收入 115.4 亿美元、同比 +50%，其中 Data Center 67.2 亿美元、同比 +107%，占收入约 58%，由 EPYC 和 MI350 驱动；毛利率 53.8%。它在 AI 链条里是中游系统/芯片设计方：≤7nm 晶圆全部依赖 TSMC，部分材料设备只有有限或唯一供应商，自己是被卡的一方。OpenAI 与 Meta 各持有最多 1.6 亿股、行权价 0.01 美元的认股权证（合计约占现有股本 19.6%），按 GPU 采购里程碑归属，既锁住大客户也带来稀释。P/E(TTM) 139 倍、P/S 21.7 倍，便宜这一关不过。体检 0 红旗 1 关注（商誉/权益 37.9%）。结论：好公司、热门票，但不是 Serenity 式的早期卡点，观察 Q3 财报与 Helios 出货。

**分级理由：** 真实需求强（DC 同比 +107%），但三道闸门：真卡点 partial、机构前 fail、便宜 fail；另有约 19.6% 认股权证稀释，故为 amber：值得跟踪，不是早期卡点机会。

**重估触发条件：** Q3 FY2026 财报（约 2026-11 初）Data Center 收入与毛利率；Helios 机架平台首批出货；OpenAI/Meta 认股权证首批归属；World Labs 收购交割

<!-- section:live-data -->
## 0. 实时数据
- 快照：`examples/live/amd-snapshot-2026-10-19.json` · 取数 2026-10-19T13:31:14Z · 来源 data.sec.gov, news.google.com, query1.finance.yahoo.com, www.sec.gov

<!-- section:doctrine -->
## 框架定位（Doctrine）
| 维度 | 判断 | 说明 |
|---|---|---|
| 框架适配 | 集成商/可替代件 · 部分 | AMD 是 AI 加速器的第二来源（可多源的芯片/系统），吃到资本开支但不掌握最窄环节；按普通成长股估值，并顺着它的供应约束找上游卡点。（PB-FIT-04, PB-HUNT-08） |
| 瓶颈状态 | 不是瓶颈 · demand | AMD 的出货受上游 TSMC 产能与内存/基板约束；它是需求方的第二来源，而不是物料卡点本身。 [E-LIVE-DOC-02] [E-LIVE-DOC-01] |
| 阶段 | 量产爬坡 | Data Center Q2 收入 67.2 亿美元、同比 +107%，MI350 放量、Helios 预计 2H FY2026 出货，处于放量阶段。 [E-LIVE-SEC-01] [E-LIVE-DOC-02] |
| 纯度 | 约 58%（reported_segment） | Q2 Data Center 收入 67.18 亿 / 总收入 115.36 亿 ≈ 58%（分部披露，含 EPYC CPU，不全是 AI GPU）。 |
| 风险档 | 锚 | PB-STYLE-03 |

<!-- section:variant -->
## 差异化观点
- **市场共识**：市场把 AMD 看作 AI 加速器的第二赢家，一年涨约 117%，新闻集中讨论其 AI 基础设施份额与 Q3 预期。 [E-LIVE-NEWS-04] [E-LIVE-NEWS-05] [E-LIVE-NEWS-06]
- **我们的看法**：需求是真的（DC 同比 +107%），但 139 倍 P/E 和最多 19.6% 的认股权证稀释让风险回报不对称；按框架更值得研究的是它上游的 TSMC/HBM 约束，而不是 AMD 本身。
- **为什么市场可能错**：PB-VP-01
- **市场何时会看到**：Q3 FY2026 财报（约 2026-11 初）与 Helios 出货时点
- **第一个证伪数字**：`amd_datacenter_revenue_q3_fy2026_usd > 8500000000.0`（2026-11-10 前检查）
- **档案之后的变化**：档案截止后：DC 收入翻倍、OpenAI/Meta 认股权证落地、8 月发行优先票据、9 月全股票收购 World Labs（约 82 亿美元）。

<!-- section:capex -->
## 1. 资本开支确定性
- 需求来源：`hyperscaler_commercial`
- 需求来自超大规模云厂商与 AI 实验室的数据中心资本开支：10-Q 显示 Data Center 上半年收入 124.9 亿美元、同比 +81%，OpenAI、Meta 认股权证按 GPU 采购里程碑归属，说明有大额采购承诺，但归属尚未发生、确定性中等。 [E-LIVE-SEC-01] [E-LIVE-DOC-02]

<!-- section:chain -->
## 2. 卡点地图：AI 数据中心加速器（Instinct GPU / EPYC / Helios 机架）
- **下游对照**：OpenAI（private）：GPU 客户，持有最多 1.6 亿股认股权证；Meta Platforms `META`：GPU 客户，持有最多 1.6 亿股认股权证
- **中游系统**：**Advanced Micro Devices, Inc.** `AMD`：Fabless 芯片设计：Instinct GPU、EPYC CPU、Helios 机架平台（预计 2H FY2026 出货）
- **中游器件**：HBM / 内存与基板供应商（unknown）：10-K 警示内存、基板短缺风险；AMD 上半年为供应协议预付约 10 亿美元
- **上游设备**：TSMC `TSM`：≤7nm 晶圆唯一代工来源（含先进封装）

<!-- section:chokepoint -->
**卡点中的卡点**（inferred）：TSMC 先进制程与封装 + HBM 内存 — AMD 的出货上限由 TSMC 先进制程/封装产能和 HBM 内存决定；10-Q 写明 ≤7nm 产品全部由 TSMC 制造，并为锁定供应预付约 10 亿美元，真正的卡点在它的上游。 [E-LIVE-DOC-02] [E-LIVE-DOC-01]

| 卡点原型 | 命中 | 理由 |
|---|---|---|
| ARC-SOLE-SOURCE | no | AMD 不是唯一供应方，反而依赖 TSMC 这一唯一代工来源。 [E-LIVE-DOC-02] |
| ARC-CAPACITY-LOCK | partial | 上半年为供应协议预付约 10 亿美元锁定产能，对小竞争者是壁垒，但锁的是别人的卡点。 [E-LIVE-DOC-02] |
| ARC-TRANSITION-GATE | partial | Helios 机架平台是从卖芯片到卖整机柜的跃迁，计划 2H FY2026 出货，尚未兑现。 [E-LIVE-DOC-02] |
| ARC-CAPEX-PICKS-SHOVELS | yes | Data Center 收入同比 +107%，直接吃到云厂商 AI 资本开支。 [E-LIVE-SEC-01] [E-LIVE-DOC-02] |

<!-- section:gates -->
## 3. 三道闸门
- 🔒 真瓶颈：◐ 部分 — 它是唯一成规模的 GPU 第二来源，客户需要它来分散对单一供应商的依赖；但自身受 TSMC、内存、基板约束，不是链条里最窄的那一环。 [E-LIVE-DOC-02] [E-LIVE-DOC-01]
- 👁️ 前机构：❌ 不过 — 市值约 8956 亿美元、一年涨约 117%，13G 显示大机构持股，已被市场充分发现。 [E-LIVE-QUOTE] [E-LIVE-SEC-10]
- 💰 便宜且去风险：❌ 不过 — P/E(TTM) 约 139 倍、P/S 约 21.7 倍、P/FCF 约 107 倍，价格已计入高增长，并不便宜。 [E-LIVE-QUOTE] [E-LIVE-FIN]

<!-- section:valuation -->
## 4. 估值不对称（尺子：`hypergrowth_forward`）
现价 548.6 USD × 股本 1,632,475,042 = 市值 895.58B USD [E-LIVE-QUOTE] [E-LIVE-SHARES]

| 情景（假设） | 期限 | 收入 | 倍数 | 隐含市值 | 隐含每股 | 相对现价 | 叙事 |
|---|---|---|---|---|---|---|---|
| bear | 2y | 60.00B USD | 30x pe @ 20% 净利率 | 360.00B USD | 210.02 | -61.7% | AI 加速器放量低于预期、毛利率被内存成本挤压：2 年后收入 600 亿美元、净利率 20%、30 倍 P/E，认股权证部分归属稀释 5%。 |
| base | 2y | 80.00B USD | 35x pe @ 25% 净利率 | 700.00B USD | 389.82 | -28.9% | Data Center 维持高增长、Helios 按计划放量：2 年后收入 800 亿美元、净利率 25%、35 倍 P/E，认股权证归属一半稀释约 10%。 |
| bull | 2y | 110.00B USD | 40x pe @ 30% 净利率 | 1.32T USD | 676.08 | +23.2% | OpenAI/Meta 里程碑全部达成、份额明显提升：2 年后收入 1100 亿美元、净利率 30%、40 倍 P/E，认股权证全部归属稀释 19.6%。 |

> 情景是“要成立需要什么”的假设推演，不是目标价、收益预测或交易建议。

<!-- section:signals -->
## 5. 先行信号（不等财报）
- **Q3 FY2026 财报中的 Data Center 收入**（filing）— 确认：DC 收入 ≥ 80 亿美元且环比继续增长；否定：DC 收入环比下滑或低于 70 亿美元；下次检查：2026-11-10
- **Q3 毛利率**（filing）— 确认：GAAP 毛利率维持 ≥ 53%；否定：GAAP 毛利率跌破 52%（内存/基板成本挤压）；下次检查：2026-11-10
- **Helios 机架平台首批出货**（anchor_customer_action）— 确认：2026 年底前确认出货给客户；否定：推迟到 2027 年；下次检查：2026-12-31
- **OpenAI/Meta 认股权证首批归属披露**（filing）— 确认：披露首批归属（意味着 GPU 采购里程碑达成）；否定：连续两个季度无归属；下次检查：2027-02-15

<!-- section:memory -->
## 6. Serenity 公开言论记录（时点）
状态：`unavailable`

No Serenity stance ledger supplied (--ledger). Silence in this pack is not a view.

<!-- section:serenity-view -->
## 7. 按 Serenity 框架会怎么看
框架是否关注：**maybe** — 按框架，AMD 吃到了 AI 资本开支（卖铲子），但它是中游的大市值热门股，卡点在 TSMC/HBM 上游；Serenity 式做法是顺着 AMD 的供应约束往上游找更小、更早的卡点，而不是追高 AMD 本身。（规则：PB-CORE-02, PB-HUNT-01, PB-GATE-02, PB-RED-01）

<!-- section:next-hop -->
## 下一跳候选（研究线索，非推荐）
| 代码 | 名称 | 关系 | 节点 | 理由 | 依据 | 先验证 |
|---|---|---|---|---|---|---|
| `TSM` | Taiwan Semiconductor Manufacturing | 上游 | ≤7nm 晶圆代工与先进封装 | AMD 的 ≤7nm 产品全部由 TSMC 制造，是 AMD 出货上限的直接约束。 | 实时数据 | 核对 TSMC 先进封装产能扩张节奏与 AI 客户占比 |
| `MU` | Micron Technology | 上游 | HBM 内存 | 10-K 警示内存短缺风险，HBM 是 GPU 出货的另一个约束。 | 推断 | 核对 HBM 产能是否售罄及对 AMD 的供货份额 |

<!-- section:red-flags -->
## 8. 红旗筛查
- [watch] company_check_B2：**yes** — 商誉 / 归母权益 = 37.89%：主要来自历史收购（含 ZT Systems，其制造业务已于 2025-10 剥离），10-Q 商誉 254.7 亿美元，未见减值，属关注项不改结论。 [E-LIVE-FIN] [E-LIVE-DOC-02]
- [watch] shelf_registration_on_file：**yes** — 2026-08-13 提交 S-3ASR 自动储架，随后 424B5 用于发行优先票据（债务，一般公司用途/可能偿债），不是增发股票。 [E-LIVE-SEC-05] [E-LIVE-SEC-03]
- [watch] repeated_prospectus_takedowns：**no** — 8/13 与 8/14 两份 424B5 是同一笔票据的初稿与定稿，配合 8/17 的 8-K 新增债务，不是连续 ATM 增发。 [E-LIVE-SEC-03] [E-LIVE-SEC-04] [E-LIVE-SEC-08]
- [watch] unregistered_equity_sale_8k_3_02：**yes** — 2026-09-28 8-K Item 3.02：以全股票方式收购 World Labs，约 82 亿美元，约占市值 0.9%，股数按交割前 10 日 VWAP 计算，稀释有限。 [E-LIVE-SEC-06]
- [watch] material_agreement_8k_1_01：**yes** — 2026-08-17 8-K：重大协议 + 新增直接债务，推断对应 8 月优先票据发行；AMD 净现金约 107.6 亿美元，债务压力低。 [E-LIVE-SEC-08] [E-LIVE-FIN]
- [watch] beneficial_owner_filings：**no** — 13G（2026-04-29）与 13G/A（2026-03-26）为被动大机构持股申报，不是激进股东信号。 [E-LIVE-SEC-10] [E-LIVE-SEC-11]
- [watch] insider_form4_activity：**unknown** — 本次未逐一核对 Form 4，未判断内部人买卖方向。 
- [watch] going_concern_exhibit_only：**no** — 持续经营字样只出现在附件/被收购方文件中，AMD 自身有约 84 亿美元 TTM 自由现金流和净现金，无持续经营风险。 [E-LIVE-FIN]
- [watch] customer_concentration：**no** — 10-K：FY2025/FY2024 无单一客户占收入 ≥10%；但 OpenAI、Meta 认股权证绑定会提高未来大客户集中度。 [E-LIVE-DOC-01] [E-LIVE-DOC-02]
- [watch] supply_concentration：**yes** — 10-Q：≤7nm 晶圆全部依赖 TSMC，部分设备材料只有有限或唯一供应商——AMD 是被卡的一方。 [E-LIVE-DOC-02]
- [watch] capacity_language：**yes** — 10-K/10-Q 警示内存、基板、设备短缺可能限制出货；上半年为供应协议预付约 10 亿美元，说明是产能受限而非需求受限。 [E-LIVE-DOC-01] [E-LIVE-DOC-02]
- [watch] atm_language：**no** — 未见 at-the-market 股权销售协议；储架用于债券。 [E-LIVE-SEC-05]
- [downgrade] warrant_dilution：**yes** — OpenAI 与 Meta 各获最多 1.6 亿股认股权证（行权价 0.01 美元），合计最多 3.2 亿股，约占现有股本 19.6%，按 GPU 采购里程碑和股价目标归属；截至 2026-06-27 尚未归属。 [E-LIVE-DOC-02] [E-LIVE-SHARES]

<!-- section:red-team -->
## 9. 红队：杀死这个判断的最短路径
1. 为什么可能不是真瓶颈？AMD 是第二来源而非卡点：客户可以多等 NVIDIA、改用自研 ASIC/TPU；AMD 的产能本身由 TSMC 与 HBM 决定。
2. 为什么可能不变现？认股权证相当于用最多 19.6% 的股本换订单，收入放量时每股价值可能被稀释抵消。
3. 市场是否已定价？约 8956 亿美元市值、139 倍 P/E，市场已计入高速增长；即使 base 情景兑现，隐含价值也低于现价。
4. 更优替代：`TSM` — AMD 与竞争对手的先进芯片都要经过 TSMC，押上游卡点比押下游赛马更少依赖单一产品周期。

**最大杀点：** Helios 延期 + Q3 Data Center 增速明显放缓，同时认股权证照常归属带来稀释，估值从 139 倍 P/E 回落。

<!-- section:falsification -->
## 10. 证伪条件
- Q3 FY2026 Data Center 收入低于 70 亿美元 `机器可检: amd_datacenter_revenue_q3_fy2026_usd < 7000000000.0`（检查：2026-11-10）（PB-EXIT-03）
- Q3 FY2026 GAAP 毛利率低于 52% `机器可检: amd_gaap_gross_margin_q3_fy2026 < 0.52`（检查：2026-11-10）（PB-EXIT-03）
- Helios 在 2026-12-31 前未开始出货（检查：2026-12-31）（PB-EXIT-11）

<!-- section:evidence -->
## 证据
- [E-LIVE-QUOTE] AMD quote 548.6 USD (NasdaqGS) — https://query1.finance.yahoo.com/v8/finance/chart/AMD?range=1y&interval=1d（2026-10-19，market_data）
- [E-LIVE-SHARES] Shares outstanding 1,632,475,042 as of 2026-07-29 (sec_companyfacts) — https://data.sec.gov/api/xbrl/companyfacts/CIK0000002488.json（2026-07-29，filing）
- [E-LIVE-FIN] Latest quarterly revenue 11,536,000,000 USD (period end 2026-06-27); TTM 41305000000; YoY 50.11%; GM 53.77% — https://data.sec.gov/api/xbrl/companyfacts/CIK0000002488.json（2026-06-27，filing）
- [E-LIVE-SEC-01] 10-Q filed 2026-08-05 — https://www.sec.gov/Archives/edgar/data/2488/000000248826000123/amd-20260627.htm（2026-08-05，filing）
- [E-LIVE-SEC-02] 10-Q filed 2026-05-06 — https://www.sec.gov/Archives/edgar/data/2488/000000248826000076/amd-20260328.htm（2026-05-06，filing）
- [E-LIVE-SEC-03] 424B5 filed 2026-08-14 — https://www.sec.gov/Archives/edgar/data/2488/000119312526352628/d173126d424b5.htm（2026-08-14，filing）
- [E-LIVE-SEC-04] 424B5 filed 2026-08-13 — https://www.sec.gov/Archives/edgar/data/2488/000119312526348029/d173126d424b5.htm（2026-08-13，filing）
- [E-LIVE-SEC-05] S-3ASR filed 2026-08-13 — https://www.sec.gov/Archives/edgar/data/2488/000119312526348013/d97381ds3asr.htm（2026-08-13，filing）
- [E-LIVE-SEC-06] 8-K filed 2026-09-28 (unregistered equity sale) — https://www.sec.gov/Archives/edgar/data/2488/000000248826000182/amd-20260926.htm（2026-09-28，filing）
- [E-LIVE-SEC-07] 8-K filed 2026-08-19 (officer/director change, exhibits) — https://www.sec.gov/Archives/edgar/data/2488/000000248826000163/amd-20260817.htm（2026-08-19，filing）
- [E-LIVE-SEC-08] 8-K filed 2026-08-17 (material definitive agreement, new debt obligation, exhibits) — https://www.sec.gov/Archives/edgar/data/2488/000119312526354029/d142696d8k.htm（2026-08-17，filing）
- [E-LIVE-SEC-09] 8-K filed 2026-08-04 (results of operations, Reg FD disclosure, exhibits) — https://www.sec.gov/Archives/edgar/data/2488/000000248826000121/amd-20260804.htm（2026-08-04，filing）
- [E-LIVE-SEC-10] SCHEDULE 13G filed 2026-04-29 — https://www.sec.gov/Archives/edgar/data/2488/000210011926000052/xslSCHEDULE_13G_X02/primary_doc.xml（2026-04-29，filing）
- [E-LIVE-SEC-11] SCHEDULE 13G/A filed 2026-03-26 — https://www.sec.gov/Archives/edgar/data/2488/000010290926000540/xslSCHEDULE_13G_X02/primary_doc.xml（2026-03-26，filing）
- [E-LIVE-NEWS-01] [lead] Advanced Micro Devices, Inc. (AMD) is Attracting Investor Attention: Here is What You Should Know - Yahoo Finance — https://news.google.com/rss/articles/CBMimwFBVV95cUxNRTJ5YzhaNG1LMFJnazZBaXNsV3JWRENRZjBZSno5UVc0a3Rjc28wVkpHRXBYTmpOSzQ0Tm1qXzZpbFNFYVpmVDktMUJtUUFSNnpJTkJVbG16M3dCa3dDamJmcE1lUFJzYmpoYXEyR1RaQTFkUGVmUzM3cTM4X0pmWUNnSDV2ODVvdk5CN29XT1lsZnF6bUU0RHVRQQ?oc=5（2026-10-19，news）
- [E-LIVE-NEWS-02] [lead] ETFs Are Net Sellers of Advanced Micro Devices (AMD) on Oct. 15 - Yahoo Finance — https://news.google.com/rss/articles/CBMinAFBVV95cUxPeGlBUlFnLW80bW5ac3JyYkJnNmR6QThXVzB1VU15Y3paT2ZhNTY1TlRQU01Va3M5TEM1NkE4OXNSVjd5X3FTaF91bElwVnZCSlV1ZVNVNkU5R0xSS3NoRTYydml3TnZiYTZQYVNxaDdTZHBJNU5nOUIyOWY0YXI4b1ZyRnNaVHNTVm5kSmx2QmwwN3BkSU5Yc0x0UzA?oc=5（2026-10-19，news）
- [E-LIVE-NEWS-03] [lead] Advanced Micro Devices, Inc. $AMD Shares Sold by Wealth Intelligence LLC - MarketBeat — https://news.google.com/rss/articles/CBMiygFBVV95cUxOS0djVTNPb09IQlN5TlRDM284Z29JRXhWTVBreVo2ZUJyZ2g1VUtqRnl3NzdweHJuaGx4UjJWWWlSMGZrdHdhRmpqOERzX3pURW93bVdyb3VwWVZDazlJYmRkQTNZS3ZqY01ONUlSUmdZOG5jamdSRFA0N3Bkc2ZWN0FaZGVyekV6Rk1MaGNNdENIbkdHeUgwZWRUWWhmMEtacnZYMVRhOTFjNkVDZEF1aXlrajJSUnA3SVBMZjRsV1o2QU8xTmh2RzFR?oc=5（2026-10-18，news）
- [E-LIVE-NEWS-04] [lead] Why Is Advanced Micro Devices (AMD) Gaining Ground In AI Infrastructure? - Yahoo Finance — https://news.google.com/rss/articles/CBMimgFBVV95cUxORDFNWFI4R2wzZ2VnVUVGc0ZYVkxMRlM3MkdLeWhzUkZCdWZvWDY0Z3VuSkt3cTExb190N3J3SXhidFVxa095cEtJbkNnaU5JX0J5YU84eEZxcWRGalVJczE5LXp3WmtUVFJvRTdVclhCby1PMUpSbGlpYV9RRHdqald1aGVwVkpnZkw4NzRxZjJzeHBrbmpKR0Fn?oc=5（2026-10-18，news）
- [E-LIVE-NEWS-05] [lead] What Advanced Micro Devices Buyers Were Betting On Before A 137% Rally - Yahoo Finance — https://news.google.com/rss/articles/CBMioAFBVV95cUxOU2h5aVQyRmhyZ01ObjBaQWhrQVkxc3ZCUFNoMGFoZ09rX2hPT0hRR1p0eFcwd3lGSldjdkJXTWlLQjR1Zl9CcW9NRFFuRHMwM0U3Z21MUzJGQVIxUnJzdGN2Qkt2T1ExMGVZUzVnMnNraks3bkxwQ09ocFUyYk5JSUVLZ09EMjFtc0xzYjFMamlscDFKcGZWQms2Wkk5M0lo?oc=5（2026-10-18，news）
- [E-LIVE-NEWS-06] [lead] What to Expect From Advanced Micro Devices’ Q3 2026 Earnings Report - Barchart.com — https://news.google.com/rss/articles/CBMirwFBVV95cUxNZW14RzdiVVdZRk1UcFNCVWZyRER4aTBCN0JhaFZxbDNDMl96SEFlYmZFdFJVMTk0OFVjd2MzenUyRXZYSVVUbkVjWlBJTUttUzJmRjY0ZzRyVGdIZDdaUnpHRVBsVEZld2pjQ2ZpX2dSckxpWWROVWt5NU5kejYxTzhWWExMVG1FaFRRYVB3cmpYSmhlQ1FfYUU3WWhxc2tBeG9kWXpyaGstQjE1X3NR?oc=5（2026-10-17，news）
- [E-LIVE-DOC-01] 10-K filed 2026-02-04 (primary document) — https://www.sec.gov/Archives/edgar/data/2488/000000248826000018/amd-20251227.htm（2026-02-04，filing）
- [E-LIVE-DOC-02] 10-Q filed 2026-08-05 (primary document) — https://www.sec.gov/Archives/edgar/data/2488/000000248826000123/amd-20260627.htm（2026-08-05，filing）

审计层：research_output `research:amd-2026-10-19`，bundle 校验 未运行

<!-- section:disclaimer -->
---
⚠️ 框架声明：本 skill 根据 Serenity 公开发布的内容提炼研究框架，用于回测与研究分析；报告由框架生成，不代表 Serenity 本人观点，亦非投资建议。

<!-- serenity-lens lens_id=lens:amd-2026-10-19 sha256=b2ba2f6752216e8c1bafff4acc11f9d2f5cd2ff8d9b40a04f2cfb41432e41d9d -->

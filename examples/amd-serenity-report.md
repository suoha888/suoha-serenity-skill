# Advanced Micro Devices, Inc.（AMD）· Serenity 框架卡点透镜

<!-- section:verdict -->
> **🟡 观察/等触发** · AMD 是 AI 资本开支的确定受益者，但在 Serenity 框架里它是“被卡的赛马者”而不是卡点：真正的不对称在它上游的 CoWoS/HBM4/CPO。
> 截止 2026-10-17 · 类型 `fabless_designer` · 市值 863.17B USD（2026-10-16）

<!-- section:thirty-sec -->
## 30 秒看懂
需求端确定：OpenAI 6GW、Anthropic 2GW 与 Q3 约 $13B 指引给出了 2026–2027 的资本开支锚。但 AMD 的出货上限由 TSMC N2/N3 与 CoWoS 分配、HBM4 合约量决定，它本身不是卡点。$863B 市值、约 80 倍年化非 GAAP EPS 已计入 Helios 顺利放量；另有最多 3.2 亿股认股权证稀释。研究分级 amber：基本面强，但三闸门里“机构前”“便宜且去风险”不过关。用 Serenity 的方法，AMD 更适合作为下游锚点，去上溯找卡点。

**分级理由：** 需求与执行证据强，但“机构前”与“便宜且去风险”两道闸门未通过，且认股权证稀释压低每股弹性；适合作为上溯卡点的锚点，不适合作为不对称标的。

**重估触发条件：** Q3/Q4 证实 Helios 放量且非 GAAP 毛利率守住 56%；供应链确认 AMD 2027 CoWoS 份额上升；估值回落到 base 情景隐含价值附近（研究复核触发，不是交易指令）

<!-- section:capex -->
## 1. 资本开支确定性
- 需求来源：`hyperscaler_commercial`
- OpenAI（6GW，首 GW 2H26）与 Anthropic（2GW，首 GW 1H27）的多 GW 协议，加上 Q3 约 $13B 指引与 2H26 服务器收入同比 >80% 的口径，构成可核验的需求锚。 [ev:openai-6gw] [ev:amd-anthropic] [ev:amd-q2-release] [ev:amd-q2-call]

<!-- section:chain -->
## 2. 卡点地图：AI 加速器与机架级系统（MI450 / Helios）
- **下游对照**：OpenAI（private）：6GW 部署协议、认股权证持有方；Anthropic（private）：2GW MI450/Helios 部署；Meta Platforms `META`：认股权证持有方、GPU 客户
- **中游系统**：**AMD Helios / MI450** `AMD`：机架级 AI 系统与加速器设计（fabless）；NVIDIA Vera Rubin `NVDA`：直接竞品，争夺同一批客户与同一份 CoWoS；台湾 ODM（Wiwynn 等） `6669.TW`：机架组装与集成（线索，待一手核实）
- **中游器件**：HBM4（SK hynix / Micron / Samsung） `MU`：高带宽内存，合约价上行、产能被预订；CPO 光引擎（SIVE + GFS，推测） `SIVE.ST`：共封装光学激光器/硅光代工（线索，待核实）
- **上游设备**：TSMC N2/N3 + CoWoS `TSM`：≤7nm 晶圆唯一来源 + 2.5D 先进封装产能；ASE / SPIL `ASX`：OSAT 封测与先进封装分流；Intel EMIB `INTC`：CoWoS 的替代封装路线（Google TPU 已采用）
- **跨主题根节点**：GW 级数据中心电力（unknown）：协议以 GW 计价，部署节奏受电力与场地约束

<!-- section:chokepoint -->
**卡点中的卡点**（inferred）：TSMC CoWoS + HBM4 — AMD 2027 年能交付多少 MI450，取决于 TSMC 分给它多少 CoWoS 与能锁到多少 HBM4；2026 年 >85% CoWoS 已被三家锁定、交期 52–78 周。卡点的卡点在先进封装 + HBM4，而不在 GPU 设计。 [ev:amd-10q] [ev:tf-cowos-cap] [ev:tf-cowos-gap] [ev:sa-hbm4]

| 卡点原型 | 命中 | 理由 |
|---|---|---|
| ARC-SOLE-SOURCE | no | AMD 自己依赖 TSMC 唯一来源，是被卡方而非唯一供应方。 [ev:amd-10q] |
| ARC-CAPACITY-LOCK | partial | AMD 是 CoWoS 锁量三家之一，锁到的产能对二线竞品是壁垒，但不对 NVDA 构成约束。 [ev:sa-hbm4] |
| ARC-TRANSITION-GATE | partial | 机架级 Helios 是从卖芯片到卖系统的跃迁，若放量顺利可抬高份额，但 NVDA 已先行。 [ev:amd-q2-call] [ev:nvda-rubin] |
| ARC-CAPEX-PICKS-SHOVELS | yes | 多 GW 协议使 AMD 直接吃到超大规模资本开支，只是位置在中游而非上游。 [ev:openai-6gw] [ev:amd-anthropic] |

<!-- section:gates -->
## 3. 三道闸门
- 🔒 真瓶颈：◐ 部分 — AMD 是 NVDA 之外唯一的规模化 GPU 第二来源，客户有分散供应的需求；但它本身受 CoWoS/HBM4 约束，不是卡点。 [ev:amd-10q] [ev:sa-hbm4]
- 👁️ 前机构：❌ 不过 — $863B 超大市值，覆盖充分、持仓拥挤，不存在信息差窗口。 [ev:amd-close]
- 💰 便宜且去风险：❌ 不过 — 约 80 倍年化 Q2 非 GAAP EPS、约 16.6 倍年化 Q3 指引收入，已计入 Helios 顺利放量。 [ev:amd-q2-release] [ev:amd-close]

<!-- section:valuation -->
## 4. 估值不对称（尺子：`hypergrowth_forward`）
现价 528.75 USD × 股本 1,632,475,042 = 市值 863.17B USD [ev:amd-close] [ev:amd-10q]

| 情景（假设） | 期限 | 收入 | 倍数 | 隐含市值 | 隐含每股 | 相对现价 | 叙事 |
|---|---|---|---|---|---|---|---|
| bear | 2y | 60.00B USD | 28x pe @ 22% 净利率 | 369.60B USD | 205.82 | -61.1% | 放量延后、HBM4 成本吃掉毛利，倍数回到成熟半导体区间；部分认股权证仍按部署进度行权。 |
| base | 2y | 85.00B USD | 35x pe @ 27% 净利率 | 803.25B USD | 427.86 | -19.1% | Helios 按 Q3 首发、Q4 放量的节奏推进，DC 成为收入主体；倍数从当前水平回落到增长股常态。 |
| bull | 2y | 120.00B USD | 40x pe @ 30% 净利率 | 1.44T USD | 737.54 | +39.5% | 多 GW 同时放量、经营杠杆释放，但认股权证全额稀释，每股价值的弹性明显低于收入弹性。 |

同层对照：`NVDA` 同一份 CoWoS 的主要争夺者，Vera Rubin 已全面投产。；`TSM` 两家 GPU 的共同上游卡点；押卡点而非押赛马者的对照组。

> 情景是“要成立需要什么”的假设推演，不是目标价、收益预测或交易建议。

<!-- section:signals -->
## 5. 先行信号（不等财报）
- **Q3 FY2026 业绩与 Q4 指引**（filing）— 确认：Q3 收入 ≥ $13B 且 Q4 指引环比继续增长；否定：Q3 收入低于 $12.7B 或 Q4 指引低于 Q3 实际；下次检查：2026-11-03
- **HBM4 合约价与供应商锁量**（spot_price）— 确认：AMD 锁量披露增加且价格上行可被转嫁；否定：毛利率因 HBM 成本跌破 55%；下次检查：2026-11-03
- **TSMC CoWoS 扩产与 AMD 份额**（capacity_announcement）— 确认：供应链确认 AMD 2027 CoWoS 份额上升；否定：扩产被 NVDA/AVGO 新增订单吸收；下次检查：2027-01-15
- **OpenAI 首个 1GW MI450 实际部署**（anchor_customer_action）— 确认：2026 年底前确认开始部署；否定：部署推迟到 2027 或转向其他供应商；下次检查：2026-12-31

**OSINT 线索：** AMD CPO 光引擎供应商是否为 SIVE + GFS（social_lead + 供应链公告, open）；台湾 $10B+ 生态投资对应的 ODM/OSAT 订单分配（social_lead + 台股月营收, open）；服务器 CPU 涨价是否延续到 Q3/Q4（渠道价格 + 财报口径, open）

<!-- section:memory -->
## 6. Serenity 公开言论记录（时点）
状态：`available` · 当前 `DORMANT（档案只覆盖到 2026-06，沉默不等于卖出）` · 首提 2025-10-06 · 最近 2026-06-03 · 提及 30 次
- 2025-10-11 `MENTION`/bullish · post 1977157799164686796 · 以 OpenAI 合同放量为依据，给出一年期偏多看法。
- 2025-11-05 `MENTION`/bullish · post 1985986580155163038 · 认为上行空间很大，依据是头部模型方确认 AMD 可用。
- 2025-12-05 `MENTION`/neutral · post 1996821550692290898 · 自述立场转弱：原先看多依赖 OpenAI 领先，竞品模型反超后下调。
- 2026-01-07 `MENTION`/neutral · post 2008877319239487537 · 把“每代都说要赢 NVDA”当作需要打折的管理层叙事。
- 2026-04-19 `REAFFIRM`/bullish · post 2045965735386820934 · 在回顾清单中重申对 AMD 的长期看法未变。
- 2026-04-23 `MENTION`/bullish · post 2047182611160965383 · 指出服务器 CPU 严重短缺、价格上调。
- 2026-04-27 `MENTION`/neutral · post 2048799639525351574 · 推测 AMD 的 CPO 选择 SIVE + GFS，把 AMD 当作上游线索。
- 2026-05-21 `MENTION`/bullish · post 2057388984310132855 · 引用 AMD 在台湾投资 $10B+ 锁产能，点名 OSAT 与 ODM 伙伴。

档案覆盖至 2026-06-05；此后 Serenity 是否有新表态未知（沉默不等于卖出或看空）。

截至 2026-10-17 的时点查询；未见明确建仓/持仓披露，持仓状态 UNKNOWN。规则基线把 2025-12-05 误标为 bullish，已人工改为 neutral，说明立场抽取需 LLM 或人工复核。Serenity 的言论只是线索，不是公司事实。

<!-- section:serenity-view -->
## 7. 按 Serenity 框架会怎么看
框架是否关注：**maybe** — 按 Serenity 框架会关注 AMD，但更多把它当作下游需求锚和供应链线索的来源（CPO、OSAT、ODM），而不是不对称标的；框架的高赔率区间在市值小、被低估的上游卡点。（规则：PB-CORE-02, PB-HUNT-01, PB-GATE-02, PB-RED-01）

<!-- section:red-flags -->
## 8. 红旗筛查
- [downgrade] 认股权证稀释：**yes** — OpenAI 与 Meta 各最多 1.6 亿股、行权价 $0.01，合计最多约 19.6% 股本；收入增长不一定等于每股增长。 [ev:amd-10q] [ev:openai-6gw]
- [watch] 单一代工来源：**yes** — ≤7nm 晶圆唯一来源 TSMC，地缘与产能分配风险集中。 [ev:amd-10q]
- [watch] 出口管制与中国许可：**yes** — MI325 对华许可于 2026 年 2 月取得，政策可逆。 [ev:amd-10q]
- [downgrade] 共识拥挤：**yes** — 超大市值、高倍数，边际买家有限，不符合“机构前”的不对称条件。 [ev:amd-close]
- [veto] 融资/持续经营风险：**no** — 现金及短投 $13.1B、债务 $3.3B、上半年经营现金流 $5.3B，无此类风险。 [ev:amd-10q]

<!-- section:red-team -->
## 9. 红队：杀死这个判断的最短路径
1. 为什么可能不是真瓶颈？AMD 是 GPU 第二来源而非卡点：客户可以等 NVDA、上 TPU/自研 ASIC，或改用 EMIB 封装；AMD 自己的产能受 TSMC 与 HBM 约束。
2. 为什么可能不变现？多 GW 协议与认股权证绑定，相当于用股权补贴价格；收入放量时每股收益可能被稀释和 HBM 成本同时侵蚀。
3. 市场是否已定价？$863B、约 80 倍年化 EPS，市场已计入 Helios 顺利放量和多 GW 转化；即便 base 情景兑现，隐含价值也低于现价。
4. 更优替代：`TSM` — AMD 与 NVDA 的 2027 出货都要经过 TSMC N2/N3 与 CoWoS；押卡点比押赛马者的胜负更少依赖单一产品周期。

**最大杀点：** OpenAI 首个 GW 延期且 NVDA 锁走 CoWoS 新增产能，导致 2027 年 DC GPU 收入显著低于市场隐含，同时认股权证照常稀释。

<!-- section:falsification -->
## 10. 证伪条件
- Q3 FY2026 收入低于指引下沿 $12.7B `机器可检: amd_revenue_q3_fy2026_usd < 12700000000.0`（检查：2026-11-03）
- Q3 FY2026 非 GAAP 毛利率低于 55% `机器可检: amd_nongaap_gross_margin_q3_fy2026 < 0.55`（检查：2026-11-03）
- OpenAI 首个 1GW MI450 部署在 2026 年底前未开始（检查：2026-12-31）

<!-- section:evidence -->
## 证据
- [ev:amd-q2-release] AMD Q2 FY2026 业绩新闻稿：收入 $11.536B、DC $6.7B、Q3 指引约 $13B — https://ir.amd.com/news-events/press-releases/detail/1295/amd-reports-second-quarter-2026-financial-results（2026-08-04，company_release）
- [ev:amd-10q] AMD 10-Q（截至 2026-06-27）：股本 1,632,475,042（2026-07-29）、TSMC 唯一来源、OpenAI/Meta 认股权证、现金 $13.1B/债务 $3.3B — https://ir.amd.com/financial-information/sec-filings/content/0000002488-26-000123/amd-20260627.htm（2026-08-05，filing）
- [ev:amd-q2-call] AMD Q2 FY2026 电话会：Helios 投产、2H26 服务器收入同比 >80% — https://d1io3yog0oux5.cloudfront.net/_55290e38f3fafb37f420fede91561c89/amd/db/841/9237/webcast_transcript/AMD2Q26EarningsCallTranscript.pdf（2026-08-04，earnings_call）
- [ev:amd-anthropic] AMD × Anthropic：最多 2GW MI450/Helios，首个 GW 于 1H27 开始 — https://ir.amd.com/news-events/press-releases/detail/1292/amd-and-anthropic-announce-strategic-partnership-to-（2026-07-22，company_release）
- [ev:openai-6gw] OpenAI × AMD 6GW 协议：首个 1GW MI450 于 2H26 开始；最多 1.6 亿股认股权证 — https://openai.com/index/openai-amd-strategic-partnership/（2025-10-06，company_release）
- [ev:tf-cowos-cap] TrendForce：TSMC CoWoS 约 13 万片/月（2026 年底）→ 26 万（2028 年底） — https://www.trendforce.com/news/2026/09/14/news-tsmc-reportedly-targets-22-2nm-16-3nm-capacity-boost-by-mid-20（2026-09-14，industry_data）
- [ev:tf-cowos-gap] TrendForce：CoWoS 供需缺口约 20% → 2026 年底约 10% — https://www.trendforce.com/news/2026/06/15/news-tsmc-cowos-supply-demand-gap-reportedly-seen-narrowing-from-20（2026-06-15，industry_data）
- [ev:sa-hbm4] Silicon Analysts 通讯：HBM4 合约价大涨；2026 年 >85% CoWoS 被 NVDA/AVGO/AMD 锁定；交期 52–78 周 — https://siliconanalysts.com/newsletter/qual-watch/2026-10-05（2026-10-05，analysis）
- [ev:amd-close] AMD 2026-10-16 收盘 $528.75（Macrotrends、Markets Insider 交叉核对） — https://fiscal.ai/company/NasdaqGS-AMD（2026-10-16，market_data）
- [ev:amd-ir-cal] AMD IR 日历：Q3 FY2026 业绩 2026-11-03 — https://ir.amd.com/（2026-10-06，company_release）
- [ev:nvda-rubin] NVIDIA：Vera Rubin 全面投产，Anthropic/Meta/OpenAI 计划采用 — https://www.manilatimes.net/2026/03/17/tmt-newswire/globenewswire/nvidia-vera-rubin-opens-agentic-ai-frontier/（2026-03-16，company_release）
- [ev:digitimes-emib] DIGITIMES：Google TPU 采用 Intel EMIB；Morgan Stanley 认为 AMD 2027 CoWoS 份额或上升 — https://www.digitimes.com/tag/cowos/00111842.html（2026-09-05，news）
- [ev:ser-2057388984310132855] Serenity 帖子（线索）：AMD 投资台湾生态 $10B+，合作 ASE/SPIL 与 ODM — https://x.com/i/status/2057388984310132855（2026-05-21，social_lead）
- [ev:ser-2048799639525351574] Serenity 帖子（线索）：推测 AMD CPO 选择 SIVE + GFS — https://x.com/i/status/2048799639525351574（2026-04-27，social_lead）
- [ev:ser-2047182611160965383] Serenity 帖子（线索）：服务器 CPU 严重短缺、涨价 10–20% — https://x.com/i/status/2047182611160965383（2026-04-23，social_lead）

审计层：research_output `research:amd-2026-10-17`，bundle 校验 未运行

<!-- section:disclaimer -->
---
⚠️ 本报告由 suoha-serenity-skill 生成，仅用于回测与研究分析，非投资建议（not investment advice）。本 skill 根据 Serenity 公开发布的内容提炼研究框架；报告不代表 Serenity 本人观点。情景估值是“需要什么条件才成立”的假设推演，不是目标价或收益预测。Serenity 的帖子仅作为线索，未经核实不视为事实。

框架声明：本 skill 根据 Serenity 公开发布的内容提炼研究框架，用于回测与研究分析；报告由框架生成，不代表 Serenity 本人观点，亦非投资建议。

<!-- serenity-lens lens_id=lens:amd-2026-10-17 sha256=91608ce0e8a992d5c7b18837cb09f456b9debbbf48e1ec9955492164ed988b80 -->

# AXT, Inc.（AXTI）· Serenity 框架卡点透镜

<!-- section:verdict -->
> **🟡 观察/等触发** · InP 衬底卡点正在变成“超级乙方”：Lumentum 6 年产能预留、Coherent 与 Casela 预付款；股价却较高点回撤 64%，仍被当周期材料股定价。
> 截止 2026-10-18 · 类型 `upstream_material` · 市值 3.38B USD（2026-10-16）

<!-- section:thirty-sec -->
## 30 秒看懂
实时数据：股价 51.47 美元，较 52 周高点回撤 64%，市值约 33.8 亿美元。Q2 收入 4,759 万美元（同比 +165%），毛利率 44.9%，营业利润率 21.9%。8-K 显示 2026 年签下三份产能预留/长协，年内约 9,100 万美元预付款，另有 2028 年 4,350 万美元押金——这是 Serenity 用来解释存储重估的“超级乙方”信号。股本一年 +42%，但来自 64.25 美元的包销增发，不是 ATM。机构前窗口已过，分级 amber；10-29 的 Q3 毛利率是第一检验点；更深一层看高纯红磷（4092.T）。

**分级理由：** 真瓶颈通过且正在变现，但“机构前”不过、稀释与出口许可仍未解决；更适合等待 Q3 毛利率验证，同时研究更上游的红磷层。

**重估触发条件：** Q3 毛利率 ≥ 40% 且两个季度内无新增发行；新增超大厂或第三家激光龙头的产能预留/预付款；估值回到 base 情景附近（研究复核触发，不是交易指令）

<!-- section:live-data -->
## 0. 实时数据
- 快照：`examples/live/axti-snapshot-2026-10-18.json` · 取数 2026-10-18T02:27:05Z · 来源 query1.finance.yahoo.com, www.sec.gov, data.sec.gov, efts.sec.gov, news.google.com
- ⚠️ `shares_as_of_older_than_price` → 股本取 2026-08-03 的 10-Q 封面数；之后未见新的 424B5，Q3 10-Q 发布后复核。
- ⚠️ `news_are_leads` → S&P 600 纳入与财报日期来自新闻线索，引用前应打开公司与指数公司的一手公告。
- ⚠️ `repeated_prospectus_takedowns` → 逐份打开 8-K：四份 424B 都对应包销增发（12.25 与 64.25 美元），不是 ATM，按 PB-FIN-04 处理。

<!-- section:doctrine -->
## 框架定位（Doctrine）
| 维度 | 判断 | 说明 |
|---|---|---|
| 框架适配 | 卡点 · 强 | 上游材料、产能高度集中、客户短期无法自建，正好落在框架核心。（PB-FIT-01, PB-LAW-02, PB-LAW-03） |
| 瓶颈状态 | 正在卡 · material | 毛利率从 8.0%（2025 Q2）升至 44.9%（2026 Q2），客户用押金和预付款锁产能，属于正在挤压的物料瓶颈。 [E-LIVE-FIN] [ev:8k-lumentum-cra] [ev:8k-casela-lta] |
| 阶段 | 量产爬坡 | Q2 收入环比 +77%、同比 +165%，营业利润率由负转正（21.9%）。 [E-LIVE-FIN] |
| 纯度 | 未知（unknown） | 公司还卖 GaAs、锗衬底和原料；InP 占比需从 10-Q 收入分类表核对，未核对前不填数字。 |
| 风险档 | 重估 | PB-STYLE-03 |

<!-- section:variant -->
## 差异化观点
- **市场共识**：股价较高点回撤 64%，价格在给中国许可、股本扩张和库存上升定价，筛选器把连续 424B5 读成 ATM 压力；卖方虽上调 2027 年收入预期，股价仍单日下跌 10%。 [E-LIVE-QUOTE] [E-LIVE-NEWS-01] [E-LIVE-NEWS-04]
- **我们的看法**：8-K 显示它正从周期材料股变成超级乙方：2026 年内约 9,100 万美元预付款（Lumentum 4,350 万 + Coherent 2,229 万 + Casela 约 2,540 万），另有 2028 年 4,350 万押金。融资是 64.25 美元的包销增发，不是 ATM。若 Q3 毛利率 ≥ 40%，33.8 亿美元约为 Q2 年化收入的 17.7 倍，接近 base 情景；周期折价收窄才是重估来源，代价是长协单价封顶了一部分涨价。
- **为什么市场可能错**：PB-VP-10, PB-VP-07, PB-VP-04
- **市场何时会看到**：2026-10-29 的 Q3 财报（毛利率与收入指引）
- **第一个证伪数字**：`axti_gross_margin_q3_2026_pct < 35`（2026-10-29 前检查）
- **档案之后的变化**：档案（覆盖到 2026-10-16）显示 Serenity 7 月仍看多，10 月回看认为论点基本兑现（PB-EXIT-07：下一步应换新问题重新立论）。同期一手信息：Casela 长协（6 月）、Coherent 预付协议（6 月）、Lumentum 6 年产能预留（7 月）；通美转香港上市；Q2 收入同比 +165%、毛利率 44.9%；新闻称已纳入 S&P 600；股价一年 +896%，但较 52 周高点回撤 64%。

<!-- section:capex -->
## 1. 资本开支确定性
- 需求来源：`hyperscaler_commercial`
- AI 光互连从可插拔走向 CPO，激光芯片需要 InP 衬底；Q2 收入同比 +165%、环比 +77%，与下游激光厂产能订满的线索一致。 [E-LIVE-FIN] [ev:ser-2053270948414099915]

<!-- section:chain -->
## 2. 卡点地图：AI 光子链：InP 原料 → 衬底 → 外延/代工 → 激光 → 光模块/CPO
- **下游对照**：Lumentum `LITE`：EML 激光龙头，下游定价权锚；Coherent `COHR`：综合光器件厂，向市场采购部分原料
- **中游器件**：Sivers Semiconductors `SIVE.ST`：CW 激光（无晶圆厂）；Win Semiconductors `3105.TWO`：InP/GaAs 激光代工
- **上游材料/代工**：**AXT, Inc.** `AXTI`：InP 衬底双寡头之一，自有部分原料/坩埚；Sumitomo Electric `5802.T`：InP 衬底另一家（敞口被大集团稀释）；JX Advanced Metals `5016.T`：InP 衬底第三供应商
- **跨主题根节点**：Nippon Chemical Industrial `4092.T`：高纯红磷（InP 原料）

<!-- section:chokepoint -->
**卡点中的卡点**（inferred）：高纯红磷 / InP 多晶原料 — InP 衬底本身依赖高纯红磷和 6N-7N 多晶原料；西方难以生产高纯红磷，衬底扩产会把压力传到这一层。 [ev:ser-2043918867349811626] [ev:ser-2058620094532718772]

| 卡点原型 | 命中 | 理由 |
|---|---|---|
| ARC-RAW-MATERIAL | yes | InP 衬底占激光 BOM 很小但不可替代，毛利率从 8% 升到 45% 体现定价权。 [E-LIVE-FIN] |
| ARC-SOLE-SOURCE | partial | 是双寡头而非唯一来源；关键看产能占比，而不是供应商家数。 [ev:ser-2034981779447455793] |
| ARC-SUPER-SUPPLIER | yes | Lumentum 6 年产能预留 + 押金、Coherent 预付并约定单价、Casela 全额预付长协：客户用现金锁产能。 [ev:8k-lumentum-cra] [ev:8k-coherent-mdsa] [ev:8k-casela-lta] |
| ARC-BOTTLENECK-OF-BOTTLENECK | partial | 自有部分原料/坩埚，部分吃到上游一层的价值，但高纯红磷仍有外部依赖。 [ev:ser-2058620094532718772] |

<!-- section:gates -->
## 3. 三道闸门
- 🔒 真瓶颈：✅ 通过 — 收入同比 +165%、毛利率同比 +36.9pp；两大激光龙头用押金/预付款锁定多年产能。 [E-LIVE-FIN] [ev:8k-lumentum-cra] [ev:8k-coherent-mdsa]
- 👁️ 前机构：❌ 不过 — 新闻称已纳入 S&P 600，另有 8 份 13G/13G/A，卖方与媒体大量覆盖，信息差窗口已关闭。 [E-LIVE-SEC-10] [E-LIVE-NEWS-08] [E-LIVE-NEWS-01]
- 💰 便宜且去风险：◐ 部分 — 约 17.7 倍 Q2 年化收入，现金及短投 4.17 亿美元且有客户预付款；但产能在中国，出口许可仍是外部变量。 [E-LIVE-QUOTE] [E-LIVE-SHARES] [E-LIVE-FIN]

<!-- section:valuation -->
## 4. 估值不对称（尺子：`chokepoint_comparable`）
现价 51.47 USD × 股本 65,573,212 = 市值 3.38B USD [E-LIVE-QUOTE] [E-LIVE-SHARES]

| 情景（假设） | 期限 | 收入 | 倍数 | 隐含市值 | 隐含每股 | 相对现价 | 叙事 |
|---|---|---|---|---|---|---|---|
| bear | 2y | 160.0M USD | 6x ps | 960.0M USD | 13.31 | -74.1% | 定价权回吐、毛利回到 30% 以下，市场把它重新当周期材料股，6 倍市销率。 |
| base | 2y | 260.0M USD | 12x ps | 3.12B USD | 45.31 | -12.0% | 定价权维持但不再加速，稀释放缓到 5%，12 倍市销率与高毛利材料股可比。 |
| bull | 2y | 400.0M USD | 18x ps | 7.20B USD | 104.57 | +103.2% | 公司把供给地位变现（主动提价、长协预付），市场按超级乙方给 18 倍市销率。 |

> 情景是“要成立需要什么”的假设推演，不是目标价、收益预测或交易建议。

<!-- section:signals -->
## 5. 先行信号（不等财报）
- **Q3 2026 业绩（10-29）**（filing）— 确认：收入 ≥ 4,500 万美元且毛利率 ≥ 40%；否定：毛利率 < 35% 或收入环比下滑超过 15%；下次检查：2026-10-29
- **下游激光厂对 InP 供给的表述**（peer_earnings）— 确认：LITE/COHR 继续称衬底或激光受限；否定：下游称供给已缓解、价格下降；下次检查：2026-11-15
- **中国出口许可节奏**（policy_export）— 确认：许可按季度稳定发放；否定：新增管制或许可暂停；下次检查：2026-12-31
- **通美香港上市申请进度**（other）— 确认：递表并披露 InP 业务估值；否定：上市再次搁置；下次检查：2027-03-31
- **新增 424B5 / ATM**（filing）— 确认：两个季度内没有新的发行；否定：股价反弹时出现新的 424B5；下次检查：2027-01-31

**OSINT 线索：** 高纯红磷供应商（4092.T）分部收入是否随衬底扩产加速（日本公司分部披露, open）；2026-07-29 8-K（1.01）对手方：Lumentum 6 年产能预留（SEC 8-K 正文, confirmed）；2026-07-08 8-K 第 2.04 项：通美撤回科创板、转香港上市（不是债务加速）（SEC 8-K 正文, confirmed）；Coherent 协议约定的单价是否低于现货，长协是否封顶了提价空间（10-Q 合同负债与毛利率, open）

<!-- section:memory -->
## 6. Serenity 公开言论记录（时点）
状态：`available` · 当前 `OPEN（档案覆盖到 2026-10-16；2026-07 仍表示看多并持有）` · 首提 2025-12-22 · 最近 2026-10-10 · 提及 461 次
- 2025-12-26 `OPEN`/bullish · post 2004577553714163817 · 提出铜转光子带来的 InP 衬底单点故障论点。
- 2026-03-20 `REAFFIRM`/bullish · post 2034981779447455793 · 强调产能占比与原料、衬底两层叠加的瓶颈。
- 2026-04-01 `MENTION`/neutral · post 2039261671739560026 · 给出条件：只有把供给地位变现才值更高估值。
- 2026-05-10 `REAFFIRM`/bullish · post 2053270948414099915 · 引用同业高管对 InP 短缺的公开表述作为印证。
- 2026-06-12 `MENTION`/bullish · post 2065291889885274552 · 回顾：这个论点花了数月，才被公司与政府公开确认 InP 衬底瓶颈。
- 2026-07-02 `MENTION`/bearish · post 2072733748261720186 · 指出上涨途中出现过流通股扩张与增发摊薄。
- 2026-07-08 `REAFFIRM`/bullish · post 2074972411557249248 · 表示仍然看多并持有。
- 2026-07-31 `REAFFIRM`/bullish · post 2083088870942642391 · 财报速评中仍把它列为最看好的名字之一。
- 2026-09-21 `MENTION`/bullish · post 2102068786493026492 · 认为 InP 衬底在中美谈判中具有筹码属性。
- 2026-10-10 `MENTION`/neutral · post 2108916977616179207 · 回看 2025 年论点，认为供给地位与超大厂风险基本被验证。

档案覆盖至 2026-10-16；此后 Serenity 是否有新表态未知（沉默不等于卖出或看空）。

立场只用于理解 Serenity 当时的思路，不用于跟单；档案后变化以实时数据为准。

<!-- section:serenity-view -->
## 7. 按 Serenity 框架会怎么看
框架是否关注：**yes** — 这是 Serenity 档案中最有代表性的卡点论点；按框架推演，下一步会关注能否主动提价，并把注意力移向更上游、更少人覆盖的原料层。（规则：PB-HUNT-08, PB-LAW-03, PB-LAW-05, PB-SIG-07, PB-VAL-12, PB-FIN-04）

<!-- section:next-hop -->
## 下一跳候选（研究线索，非推荐）
| 代码 | 名称 | 关系 | 节点 | 理由 | 依据 | 先验证 |
|---|---|---|---|---|---|---|
| `4092.T` | Nippon Chemical Industrial | 上游 | 高纯红磷（InP 原料） | 瓶颈的瓶颈：衬底扩产必须买它的高纯红磷，日本上市、覆盖少。 | Serenity 公开线索 | 运行 live_data snapshot 4092.T，核对相关分部收入与毛利是否加速 |
| `5802.T` | Sumitomo Electric | 西方替代 | InP 衬底（日本） | 非中国的衬底产能，地缘风险更低，但卡点业务被大集团稀释。 | Serenity 公开线索 | 核对化合物半导体业务占集团收入的比例（纯度） |
| `3105.TWO` | Win Semiconductors | 下游 | InP/GaAs 激光代工 | 衬底供给放松后，激光产能会成为新约束；研报覆盖少。 | Serenity 公开线索 | 看月营收与光通信产能扩充公告 |

<!-- section:red-flags -->
## 8. 红旗筛查
- [downgrade] 股本扩张：**yes** — 股本 4,612 万（2025-08）→ 6,557 万（2026-08），+42%。来自两次包销增发（12.25 美元、64.25 美元），不是 ATM；4 月那次价格高于现价，属于高位融资扩产（PB-FIN-04）。储架仍在，需关注再次发行。 [E-LIVE-SHARES] [ev:8k-offering-2025-12] [ev:8k-offering-2026-04] [E-LIVE-SEC-05]
- [watch] 中国出口许可与地缘：**yes** — 主要产能在中国，出口许可节奏决定出货；这是便宜的原因，也是论点的一部分（PB-RISK-03）。 [E-LIVE-SEC-01]
- [watch] 库存上升：**yes** — 存货 8,006 万（2025-06）→ 9,632 万美元（2026-06），需区分战略备料与滞销。 [E-LIVE-SEC-01] [E-LIVE-NEWS-03]
- [veto] 融资/持续经营风险：**no** — SEC 全文检索无持续经营措辞；现金及短投 4.17 亿美元，近四季 FCF 合计小幅为负。 [E-LIVE-FIN]

<!-- section:red-team -->
## 9. 红队：杀死这个判断的最短路径
1. 为什么可能不是真瓶颈？日本两家衬底厂和中国新进入者扩产后，衬底可能在 2027 年转为宽松；双寡头不等于不可替代。
2. 为什么可能不变现？长协用价格换确定性：Coherent 协议约定了单价，预付款是出货抵扣而非额外收入；若现货继续上涨，公司反而吃不到全部涨价。
3. 市场是否已定价？1 年涨近 9 倍，新闻称已纳入 S&P 600，卖方上调 2027 预期，市场已经知道这个卡点，剩余分歧主要在执行。
4. 更优替代：`4092.T` — 同一条链更上游、覆盖更少的高纯红磷供应商，日本上市折价，承接衬底扩产的需求。

**最大杀点：** 中国暂停 InP 衬底出口许可一个季度以上，同时公司在低位增发，营收和每股价值同时受损。

<!-- section:falsification -->
## 10. 证伪条件
- Q3 2026 毛利率低于 35% `机器可检: axti_gross_margin_q3_2026_pct < 35`（检查：2026-10-29）（PB-EXIT-03）
- Q3 2026 收入低于 4,000 万美元 `机器可检: axti_revenue_q3_2026_usd < 40000000`（检查：2026-10-29）（PB-EXIT-03）
- 两个季度内再次通过 424B5 增发（检查：2027-01-31）（PB-EXIT-04）

<!-- section:evidence -->
## 证据
- [E-LIVE-QUOTE] AXTI quote 51.47 USD (NasdaqGS) — https://query1.finance.yahoo.com/v8/finance/chart/AXTI?range=1y&interval=1d（2026-10-16，market_data）
- [E-LIVE-SHARES] Shares outstanding 65,573,212 as of 2026-08-03 (sec_companyfacts) — https://data.sec.gov/api/xbrl/companyfacts/CIK0001051627.json（2026-08-03，filing）
- [E-LIVE-FIN] Latest quarterly revenue 47,589,000 (period end 2026-06-30); TTM 125509000; YoY 164.77% — https://data.sec.gov/api/xbrl/companyfacts/CIK0001051627.json（2026-06-30，filing）
- [E-LIVE-SEC-01] 10-Q filed 2026-08-13 — https://www.sec.gov/Archives/edgar/data/1051627/000143774926027677/axti20260630_10q.htm（2026-08-13，filing）
- [E-LIVE-SEC-03] 424B5 filed 2026-04-21 — https://www.sec.gov/Archives/edgar/data/1051627/000121390026046176/ea0287123-424b5_axtinc.htm（2026-04-21，filing）
- [E-LIVE-SEC-05] S-3ASR filed 2026-04-20 — https://www.sec.gov/Archives/edgar/data/1051627/000121390026045578/ea0286790-s3asr_axt.htm（2026-04-20，filing）
- [E-LIVE-SEC-07] 8-K filed 2026-07-29 (material definitive agreement, exhibits) — https://www.sec.gov/Archives/edgar/data/1051627/000143774926024883/axti20260715_8k.htm（2026-07-29，filing）
- [E-LIVE-SEC-10] SCHEDULE 13G/A filed 2026-10-05 — https://www.sec.gov/Archives/edgar/data/1051627/000201238326003311/xslSCHEDULE_13G_X02/primary_doc.xml（2026-10-05，filing）
- [E-LIVE-NEWS-01] [lead] Seeking Alpha：AXT 是华尔街可能低估的 AI 基建瓶颈 — https://news.google.com/rss/articles/CBMisgFBVV95cUxONjVIdnFtbi14a1FhMEVJdFhEelpzQTg1eFdWU01sVnVMSlZ5ZGtEQlZ2akc1UWw5MW5GVk1LMV9XLXRDOE1fbGRZX3FpS2xHZjNDXzB5cGM3TEowRGNucWN0TDcwVkdLQy00WmFUWUlCZ1FJenZSNVIxeGp2RzAtcUUyVmFFWmp1VUhyR1FGS3BtZ2paRkVRd1k4dFVjc3J0b2dIYVhRMjF3YzIxc21UTGN3?oc=5（2026-10-17，news）
- [E-LIVE-NEWS-03] [lead] Yahoo Finance：AXT 存货大幅上升，营运资金压力 — https://news.google.com/rss/articles/CBMiowFBVV95cUxNV1p5T3QxanA3Nkp2cG5KQmlsV1Z4SGxvV25yQkpPR2RkSVBuVXZ0clVTTW5PV1lRNXpDNXVBbXhvdm9VMXVwb0NTUk9EMW9zUGI3LWNNMEtmbk8wekFLbkhUdDZBN0VtbHdYbldaUkZPejd5UmtXckpoaDlqSTJKcEdOY25uSEtEaFU2SGdlM2dONGVOT3pnYnkzZ0lnYUtfZ01Z?oc=5（2026-10-13，news）
- [E-LIVE-NEWS-04] [lead] TIKR：股价单日跌 10%，而分析师把 2027 年收入预期上调一倍以上 — https://news.google.com/rss/articles/CBMi4AFBVV95cUxPdksya2pzY0xrVFhSNEJ3LURBN0JybkJJbGd5UnByM2ZtX0swbk5hY1pfemItNUZ3M296OVFSc3RQWlVwSFhQTGZQcGxDZVZqZFN4WUxhNVR6NWotaHNVdk8xVl83TnlfNTN5MDlKOVZYZ1FrYXRxazVNQzIxcW9MREFQNjFZSENQeVpZQkJTUVh3amlJRUZuYTlib1I1eHhGRFFXSGcxa1l5bFRMTzQ2aUVHSUhwVTFrZ0hydzc0ZjhBeDYtREkya3ZuS0lIeEZiNXl0NFRqWmIyR2hud29WTA?oc=5（2026-10-09，news）
- [E-LIVE-NEWS-07] [lead] AXT 公告 2026-10-29 发布 Q3 2026 业绩（新闻线索） — https://news.google.com/rss/articles/CBMiywFBVV95cUxPZ2F1Q3BlcC1qQkM3bXNKTGtqTmZmYk1QaXhaQ1J4bXBCV2E0blNRQ2p2R252eWFweG1lZ1E0YVFHV0EtVUQ5eXlQUTZndGUxOEI1RW1MX2s3TlNERlB3dXM5bTlJb0FuenF4YjRwTGQxRXJFaTdDYlNOcVJHbTF5R0c5QVN6SWpQRjN0ZnVVcG02TzFwZm9uOElaenlkV05FRk5nc1l5ME5uYzEtTG96Zm1xWGtWWWJrUWRkMk5QajZ2dno1ajF5b0EwOA?oc=5（2026-10-01，news）
- [E-LIVE-NEWS-08] [lead] AXTI 被纳入 S&P 600（新闻线索，需以指数公司公告确认） — https://news.google.com/rss/articles/CBMikAFBVV95cUxQSzN5RGlpUGJSSzFVYVNDNjhIdkNBdG8yRFpQMm14aHQzaHg0R1N4WDg3YkttYTFJaG4zNFdDVUIzQm01UFlSQlBwelJ0eDNHYVBxNlFvRmhvUks0TXF2clh3Y09qUDRBZlFrNzhwdkI5SG8wLXZZd1hQUUlvVk5MdE5XSVRseVB6bHBBMHNwc2o?oc=5（2026-09-21，news）
- [ev:8k-lumentum-cra] 8-K 1.01：与 Lumentum 签 6 年 InP 衬底产能预留协议，首笔押金 4,350 万美元，2028 年第二笔 4,350 万美元，作为出货抵扣 — https://www.sec.gov/Archives/edgar/data/1051627/000143774926024883/axti20260715_8k.htm（2026-07-29，filing）
- [ev:8k-coherent-mdsa] 8-K 1.01：与 Coherent 签 3 年 6 英寸 InP 衬底开发供货协议，北京扩产 2026–2028，预付款 2,228.85 万美元，约定单价 — https://www.sec.gov/Archives/edgar/data/1051627/000143774926022557/axti20260630_8k.htm（2026-07-02，filing）
- [ev:8k-casela-lta] 8-K 1.01：通美与 Casela 签 2027 年 InP 衬底长协 1.73 亿元人民币（约 2,540 万美元），2026 年内全额预付，最低 80% 采购 — https://www.sec.gov/Archives/edgar/data/1051627/000143774926020978/axti20260615_8k.htm（2026-06-17，filing）
- [ev:8k-tongmei-hk] 8-K 2.04：子公司通美撤回科创板 IPO，转向香港上市并以 InP 业务为重点 — https://www.sec.gov/Archives/edgar/data/1051627/000143774926022984/axti20260629_8k.htm（2026-07-08，filing）
- [ev:8k-offering-2026-04] 8-K 1.01：包销增发 856 万股，每股 64.25 美元，毛额约 5.5 亿美元 — https://www.sec.gov/Archives/edgar/data/1051627/000121390026045867/ea0286957-8k_axt.htm（2026-04-21，filing）
- [ev:8k-offering-2025-12] 8-K 1.01：包销增发 710 万股，每股 12.25 美元，毛额约 8,700 万美元 — https://www.sec.gov/Archives/edgar/data/1051627/000121390025126296/ea0271065-8k_axtinc.htm（2025-12-30，filing）
- [ev:ser-2004577553714163817] Serenity 线索：铜转光子形成单点故障，InP 衬底高度集中（自写概括） — https://x.com/i/status/2004577553714163817（2025-12-26，social_lead）
- [ev:ser-2034981779447455793] Serenity 线索：看产能占比而非供应商数量；原料与衬底两层叠加（自写概括） — https://x.com/i/status/2034981779447455793（2026-03-20，social_lead）
- [ev:ser-2039261671739560026] Serenity 线索：只有把供给地位变现才有更高估值（自写概括） — https://x.com/i/status/2039261671739560026（2026-04-01，social_lead）
- [ev:ser-2043918867349811626] Serenity 线索：高纯红磷是 InP 衬底的上游瓶颈（自写概括） — https://x.com/i/status/2043918867349811626（2026-04-14，social_lead）
- [ev:ser-2053270948414099915] Serenity 线索：外延厂 CEO 公开称 InP 衬底短缺是 AI 基建瓶颈（自写概括） — https://x.com/i/status/2053270948414099915（2026-05-10，social_lead）
- [ev:ser-2058620094532718772] Serenity 线索：AXTI 覆盖原料/坩埚/前驱体，具备提价能力（自写概括） — https://x.com/i/status/2058620094532718772（2026-05-24，social_lead）

审计层：research_output `research:axti-2026-10-18`，bundle 校验 未运行

<!-- section:disclaimer -->
---
⚠️ 本报告由 suoha-serenity-skill 生成，仅用于回测与研究分析，非投资建议（not investment advice）。本 skill 根据 Serenity 公开发布的内容提炼研究框架；报告不代表 Serenity 本人观点。情景估值是“需要什么条件才成立”的假设推演，不是目标价或收益预测。Serenity 的帖子仅作为线索，未经核实不视为事实。

框架声明：本 skill 根据 Serenity 公开发布的内容提炼研究框架，用于回测与研究分析；报告由框架生成，不代表 Serenity 本人观点，亦非投资建议。

<!-- serenity-lens lens_id=lens:axti-2026-10-18 sha256=c7ecbed9d81413d4c7b871a01b7f6c268560002dbeeb4d174bec5ad0aef301ab -->

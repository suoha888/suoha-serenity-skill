# 研究包：MU（Micron Technology, Inc.）

> 数据抓取 2026-10-18T04:43:33Z · 连接器 v6.1.0 · 用时 1.56 秒。以下是数据底稿与机械线索，不是结论；判断写进 lens-draft.json 后用 `serenity_lens.py finish` 收尾。

## 1. 对比表（USD 用即期汇率，仅作横向比较）

| 代码 | 价格 | 市值(USD) | 52周回撤 | 1年涨跌 | TTM收入(USD) | 收入同比 | 收入环比 | 毛利率(期末) | 毛利率同比 | P/S | 股本变化 | 机械旗标 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `MU` | 878.84 USD | 994.34B | -30.0% | +334.4% | 133.19B | +379.3% | +30.8% | 86.8% (2026-09-03) | +42.1pp | 7.5x | +0.8% | pricing_power, acceleration, beneficial_owner_filings, insider_form4_activity, going_concern_exhibit_only |
| `000660.KS` | 1272000.0 KRW | 720.76B | -57.4% | +165.6% | 151.34B | +256.8% | +50.9% | 83.2% (2026-06-30) | +29.3pp | 4.8x | +2.6% | pricing_power, acceleration, drawdown |
| `005930.KS` | 215500.0 KRW | 998.64B | -42.5% | +121.0% | 388.22B | +130.0% | +28.1% | 69.6% (2026-06-30) | +35.4pp | 2.6x | -1.4% | pricing_power, acceleration |

## 2. 主体要点

- 最新季度收入：54.23B USD（期末 2026-09-03）；营业利润率 80.7%；现金+短投 43.43B；FCF 跑道 — 季。
- 计算市值：994.34B USD（878.84 × 1,131,423,212 股，股本截至 2026-10-02）。
- 文件雷达 `beneficial_owner_filings`（PB-SIG-09）：New 13G/13D filers = institutional discovery or activist; read filer name and %.
- 文件雷达 `insider_form4_activity`（PB-SIG-10）：Classify open-market buys (code P) vs sales/grants; buys after a run-up are rarer signals.
- SEC 全文检索命中（近 25 个月）：supply_concentration 11（主文档 4/6）；capacity_signal 17（主文档 4/6）；going_concern 4（主文档 0/4）

## 3. 一手文件关键词摘录

### 10-K（提交 2026-10-09，期末 2026-09-03）`E-LIVE-DOC-01`
来源：https://www.sec.gov/Archives/edgar/data/723125/000072312526000023/mu-20260903.htm

- **take_or_pay** ×5：…istributors. We maintain inventory at locations in close proximity to certain key customers to facilitate rapid delivery of products. Contracts with certain of our customers are short-term in duration. We also have strategic customer agreements structured as take-or-pay agreements, with binding commitments for specific contractually enforceable volumes over the multi-year contract terms. Pricing for our contracts is
- **remaining_performance_obligations** ×7：…t terms. Pricing for our contracts is either fixed or periodically negotiated, with the majority of the strategic customer agreements having pricing that is subject to minimum and maximum bands. As of September 3, 2026, the transaction price allocated to our remaining performance obligations was approximately $134 billion, of which $13 billion has been recognized as contract liabilities. Contract liabilities primari
- **customer_deposits** ×19：…is either fixed or periodically negotiated, with the majority of the strategic customer agreements having pricing that is subject to minimum and maximum bands. In connection with these customer agreements, we have received, and expect to continue to receive, customer deposits and letters of credit. Any failure to perform our obligations under these arrangements could subject us to contractual damages or other financ
- **sole_source** ×4：…supply for our materials and services. However, only a limited number of suppliers are capable of delivering certain materials, components, and services that meet our standards and, in some cases, materials, components, or services are provided by a single or sole source, and we may be unable to qualify new suppliers on a timely basis. The availability of materials or components, such as chemicals, silicon wafers, g
- **customer_concentration** ×1：…on, and $103 million, respectively. 93 | 2026 10-K Table of Contents Note 21. Certain Concentrations Our business units are based on market segments. See Note 20. Segment and Other Information for disclosure of disaggregated revenue by market segment. No customer accounted for 10% or more of total revenue in 2026. Revenue from one customer was 17% (primarily included in the CMBU segment) of total revenue for 2025. R
- **export_controls** ×8：…vely, new entrants into the memory and storage market could have a significant adverse impact on our competitive position. We operate in different jurisdictions than our competitors and may be impacted by unfavorable changes in currency exchange rates, import/export restrictions, and other trade regulations, including tariffs. In addition, governments have provided, and may continue to provide, significant assistanc
- **default_covenant** ×3：…intain letters of credit with third-party financial institutions. Our right to access such letters of credit is contingent upon the occurrence of specified events of default or breach by our customers. Letters of credit are not recognized as revenue unless an event of default or breach has occurred. The aggregate amount of letters of credit issued, or contractually committed to be issued, by third-party financial in

### 10-Q（提交 2026-06-25，期末 2026-05-28）`E-LIVE-DOC-02`
来源：https://www.sec.gov/Archives/edgar/data/723125/000072312526000015/mu-20260528.htm

- **take_or_pay** ×2：…ments, Note 17. Segment and Other Information for disclosure of disaggregated revenue by market segment. We recently executed certain strategic customer agreements, including agreements executed subsequent to May 28, 2026. These agreements are structured as take-or-pay agreements, with binding commitments for specific volumes over the multi-year contract terms and include contractually enforceable volumes. Pricing f
- **remaining_performance_obligations** ×6：…ly enforceable volumes. Pricing for most agreements is either fixed, or is subject to minimum and maximum pricing. A minority of the agreements do not have any fixed pricing or price bands, as pricing for those agreements is subject to market conditions. Our remaining performance obligations disclosure is based on minimum committed volumes and minimum pricing and is not expected to be indicative of future revenue un
- **customer_deposits** ×7：…ion of total unrecognized compensation costs for unvested awards, before the effect of any future forfeitures, was expected to be recognized through the third quarter of 2030, resulting in a weighted-average period of 1.2 years. Note 14. Revenue and Customer Contract Liabilities Revenue by Technology Quarter Ended Nine Months Ended May 28, 2026 May 29, 2025 May 28, 2026 May 29, 2025 DRAM $ 31,328 $ 7,071 $ 60,908 $ 
- **sole_source** ×2：…supply for our materials and services. However, only a limited number of suppliers are capable of delivering certain materials, components, and services that meet our standards and, in some cases, materials, components, or services are provided by a single or sole source, and we may be unable to qualify new suppliers on a timely basis. The availability of materials or components, such as chemicals, silicon wafers, g
- **export_controls** ×5：…oducts by third parties. These restrictions may not prohibit our competitors from selling similar products to our customers, which may result in a loss of sales and market share. Even as such restrictions are lifted, financial or other penalties or continuing export restrictions imposed with respect to our customers could have a continuing negative impact on our future revenue and results of operations, and we may n

## 4. 图谱位置与下一跳候选

- 链 `memory` / 节点 `hbm_dram`（HBM / 先进 DRAM，状态 now，类型 material）；同层：000660.KS, 005930.KS
  - 下一跳 `VECO` Veeco — 存储工序设备与 IP（filling，依据 serenity_lead）
  - 下一跳 `RMBS` Rambus — 存储工序设备与 IP（filling，依据 serenity_lead）
  - 下一跳 `ONTO` Onto Innovation — 存储工序设备与 IP（filling，依据 serenity_lead）
  - 下一跳 `6315.T` Towa — HBM 压缩成型（monopoly_not_bottleneck，依据 serenity_lead）

## 5. Serenity 公开言论记忆（时点）

- 状态：unavailable；No Serenity stance ledger supplied (--ledger). Silence in this pack is not a view.

## 6. 数据质量警告（写进 lens 的 live_data.warnings_addressed）

- `000660.KS`：sec_filings_not_applicable_non_us: read exchange filings (DART/MOPS/TDnet/RNS) for financing and contracts
- `005930.KS`：share_class_note_partial: Samsung Electronics preferred shares (005935.KS) are excluded; common-only value understates group equity.
- `005930.KS`：sec_filings_not_applicable_non_us: read exchange filings (DART/MOPS/TDnet/RNS) for financing and contracts

## 7. 下一步（快速路径）

1. 只在 brief 不够时再读一手文件：`python connectors/live_data.py filing-text --ticker X --latest 10-Q --preset contracts`（≤2 份）。
2. 填写 `lens-draft.json` 中所有 `TODO:` 字段（判断、情景、证伪条件、红队）。
3. `python scripts/serenity_lens.py finish lens-draft.json --md report.md --html report.html` 一步完成计算、校验、渲染与核验。

---

框架声明：本 skill 根据 Serenity 公开发布的内容提炼研究框架，用于回测与研究分析；报告由框架生成，不代表 Serenity 本人观点，亦非投资建议。

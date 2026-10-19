# 公司类型路由（v5）

> 不同类型的公司“卡点”在不同地方、该用的估值尺子也不同。`subject.company_type` 决定 Lens 的默认问题清单与尺子；agent 可以改，但要在 `tier_reason` 里说明为什么。

| `company_type` | 典型 | 先问什么 | 默认尺子 | 常见红旗 |
|---|---|---|---|---|
| `upstream_material` | 衬底、玻璃布、电子化学品、关键原料 | 有几家能做？认证周期多久？扩产要几年？ | `capacity_revenue` | 原料价格周期、单一客户 |
| `component_supplier` | 激光器、HBM、PCB、连接器、被动件 | 是否进入明星客户 BOM？份额与认证状态？ | `chokepoint_comparable` | 客户关系只是传闻、价格战 |
| `equipment_test` | 前/后道设备、测试量测 | 订单/积压、交期、客户资本开支指引 | `hypergrowth_forward` | 订单前置透支、出口管制 |
| `foundry_osat` | 晶圆代工、先进封装、封测 | 产能（片/月）、利用率、长约与预付款 | `capacity_revenue` | 资本开支过度、地缘 |
| `fabless_designer` | GPU/CPU/ASIC 设计 | 它被谁卡（代工/封装/HBM）？份额与客户集中度？ | `hypergrowth_forward` | 稀释（认股权证/股权激励）、代工单一来源 |
| `system_integrator` | ODM、机架、服务器 | 毛利率能否守住？是否只是“过路收入”？ | `hypergrowth_forward`（PE） | 低毛利、营运资金占用 |
| `infrastructure_power` | 电力设备、数据中心、散热 | GW 级订单、并网/场地、交期 | `capacity_revenue` | 项目延期、利率 |
| `hyperscaler_platform` | 云、模型平台 | 资本开支与回报、算力自给 | `hypergrowth_forward` | 资本开支回报下降 |
| `software_application` | 软件 | 用量与定价权是否受 AI 驱动 | `hypergrowth_forward`（PS） | 增速放缓但按高增长定价（PB-RED-04） |
| `value_cyclical` | 周期底部的老牌公司 | 账面价值、现金、周期位置、催化剂 | `deep_value` | 价值陷阱 |
| `other` | 其他 | 先归类再研究；无法归类时降级为 amber | 视情况 | — |

## 路由规则

1. **大型下游公司（市值远大于其上游）**：默认把它当作 `downstream_reference` 锚点，`red_team.better_alternative` 必须指向一个上游节点；例见 `examples/amd-serenity-lens.json`。
2. **小市值上游公司**：重点是 `pre_institutional` 与 `cheap_derisked` 两道闸门，以及 PB-RED-01（稀释）。
3. **跨市场标的**：先用 `scripts/ticker_normalizer.py` 解析代码与币种，`subject.currency` 必须与报价币种一致（validate 强制）。

## 公司体检的类型路由（v7.1，`scripts/company_check.py`）

`company_type`（上表）描述的是“它在产业链里是什么”；公司体检另有一层**财务类型**路由，决定哪些指标有意义。任何 A 股、港股、美股公司都能跑，不要求在卡点图谱里。

| 财务类型 | 判定依据（按顺序） | 跳过 | 加看 |
|---|---|---|---|
| `bank` 银行 | 聚合源 `org_type`/行业含“银行”；SEC SIC 6000–6199 | 毛利率、经营现金流/净利、资产负债率、营运资金 | 不良率（S1）、拨备覆盖率（S2）、核心一级资本充足率（S3）、P/B |
| `insurer` 保险 | “保险”；SIC 6300–6419 | 同上 | ROE、P/B；内含价值需读年报 |
| `broker` 券商 | “证券”；SIC 6200–6299 | 同上 | ROE、P/B |
| `financial_other` | “多元金融”；SIC 6700–6799 | 同上 | ROE、P/B |
| `real_estate` / `reit` | “房地产”；SIC 6500–6599 / REIT 6798 | 资产负债率只作参考（info） | 净现金、商誉、合同负债 |
| `utility` | “电力/燃气/水务”；SIC 4900–4999 | 资产负债率只作参考 | 现金流、股息率 |
| `general` | 以上都不是 | — | 全部检查 |

检查项与阈值（`RULES`，watch / flag）：

| 编号 | 指标 | watch | flag | 说明 |
|---|---|---|---|---|
| G1 / G1q | 收入同比（累计 / 单季） | < 0% | < −10% | A/H 用最新报告期累计同比，美股用最新季度同比 |
| G2 | 归母净利同比 | < 0% | < −20% | 美股为 TTM 对一年前 TTM，上年亏损时不算 |
| G3 | 非经常性损益占净利 | > 20% | > 50% | 仅 A 股（扣非净利） |
| P1d | 毛利率同比变化 | < −3pp | < −8pp | 非金融 |
| P3 | ROE（TTM 归母净利 / 期末归母权益） | < 8% | < 3% | 未取平均权益 |
| C1 | 经营现金流 / 净利润（TTM） | < 0.7 | < 0.3 | 净利为负时只作 info |
| C3 | SBC / 收入（TTM） | > 10% | > 20% | 美股 |
| B1 | 资产负债率 | > 70% | > 85% | 地产/公用事业只作 info |
| B2 | 商誉 / 归母权益 | > 30% | > 50% | |
| W1 / W2 | 应收 / 存货增速 − 收入增速 | > 20pp | > 50pp | 该项不足 TTM 收入 5% 时只作 info |
| W3 | 合同负债同比 | < −15% | < −40% | 不足 TTM 收入 1% 时只作 info |
| D1 | 股本变化（约一年） | > 5% | > 10% | 稀释 |
| D2 | 股权质押比例 | > 15% | > 30% | 仅 A 股（中国结算） |
| S1 / S2 / S3 | 不良率 / 拨备覆盖率 / CET1 | 1.8% / <180% / <9.5% | 3% / <150% / <8% | 仅银行 |

估值统一在**报告币种**下计算：价格 × 报表总股本（A+H 公司用全部股本，按本线价格），港股报告币种与上市币种不同时用 Yahoo 汇率换算；P/E 与腾讯行情的 PE 交叉核对（>25% 差异只是提示，口径常不同）。所有状态只是“该去看什么”，不是买卖结论；flag/watch 会在 `pack` 的 lens 草稿里变成待核实的红旗（`company_check_<编号>`）。

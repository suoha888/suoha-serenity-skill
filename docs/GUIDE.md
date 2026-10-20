# 使用手册

[← 返回首页](../README.md)

suoha-serenity-skill 是一个给 AI 用的股票研究 Skill：把 Serenity 公开推文里的卡脖子理论整理成可执行的研究流程，配合官方数据，帮你研究任意一只 A 股、港股或美股。

- [安装](#安装)
- [直接对 AI 说](#直接对-ai-说)
- [命令行用法](#命令行用法)
- [一份研究报告包含什么](#一份研究报告包含什么)
- [数据来源](#数据来源)
- [常见问题](FAQ.md)
- [声明](#声明)

## 安装

需要 Git 和 Python 3.10+。核心功能只用 Python 标准库，**不需要任何 API Key**。

**一键安装**（自动检测 Claude Code、Codex，安装后自动校验；已有旧版本会先备份）：

~~~bash
# macOS / Linux
git clone https://github.com/suoha888/suoha-serenity-skill.git && cd suoha-serenity-skill && ./install.sh

# Windows（PowerShell）
git clone https://github.com/suoha888/suoha-serenity-skill.git; cd suoha-serenity-skill; .\install.ps1
~~~

指定安装位置：`./install.sh claude|codex|agents|all`，Windows 用 `.\install.ps1 -Target all`。

**手动安装**（PowerShell 执行策略拦截脚本时使用，不必关闭安全策略）：

~~~powershell
$skillTarget = "$HOME\.agents\skills\suoha-serenity-skill"
python scripts/build_runtime.py --source . --output $skillTarget
python scripts/verify_runtime.py --source . --runtime $skillTarget
~~~

已有安装时加 `--replace`，旧版本会保留在 `.runtime-backups`。

**更新**：在克隆目录运行 `git pull --rebase`，再重新执行安装命令。

## 直接对 AI 说

安装后，在支持 Skills 的 AI 客户端（Claude Code、Codex 等）里直接说：

| 你说 | 你会得到 |
|---|---|
| 用 suoha-serenity-skill 讲讲 Serenity 的卡脖子理论 | 理论要点 + 历史案例 |
| 用 suoha-serenity-skill 体检 600519，先给结论再给证据 | 财务体检：哪里正常、哪里要留意、有没有红旗 |
| 用 suoha-serenity-skill 研究腾讯（00700）的供应链卡点 | 一份完整研究报告：结论、证据、风险 |
| 用 suoha-serenity-skill 看看 NVDA 有没有财务红旗 | 逐项检查结果，每项附公式 |

股票可以用代码，也可以直接用名称，比如“贵州茅台”“騰訊”“苹果”。

## 命令行用法

所有功能都通过一个入口 `suoha.py` 使用，出错时会给出中文修复提示。

~~~bash
python suoha.py doctor                    # 环境自检（加 --online 测试数据连接）
python suoha.py resolve 腾讯 比亚迪 苹果    # 名称 → 标准代码（含 A+H、港美两地上市）
python suoha.py check 600519              # 公司体检：成长、盈利、现金、负债、股东、估值
python suoha.py research MU               # 研究包：实时数据 + 公告 + 同链对比 + 报告草稿
python suoha.py finish work/mu-<日期>/lens-draft.json   # 复算、校验，生成 HTML + Markdown 报告
python suoha.py exchange 300308.SZ        # 交易所原生数据：公告、旗标、第二行情
~~~

**公司体检**（`check`）会先判断公司类型（银行、保险、券商、地产、公用事业、一般企业），再逐项检查。结果分三类：✅ 正常、👀 需要留意、🚩 财务红旗，每个数字都附公式和阈值。红旗是“该去核实什么”，不是买卖结论。

**研究报告**（`research` → `finish`）：`research` 准备好数据和草稿 `lens-draft.json`，由 AI 把所有 `TODO:` 换成判断；`finish` 会拒绝未完成的草稿，并用脚本复算所有数字后再出报告。

## 一份研究报告包含什么

~~~text
资本开支确定性 → 多层卡点地图（含上游）→ 卡点中的卡点
→ 三道闸门：真瓶颈 / 机构是否已发现 / 是否便宜且风险可控
→ 悲观 / 基准 / 乐观三种假设 → 先行信号 → 财务红旗
→ 反方观点与最大风险 → 可检验的证伪条件 → 结论：绿 / 黄 / 红
~~~

报告固定区分四件事：瓶颈是否成立、公司占据哪一环、能否赚到钱、市场是否已经反映。不是每只股票都有卡点，也不是每只都被低估。

- 每条规则引用 [理论全书](../references/serenity-doctrine.md) 和 [方法手册](../references/serenity-playbook.md) 里的编号，只附帖子编号，不转载原文。规则提炼自 2025-07 至 2026-10 的 7,153 条公开推文。
- 每条证伪条件会标上“兑现与失效”规则编号（PB-EXIT），说明它触发后论点是失效、降级、重新立论还是已经兑现；宏观回调、内部人卖出等噪音会明确写“不构成失效”。
- 想知道某只股票在哪条产业链上：`python scripts/atlas.py ticker NBIS`（[卡点地图](../references/chokepoint-atlas.md)，10 条链、46 个节点）。
- 市值、隐含市值、涨跌空间等数字全部由脚本计算，不靠手写。
- 示例报告（方法演示，非投资建议）：[MU](../examples/mu-serenity-report.html) · [AMD](../examples/amd-serenity-report.html) · [AXTI](../examples/axti-serenity-report.html)

## 数据来源

联网只发生在 `connectors/`：只读、HTTPS、只访问白名单网站。

| 市场 | 数据源 | 内容 |
|---|---|---|
| 美股 | SEC EDGAR、XBRL、全文检索 | 财务、股本、增发/融资公告、10-K/10-Q 摘录 |
| A 股 | 巨潮资讯 + 腾讯行情 + 东方财富 | 公告与风险旗标、近 9 期财务、TTM、资产负债表、股权质押、分红 |
| 港股 | 披露易 + 腾讯行情 + 东方财富 | 公告与风险旗标、近 10 期财务、TTM、资产负债表、股息、A+H 溢价 |
| 日本 | TDnet；EDINET（可选免费密钥） | 适时披露、法定文件 |
| 台湾 | TWSE / TPEx | 月营收（早于季报） |
| 韩国 | DART（可选免费密钥） | 公告 |

代码库收录全部 A 股、港股和 SEC 登记的美股代码。部分数字来自聚合源，关键结论请以巨潮、披露易或 SEC 原文为准。

## 声明

本项目由 X 博主 **梭哈.AI**（[@suoha_AI](https://x.com/suoha_AI)）设计和维护。

研究方法提炼自 Serenity 公开发布的推文，只引用帖子编号，不含推文原文。报告由框架生成，**不代表 Serenity 本人观点，也不构成投资建议**。

更多：[数据政策](DATA_POLICY.md) · [第三方声明](THIRD_PARTY_NOTICES.md) · [架构说明](ARCHITECTURE.md) · [更新日志](CHANGELOG.md) · License：[MIT](../LICENSE)

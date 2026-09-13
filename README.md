<div align="center">

# suoha-serenity skill

### Evidence-first supply-chain and company research compiler

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-black)](SKILL.md)

</div>

面对一个热门投资叙事，最难的通常不是找到更多股票，而是判断应该先研究产业链哪一层、哪些证据真正成立、什么事实会让原判断失效。

suoha-serenity skill 把这种问题变成可重复、可审计的研究流程：

~~~text
市场叙事 -> 系统变化 -> 架构必要性 -> 产业链关系
-> 13 维 BottleneckAssessment 与 7 种产能状态
-> 公司画像/暴露/价值捕获/资本结构与 MarketSnapshot
-> 经济传导与估值语境 -> 六级验证梯与反身性审计
-> 预期差与条件化研究理由 -> 证据与反证
-> thesis 生命周期 -> 优先研究清单 -> 下一步核验
~~~

它是独立的公开方法论项目，灵感来自 Serenity / @aleabitoreddit 的公开可观察研究路径，不代表对其本人、私有内容或投资观点的复制、背书或关联。

## 核心能力

- 先研究系统和瓶颈，再讨论 ticker。
- 先验证架构是否真的绕不开，再把供应商集中度、替代性、认证、扩产、客户
  紧迫性、产能可见度、定价权、价值捕获、良率、商用/自用产能、地理/监管和
  资本强度分开评估，不把它们压成一个总分。
- 把供应链 edge 记录为上游、产品/工艺、下游依赖、关系类型、有效期、证据、
  反证和替代路径，而不是把产品提及当成客户关系。
- 将名义、安装、可用、合格、商用、自用和可获得产能分开，阻止“扩产公告”
  直接变成收入预测。
- 公司研究输出强制包含 CompanyProfile 和 MarketSnapshot：ticker、交易所、
  币种、股价、市值、股本、主营、收入结构、客户、地区、竞争格局、财务质量
  和风险，并为每个字段保留 as_of 与来源。
- 将直接产业链暴露、公司价值捕获和融资/稀释拆成三个独立判断。
- 将“市场可能低估了什么”写成有市场代理、有机制、有证据、有反证的
  variant-perception 假设。
- 输出架构必要性、物理供给、客户验证、公司捕获、财务传导、市场预期六级
  validation ladder，并审计社交信息是否先于价格变化。
- 将“为什么值得进一步研究”写成 IF/THEN/BECAUSE/CONFIRM/FAIL 条件，
  不输出自动买卖指令、目标价或收益承诺。
- 把 FACT、INFERENCE、HYPOTHESIS、UNKNOWN 与证据状态分开。
- 对每条重要判断保留来源、时间、哈希和抽取版本。
- 显式寻找替代解释、反方证据和失效条件。
- 用 dated thesis events 保存建立、强化、减弱、修正、反转和失效。
- 支持美股、港股、A 股、台股、日股、韩股和欧洲市场的来源路由。
- 将历史资料蒸馏成可复核的 context、claim、evidence、event 和 method-card candidates。

研究排序不是买卖建议。项目不执行交易、不访问钱包或券商、不预测收益、不承诺回报。

## 安装

机器可用的 Skill 名称是 suoha-serenity-skill；用户界面显示名称是 suoha-serenity skill。

~~~powershell
$skill = "$HOME\.agents\skills\suoha-serenity-skill"
New-Item -ItemType Directory -Force $skill | Out-Null
Copy-Item -Recurse -Force SKILL.md,LICENSE,references,kernel,contracts,schemas,adapters,assets,examples,scripts,agents $skill
~~~

在项目内使用时，建议由 source 目录执行 scripts/build_runtime.py，生成 runtime 和客户端部署副本。不要直接编辑部署副本。
当前发布版本为 v4；唯一可编辑副本是 source/suoha-serenity-skill。

## 本地历史资料蒸馏

脚本只读取已经标准化的 JSONL，不读取原始档案，不联网，不调用远程模型；存在冻结
holdout 时，默认不把它纳入研究派生层：

~~~powershell
python scripts/distill_archive.py --data-root ..\..\data\serenity --partition public --output-root ..\..\data\serenity\derived\public --replace
python scripts/distill_archive.py --data-root ..\..\data\serenity --partition subscription --output-root ..\..\data\serenity\derived\subscription --replace
~~~

输出分别位于 data/serenity/derived/public 和 data/serenity/derived/subscription。订阅内容及其所有衍生对象都只能留在本地私有层；候选 method card 在人工复核前不是权威方法。

建立本地检索索引：

~~~powershell
python scripts/build_local_index.py --data-root ..\..\data\serenity --partition all
python scripts/build_local_index.py --data-root ..\..\data\serenity --query bottleneck --access-level public --as-of 2026-09-02T23:59:59Z
~~~

JSONL 是标准数据格式，SQLite + FTS5 只是可重建的本地查询层。
索引默认排除冻结 holdout；--include-holdout 只用于隔离的 evaluator 查询。

## 运行检查

~~~powershell
python scripts/validate_skill.py . --strict
python scripts/run_evals.py --root . --data-root ..\..\data\serenity --runtime-root ..\..\runtime\suoha-serenity-skill --report ..\..\data\serenity\reports\v4-automated-eval.json
~~~

自动化检查覆盖结构、脚本语法、网络依赖、public/subscription 分区、来源 lineage、时间 holdout、运行副本漂移、Company ResearchOutput 合约和评测 fixture。它不能替代人工研究质量评估、法律审查或真实来源的事实核验。

## 公开与私有边界

公开仓库只放代码、schema、契约、抽象方法、合成样例和评测 harness。不要提交原始推文档案、批量截图、subscription 正文、subscription 摘要、可逆衍生物、私有笔记或 outcome 标签。

参见：

- [ARCHITECTURE_V4.md](ARCHITECTURE_V4.md)
- [ARCHITECTURE_V3.md](ARCHITECTURE_V3.md)（历史 v3 架构）
- [ARCHITECTURE_V2.md](ARCHITECTURE_V2.md)（历史 baseline）
- [DATA_POLICY.md](DATA_POLICY.md)
- [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
- [references/distillation-playbook.md](references/distillation-playbook.md)
- [references/advanced-bottleneck-diagnostics.md](references/advanced-bottleneck-diagnostics.md)
- [references/benchmark-protocol.md](references/benchmark-protocol.md)
- [references/security-operations.md](references/security-operations.md)

## License

代码和本项目拥有授权的文档采用 MIT。第三方社交内容、图片、商标、付费资料和用户自有档案不因本仓库的 LICENSE 自动获得 MIT 授权。

<div align="center">

# suoha-serenity skill

### Evidence-first, time-aware supply-chain research for investment agents

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-black)](SKILL.md)

</div>

面对一个热门投资叙事，最难的通常不是找到更多股票，而是判断应该先研究产业链哪一层、哪些证据真正成立、什么事实会让原判断失效。

suoha-serenity skill 把这种问题变成可重复的研究流程：

~~~text
市场叙事 -> 系统变化 -> 产业链层级 -> 物理瓶颈
-> 经济传导 -> 公司候选 -> 证据与反证
-> thesis 生命周期 -> 优先研究清单 -> 下一步核验
~~~

它是独立的公开方法论项目，灵感来自 Serenity / @aleabitoreddit 的公开可观察研究路径，不代表对其本人、私有内容或投资观点的复制、背书或关联。

## 核心能力

- 先研究系统和瓶颈，再讨论 ticker。
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
python scripts/run_evals.py --root . --data-root ..\..\data\serenity --runtime-root ..\..\runtime\suoha-serenity-skill --report ..\..\data\serenity\reports\v2-automated-eval.json
~~~

自动化检查覆盖结构、脚本语法、网络依赖、public/subscription 分区、来源 lineage、时间 holdout、运行副本漂移和评测 fixture。它不能替代人工研究质量评估、法律审查或真实来源的事实核验。

## 公开与私有边界

公开仓库只放代码、schema、契约、抽象方法、合成样例和评测 harness。不要提交原始推文档案、批量截图、subscription 正文、subscription 摘要、可逆衍生物、私有笔记或 outcome 标签。

参见：

- [ARCHITECTURE_V2.md](ARCHITECTURE_V2.md)
- [DATA_POLICY.md](DATA_POLICY.md)
- [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
- [references/distillation-playbook.md](references/distillation-playbook.md)
- [references/benchmark-protocol.md](references/benchmark-protocol.md)
- [references/security-operations.md](references/security-operations.md)

## License

代码和本项目拥有授权的文档采用 MIT。第三方社交内容、图片、商标、付费资料和用户自有档案不因本仓库的 LICENSE 自动获得 MIT 授权。

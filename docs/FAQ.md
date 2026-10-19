# 常见问题 / FAQ

## 这是什么，能做什么、不能做什么？

suoha-serenity-skill 是给 AI 使用的研究方法和 Python 工具：判断供应链卡点、公司能否捕获价值，检查成长、盈利、现金、负债及估值。输入代码或名称即可开始。体检红旗是待核实线索，不是自动买卖结论；不执行交易、不承诺收益，也不证明完整复原了 Serenity 的理论。

English: Research workflow and financial screens, not trading or guaranteed returns.

## 环境和 API Key？

需要 Git、Python 3.10+ 和可联网环境；核心功能仅用 Python 标准库，不需要 API Key，也不需要 OPENAI_API_KEY。AI 客户端本身的账户或订阅由客户端决定。日本 EDINET / 韩国 DART 的扩展接口可选配免费 key；SEC_USER_AGENT 是建议提供的联系标识，不是 API Key。Windows 没有 IANA 数据时，对 1992 年起的受支持亚洲市场使用固定时差；更早的历史时间需要系统时区数据。

安装方式见 [首页](../README.md#安装3-步)。PowerShell 执行策略阻止脚本时，可使用 [使用手册](GUIDE.md#安装) 的 Python 手动安装，不必关闭安全策略。更新使用 git pull --rebase 后重新安装；遇到本地改动先备份，不要强制覆盖。

English: Git and Python 3.10+, standard library only. No API key for core features.

## 支持哪些市场？

通用体检重点支持 A 股、港股、美股，例：600519 / 00700 / AAPL。用 `python suoha.py resolve 腾讯` 查询代码；存在多个上市地时明确选择。其他市场有部分交易所公告或收入数据，覆盖并不等同。任意公司指入口不局限于图谱里的公司，不代表所有上市公司、全部指标始终可用。

English: A-share, HK and US checks; other markets have partial connector coverage.

## 仓库有没有推文原文？

没有。方法来自 Serenity 公开推文的研究框架提炼，理论引用只给帖子编号，不转载原文。报告不代表 Serenity 本人观点。订阅正文、私有档案及其衍生内容不应上传；提交反馈时也不要附带这些内容、账号密码或 API 密钥。

English: No tweet text; post IDs only. Reports do not represent Serenity's own views.

## 数据从哪来，出错怎么办？

美国申报数据来自 SEC；A 股/港股公告来自巨潮和披露易。行情及部分财务也来自 Yahoo、腾讯和东方财富等聚合源，并非所有数据都是官方数据。保留来源、日期和警告，并以公司申报文件复核关键结论。限流、延迟或字段变化时，稍后重试并检查网络/代理，不要把缺失当成零或当成低风险。

```sh
python suoha.py doctor
python suoha.py doctor --online --ticker 600519
python suoha.py check AAPL --debug
```

doctor 默认离线检查环境和安装文件；`--online` 才测试数据连接，`--ticker` 检查指定代码。它不能证明全部来源可用或数据准确。普通错误给出中英提示；`--debug` 保留诊断详情，公开贴出前请删除私人路径和敏感信息。

English: Official filings plus aggregators. Retry transient failures; inspect warnings and verify filings.

## 如何反馈？

[提交实测反馈](https://github.com/suoha888/suoha-serenity-skill/issues/new?template=field-test.yml)：填写市场、代码、版本、命令或提示词、实际和预期结果，附脱敏输出。不需要上传完整私人研究包。

English: Include ticker, version, command/prompt, expected/actual result and redacted output.

本工具仅供研究，不构成投资建议。

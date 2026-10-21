#!/usr/bin/env python3
"""suoha — one command for the whole suoha-serenity skill workflow.

本项目由 X 博主 梭哈.AI（@suoha_AI）设计和维护。

  python suoha.py doctor [--online]          环境自检（Python、文件、代码真值表、可选联网）
  python suoha.py research MU                一键研究包：实时数据 + 交易所公告 + 同链对比 + lens 草稿
  python suoha.py finish work/mu/lens-draft.json   计算、校验并生成研究报告
  python suoha.py check 贵州茅台             通用公司体检（A 股/港股/美股任意公司：成长/盈利/现金/负债/股东/估值）
  python suoha.py resolve 腾讯 比亚迪 苹果     名称/代码 → 标准代码（含 A+H、港美两地上市线）
  python suoha.py exchange 300308.SZ         非美股交易所原生数据（公告/旗标/第二行情/台股月营收）
  python suoha.py etf [--refresh]            ETF 覆盖审计（非共识卡点 / 图谱缺口）
  python suoha.py truth [--refresh]          代码真值表（名称/币种/交易所）构建与校验
  python suoha.py update <args>              Serenity 私有档案更新（转交 scripts/serenity_update.py）

Everything here shells out to the scripts in scripts/ and connectors/; this
file adds no network code of its own. Research only, not investment advice.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
LIVE = ROOT / "connectors" / "live_data.py"
S = ROOT / "scripts"
ETFS = ("SMH", "SOXX", "XSD", "PSI")
DEBUG = False
MESSAGES = {
    "python": ("需要 Python 3.10+；请升级 Python 后重试。", "Python 3.10+ is required; upgrade Python and retry."),
    "network": ("网络或数据源暂不可用；稍后重试，并检查网络、代理。", "Network/data source unavailable; retry later and check your connection/proxy."),
    "ticker": ("无法识别股票；用 python suoha.py resolve <名称> 查询。示例：600519.SS / 0700.HK / AAPL。", "Ticker unresolved; run python suoha.py resolve <name>. Examples: 600519.SS / 0700.HK / AAPL."),
    "usage": ("缺少文件或参数，或参数无效；运行 python suoha.py --help 查看用法，安装不完整请重新安装。", "Missing files/arguments or invalid options; run python suoha.py --help, or reinstall an incomplete package."),
    "lens": ("lens 未通过校验：按上面的 ERROR 行逐条修改 lens 文件后重新运行 finish。", "Lens failed validation: fix each ERROR line above in the lens file and rerun finish."),
    "internal": ("操作未完成；加 --debug 查看详情，并通过 FAQ 中的反馈入口报告问题。", "Operation failed; add --debug for details and report through the FAQ feedback link."),
}

class FriendlyError(Exception):
    def __init__(self, kind):
        self.kind = kind
        super().__init__(kind)

def explain(kind):
    for line in MESSAGES.get(kind, MESSAGES["internal"]):
        print(line, file=sys.stderr)

class FriendlyParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        raise FriendlyError("usage")

def normalized_ticker(raw, hint=""):
    if str(S) not in sys.path:
        sys.path.insert(0, str(S))
    from ticker_normalizer import normalize, load_aliases, SEED_PATH
    result = normalize(raw, load_aliases([SEED_PATH]), hint)
    if not result.get("symbol"):
        raise FriendlyError("ticker")
    return result["symbol"]
HINTS = {
    "network": "联网失败：稍后重试，检查网络/代理。SEC_USER_AGENT 是可选联系标识；不需要 API Key。",
    "lens": "lens 校验未通过：按上面列出的字段补齐（所有 TODO: 必须替换成判断），再运行一次。",
    "truth": "代码真值表报错：图谱/报告里的公司名或币种与官方不符，先核实代码是否写错。",
}


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def run(args: list[str], hint: str | None = None, check: bool = True) -> int:
    def rel(x: object) -> str:
        if isinstance(x, Path) and x.is_absolute():
            try:
                return str(x.relative_to(ROOT))
            except ValueError:
                return str(x)
        return str(x)
    args = [args[0]] + [rel(x) for x in args[1:]]
    print("$ python " + " ".join(args[1:]), flush=True)
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    result = subprocess.run([str(a) for a in args], cwd=ROOT, env=env,
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    code = result.returncode
    if not code or DEBUG:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
    # Several connectors return an unavailable JSON block with exit code zero.
    if not code:
        try:
            payload = json.loads(result.stdout)
            if isinstance(payload, dict) and payload.get("status") in ("unavailable", "error"):
                code = 1
        except (ValueError, TypeError):
            pass
    if code and check and hint == "lens" and not DEBUG:
        # v8.1: validation errors are the user's to fix, so show them instead of a generic "internal" message
        lines = [ln for ln in (result.stdout + "\n" + result.stderr).splitlines() if ln.startswith(("ERROR", "WARN", "TODO"))]
        for ln in lines[:40]:
            print(ln, file=sys.stderr)
        if not lines:
            hint = None
    if code and check:
        kind = "usage" if "FileNotFoundError" in result.stderr else (hint if hint in MESSAGES else "internal")
        explain(kind)
    return code


def atlas_tickers() -> list[str]:
    atlas = json.loads((ROOT / "assets" / "chokepoint-atlas.json").read_text(encoding="utf-8"))
    return sorted({h["ticker"] for c in atlas["chains"] for n in c["nodes"] for h in n.get("holders", [])})


def cmd_doctor(a: argparse.Namespace) -> int:
    ok = True

    def line(good: bool, text: str, fix: str = "") -> None:
        nonlocal ok
        ok &= good
        print(("✅ " if good else "❌ ") + text + ("" if good or not fix else f"\n   → {fix}"))
    v = sys.version_info
    line(v >= (3, 10), f"Python {platform.python_version()}", "需要 Python 3.10 或更高版本")
    for rel in ("SKILL.md", "connectors/live_data.py", "connectors/venues.py", "assets/chokepoint-atlas.json",
                "assets/ticker-truth.json"):
        line((ROOT / rel).is_file(), f"文件 {rel}", "安装不完整：重新下载或 git pull")
    for rel in ("scripts/ticker_truth.py", "scripts/atlas.py",
                "scripts/ticker_normalizer.py", "scripts/company_check.py", "assets/ticker-aliases.seed.json",
                "assets/universe/cn.json", "assets/universe/hk.json", "assets/universe/us.json"):
        line((ROOT / rel).is_file(), f"文件 {rel}")
    if not ok:
        explain("usage")
        return 1
    if getattr(a, "ticker", None):
        print("Ticker:", normalized_ticker(a.ticker))
    line(run([PY, S / "ticker_truth.py", "check"], check=False) == 0, "代码真值表", HINTS["truth"])
    line(run([PY, S / "atlas.py", "validate"], check=False) == 0, "卡点图谱结构")
    print(("✅ " if os.environ.get("SEC_USER_AGENT") else "⚠️  ") + "SEC_USER_AGENT " +
          ("已设置" if os.environ.get("SEC_USER_AGENT") else "未设置（美股文件可用默认标识，但建议设置：export SEC_USER_AGENT=\"名字 邮箱\"）"))
    for key, what in (("EDINET_API_KEY", "日本 EDINET 法定文件"), ("DART_API_KEY", "韩国 DART 公告")):
        print(("✅ " if os.environ.get(key) else "ℹ️  ") + f"{key} " + ("已设置" if os.environ.get(key) else f"未设置（可选，免费注册后启用{what}）"))
    if a.online:
        line(run([PY, LIVE, "quote", "MU"], check=False) == 0, "联网：Yahoo 行情", HINTS["network"])
        line(run([PY, LIVE, "exchange", "0700.HK", "--days", "30"], check=False) == 0, "联网：HKEXnews + 腾讯行情", HINTS["network"])
        if not ok:
            explain("network")
    else:
        print("联网未检查 / Network not checked: python suoha.py doctor --online")
    print("\n" + ("🎉 一切正常。下一步：python suoha.py research MU" if ok else "⚠️  有项目未通过，按上面的提示处理。"))
    return 0 if ok else 1


def cmd_research(a: argparse.Namespace) -> int:
    out = a.out_dir or f"work/{a.ticker.lower().replace('.', '-')}-{today()}"
    args = [PY, LIVE, "pack", a.ticker, "--out-dir", out]
    for flag, val in (("--peers", a.peers), ("--adr-ratio", a.adr_ratio), ("--ledger", a.ledger), ("--news-query", a.news_query)):
        if val is not None:
            args += [flag, val]
    code = run(args, "network")
    if not code:
        print(f"\n✅ 研究包已生成：{out}/brief.md（先读）与 {out}/lens-draft.json（把所有 TODO: 换成判断）。"
              f"\n下一步：python suoha.py finish {out}/lens-draft.json")
    return code


def cmd_check(a: argparse.Namespace) -> int:
    a.ticker = normalized_ticker(a.ticker)
    stem = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in a.ticker.lower())
    snap = (Path(a.out) if a.out else ROOT / "work" / f"check-{stem}-{today()}.json").resolve()
    snap.parent.mkdir(parents=True, exist_ok=True)
    args = [PY, LIVE, "snapshot", a.ticker, "--no-fts", "--no-news", "--out", snap]
    if a.yahoo:
        args += ["--yahoo", a.yahoo]
    code = run(args, "network")
    if code:
        return code
    data = json.loads(snap.read_text(encoding="utf-8"))
    from company_check import extract
    summary = extract(data)
    if (data.get("quote") or {}).get("status") != "ok" or not any(
        summary.get(key) is not None for key in ("revenue_ttm", "profit_ttm", "total_assets", "profit_period")
    ):
        explain("network")
        print(f"诊断快照 / Diagnostic snapshot: {snap}", file=sys.stderr)
        return 1
    md = snap.with_suffix(".md")
    code = run([PY, S / "company_check.py", snap, "--md", md, "--json", snap.with_name(snap.stem + "-check.json")])
    if not code:
        print(md.read_text(encoding="utf-8"))
        result = json.loads(snap.with_name(snap.stem + "-check.json").read_text(encoding="utf-8"))
        if result.get("data_status") == "insufficient":
            print("\n⚠️ 数据不足：可打分项目太少，0 个红旗不代表公司“干净”。请补充定期报告数据后再判断。")
        print(f"\n✅ 体检已保存：{md}（数据快照 {snap}）。状态只是“该去看什么”，不是买卖结论。")
    return code


def cmd_finish(a: argparse.Namespace) -> int:
    code = run([PY, S / "serenity_lens.py", "finish", a.lens], "lens")
    if not code:
        print("\n✅ 报告已生成。")
    return code


def cmd_etf(a: argparse.Namespace) -> int:
    if a.refresh:
        for etf in ETFS:
            if run([PY, LIVE, "etf-holdings", etf, "--out", f"work/etf-{etf}.json"], "network"):
                return 1
            raw = json.loads((ROOT / f"work/etf-{etf}.json").read_text(encoding="utf-8"))
            if raw.get("status") != "ok":
                print(f"⚠️ {etf}: {raw.get('error')}")
                continue
            keep = {k: raw.get(k) for k in ("etf", "fund", "registrant", "series_id", "period_end", "filed", "net_assets_usd", "source_url", "note")}
            keep["holdings"] = [{k: h.get(k) for k in ("name", "isin", "cusip", "pct", "country", "asset_cat")}
                                for h in raw["holdings"] if h.get("asset_cat") in (None, "EC")]
            (ROOT / "assets" / "etf-holdings" / f"{etf}.json").write_text(json.dumps(keep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return run([PY, S / "etf_audit.py", "--md", "work/etf-audit.md"])


def cmd_truth(a: argparse.Namespace) -> int:
    if a.refresh:
        snaps = f"work/truth-{today()}"
        tickers = sorted(set(atlas_tickers()))
        if run([PY, LIVE, "batch", *tickers, "--out-dir", snaps], "network"):
            return 1
        if run([PY, S / "ticker_truth.py", "build", "--snapshots", snaps]):
            return 1
    return run([PY, S / "ticker_truth.py", "check"], "truth")


def dispatch(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles
        sys.stderr.reconfigure(encoding="utf-8")
    ap = FriendlyParser(prog="suoha.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--debug", action="store_true", help="show full diagnostic tracebacks")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("doctor", help="环境自检"); p.add_argument("--online", action="store_true"); p.add_argument("--ticker")
    p = sub.add_parser("research", help="一键研究包"); p.add_argument("ticker"); p.add_argument("--peers"); p.add_argument("--out-dir")
    p.add_argument("--adr-ratio"); p.add_argument("--ledger"); p.add_argument("--news-query")
    p = sub.add_parser("finish", help="完成 lens：计算/校验/渲染"); p.add_argument("lens")
    p = sub.add_parser("check", help="通用公司体检"); p.add_argument("ticker"); p.add_argument("--yahoo"); p.add_argument("--out")
    p = sub.add_parser("resolve", help="名称/代码解析"); p.add_argument("inputs", nargs="+"); p.add_argument("--hint")
    p = sub.add_parser("exchange", help="交易所原生数据"); p.add_argument("symbol"); p.add_argument("--days", default="180")
    p = sub.add_parser("etf", help="ETF 覆盖审计"); p.add_argument("--refresh", action="store_true")
    p = sub.add_parser("truth", help="代码真值表"); p.add_argument("--refresh", action="store_true")
    p = sub.add_parser("update", help="Serenity 私有档案更新"); p.add_argument("rest", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    if a.cmd == "doctor":
        return cmd_doctor(a)
    if a.cmd == "research":
        a.ticker = normalized_ticker(a.ticker)
        return cmd_research(a)
    if a.cmd == "finish":
        return cmd_finish(a)
    if a.cmd == "check":
        return cmd_check(a)
    if a.cmd == "resolve":
        for raw in a.inputs:
            normalized_ticker(raw, a.hint or "")
        return run([PY, S / "ticker_normalizer.py", *a.inputs, *(["--hint", a.hint] if a.hint else [])])
    if a.cmd == "exchange":
        return run([PY, LIVE, "exchange", a.symbol, "--days", a.days], "network")
    if a.cmd == "etf":
        return cmd_etf(a)
    if a.cmd == "truth":
        return cmd_truth(a)
    return run([PY, S / "serenity_update.py", *a.rest])


def main(argv=None):
    global DEBUG
    args = list(sys.argv[1:] if argv is None else argv)
    DEBUG = "--debug" in args
    args = [arg for arg in args if arg != "--debug"]
    try:
        if sys.version_info < (3, 10):
            raise FriendlyError("python")
        return dispatch(args)
    except FriendlyError as exc:
        if DEBUG:
            raise
        explain(exc.kind)
    except (FileNotFoundError, NotADirectoryError):
        if DEBUG:
            raise
        explain("usage")
    except (TimeoutError, ConnectionError):
        if DEBUG:
            raise
        explain("network")
    except Exception:
        if DEBUG:
            raise
        explain("internal")
    return 1


if __name__ == "__main__":
    sys.exit(main())

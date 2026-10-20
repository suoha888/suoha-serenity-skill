#!/usr/bin/env python3
"""Render a validated SerenityLens into Markdown and a self-contained HTML report.

The renderer refuses lenses that fail scripts/serenity_lens.py validate, so a
report can never show unchecked arithmetic.  The HTML embeds the canonical lens
JSON plus its SHA-256; scripts/verify_report.py uses that to detect hand edits.

  python scripts/render_report.py lens.json --out-dir reports/
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from serenity_lens import validate  # noqa: E402

REQUIRED_SECTIONS = (
    "verdict", "thirty-sec", "capex", "chain", "chokepoint", "gates", "valuation",
    "signals", "memory", "serenity-view", "red-flags", "red-team", "falsification",
    "evidence", "disclaimer",
)
V6_SECTIONS = ("live-data", "doctrine", "variant", "next-hop")
ROLE_TEXT = {
    "chokepoint": "卡点", "price_setter_anchor": "价格制定者/锚", "downstream_platform": "下游平台",
    "integrator_or_commodity": "集成商/可替代件", "diluter_or_story": "稀释/叙事型", "non_ai_compounder": "非 AI 复利股",
}
FIT_TEXT = {"strong": "强", "partial": "部分", "weak": "弱", "not_applicable": "不适用"}
STATUS_TEXT = {
    "now": "正在卡", "filling": "正在被订满", "coming": "即将成为瓶颈", "monopoly_not_bottleneck": "垄断但不紧缺",
    "diluted_exposure": "卡点敞口被稀释", "resolving": "正在缓解", "not_bottleneck": "不是瓶颈", "unknown": "未知",
}
STAGE_TEXT = {
    "rnd": "研发", "sampling": "样品", "qualification": "认证", "volume_ramp": "量产爬坡",
    "steady_state": "稳态", "decline": "衰退",
}
RISK_TEXT = {
    "moonshot": "登月", "rerating": "重估", "western_twin": "西方替代", "binary_restructuring": "二元重组",
    "steady_compounder": "稳健复利", "anchor": "锚", "avoid": "回避",
}
RELATION_TEXT = {"upstream": "上游", "downstream": "下游", "peer": "同层", "western_twin": "西方替代", "anchor": "锚"}


def required_sections(lens: dict[str, Any] | None = None) -> tuple[str, ...]:
    if lens and lens.get("schema_version") == "6.0":
        return REQUIRED_SECTIONS + V6_SECTIONS
    return REQUIRED_SECTIONS


TIER_TEXT = {"green": "🟢 优先研究", "amber": "🟡 观察/等触发", "red": "🔴 排除/否决"}
GATE_TEXT = {"pass": "✅ 通过", "partial": "◐ 部分", "fail": "❌ 不过", "unknown": "？未知"}
LAYER_TEXT = {
    "downstream_reference": "下游对照", "midstream_system": "中游系统", "midstream_component": "中游器件",
    "upstream_equipment": "上游设备", "upstream_material": "上游材料/代工", "cross_theme_root": "跨主题根节点",
}
FRAMEWORK_NOTICE = ("框架声明：本 skill 根据 Serenity 公开发布的内容提炼研究框架，用于回测与研究分析；"
                    "报告由框架生成，不代表 Serenity 本人观点，亦非投资建议。")
BASIS_TEXT = {"serenity_lead": "Serenity 公开线索", "author_lead": "Serenity 公开线索", "industry_knowledge": "行业常识",
              "live_data": "实时数据", "inference": "推断", "inferred": "推断"}
GATE_NAME = {"real_bottleneck": "🔒 真瓶颈", "pre_institutional": "👁️ 前机构", "cheap_derisked": "💰 便宜且去风险"}


def canonical(lens: dict[str, Any]) -> str:
    return json.dumps(lens, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def lens_hash(lens: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(lens).encode("utf-8")).hexdigest()


def fmt_money(v: float, ccy: str) -> str:
    a = abs(v)
    if a >= 1e12:
        s = f"{v / 1e12:.2f}T"
    elif a >= 1e9:
        s = f"{v / 1e9:.2f}B"
    elif a >= 1e6:
        s = f"{v / 1e6:.1f}M"
    else:
        s = f"{v:,.2f}"
    return f"{s} {ccy}"


def e(x: Any) -> str:
    return html.escape(str(x), quote=True)


def cite(ids: list[str] | None) -> str:
    return " ".join(f"[{i}]" for i in (ids or []))


# ----------------------------------------------------------------- v6 blocks
def md_v6_head(L: dict[str, Any]) -> list[str]:
    live, fit, bs, ph, pu, vp = (L["live_data"], L["framework_fit"], L["bottleneck_status"],
                                 L["phase"], L["purity"], L["variant_perception"])
    o: list[str] = []
    o.append("<!-- section:live-data -->")
    o.append("## 0. 实时数据")
    o.append(f"- 快照：`{live['snapshot_path']}` · 取数 {live['retrieved_at']} · 来源 {', '.join(live['source_hosts'])}")
    for w_ in live["warnings_addressed"]:
        o.append(f"- ⚠️ `{w_['warning']}` → {w_['handling']}")
    o.append("")
    o.append("<!-- section:doctrine -->")
    o.append("## 框架定位（Doctrine）")
    o.append("| 维度 | 判断 | 说明 |")
    o.append("|---|---|---|")
    o.append(f"| 框架适配 | {ROLE_TEXT[fit['role']]} · {FIT_TEXT[fit['fit']]} | {fit['rationale']}（{', '.join(fit['rule_ids'])}） |")
    o.append(f"| 瓶颈状态 | {STATUS_TEXT[bs['status']]} · {bs['kind']} | {bs['rationale']} {cite(bs['evidence_ids'])} |")
    o.append(f"| 阶段 | {STAGE_TEXT[ph['stage']]} | {ph['evidence']} {cite(ph['evidence_ids'])} |")
    pct = "未知" if pu["exposure_pct_estimate"] is None else f"约 {pu['exposure_pct_estimate']:g}%"
    o.append(f"| 纯度 | {pct}（{pu['basis']}） | {pu['rationale']} |")
    o.append(f"| 风险档 | {RISK_TEXT[L['risk_tier']]} | PB-STYLE-03 |")
    o.append("")
    o.append("<!-- section:variant -->")
    o.append("## 差异化观点")
    o.append(f"- **市场共识**：{vp['consensus']} {cite([x for x in vp['consensus_sources'] if not x.startswith('assumption:')])}")
    o.append(f"- **我们的看法**：{vp['our_view']}")
    o.append(f"- **为什么市场可能错**：{', '.join(vp['reason_codes'])}")
    o.append(f"- **市场何时会看到**：{vp['when_market_sees']}")
    fn = vp["first_number_to_prove_wrong"]
    o.append(f"- **第一个证伪数字**：`{fn['metric']} {fn['operator']} {fn['threshold']}`（{fn['check_by']} 前检查）")
    o.append(f"- **档案之后的变化**：{vp['what_changed_since_archive']}")
    o.append("")
    return o


def md_v6_next_hop(L: dict[str, Any]) -> list[str]:
    o = ["<!-- section:next-hop -->", "## 下一跳候选（研究线索，非推荐）", "| 代码 | 名称 | 关系 | 节点 | 理由 | 依据 | 先验证 |", "|---|---|---|---|---|---|---|"]
    for p in L["next_hop_picks"]:
        o.append(f"| `{p['ticker']}` | {p['name']} | {RELATION_TEXT[p['relation']]} | {p['node']} | {p['why']} | {BASIS_TEXT.get(p['basis'], p['basis'])} | {p['verify_first']} |")
    o.append("")
    return o


def html_v6_head(L: dict[str, Any]) -> str:
    live, fit, bs, ph, pu, vp = (L["live_data"], L["framework_fit"], L["bottleneck_status"],
                                 L["phase"], L["purity"], L["variant_perception"])
    pct = "未知" if pu["exposure_pct_estimate"] is None else f"约 {pu['exposure_pct_estimate']:g}%"
    fn = vp["first_number_to_prove_wrong"]
    parts = [
        f"<section id='live-data'><h2>0 · 实时数据</h2><p class='mut'>快照 <code>{e(live['snapshot_path'])}</code> · 取数 {e(live['retrieved_at'])} · {e(', '.join(live['source_hosts']))}</p><ul>"
        + "".join(f"<li>⚠️ <code>{e(x['warning'])}</code> → {e(x['handling'])}</li>" for x in live["warnings_addressed"]) + "</ul></section>",
        "<section id='doctrine'><h2>框架定位</h2><table><tr><th>维度</th><th>判断</th><th>说明</th></tr>"
        f"<tr><td>框架适配</td><td>{e(ROLE_TEXT[fit['role']])} · {e(FIT_TEXT[fit['fit']])}</td><td>{e(fit['rationale'])} <span class='mut'>{e(', '.join(fit['rule_ids']))}</span></td></tr>"
        f"<tr><td>瓶颈状态</td><td>{e(STATUS_TEXT[bs['status']])} · {e(bs['kind'])}</td><td>{e(bs['rationale'])} <span class='mut'>{e(cite(bs['evidence_ids']))}</span></td></tr>"
        f"<tr><td>阶段</td><td>{e(STAGE_TEXT[ph['stage']])}</td><td>{e(ph['evidence'])} <span class='mut'>{e(cite(ph['evidence_ids']))}</span></td></tr>"
        f"<tr><td>纯度</td><td>{e(pct)}</td><td>{e(pu['rationale'])}</td></tr>"
        f"<tr><td>风险档</td><td>{e(RISK_TEXT[L['risk_tier']])}</td><td class='mut'>PB-STYLE-03</td></tr></table></section>",
        "<section id='variant'><h2>差异化观点</h2><ul>"
        f"<li><b>市场共识：</b>{e(vp['consensus'])}</li><li><b>我们的看法：</b>{e(vp['our_view'])}</li>"
        f"<li><b>为什么市场可能错：</b>{e(', '.join(vp['reason_codes']))}</li><li><b>市场何时会看到：</b>{e(vp['when_market_sees'])}</li>"
        f"<li><b>第一个证伪数字：</b><code>{e(fn['metric'])} {e(fn['operator'])} {e(fn['threshold'])}</code>（{e(fn['check_by'])} 前）</li>"
        f"<li><b>档案之后的变化：</b>{e(vp['what_changed_since_archive'])}</li></ul></section>",
    ]
    return "".join(parts)


def html_v6_next_hop(L: dict[str, Any]) -> str:
    return ("<section id='next-hop'><h2>下一跳候选（研究线索，非推荐）</h2><table><tr><th>代码</th><th>名称</th><th>关系</th><th>节点</th><th>理由</th><th>依据</th><th>先验证</th></tr>"
            + "".join(f"<tr><td><code>{e(p['ticker'])}</code></td><td>{e(p['name'])}</td><td>{e(RELATION_TEXT[p['relation']])}</td><td>{e(p['node'])}</td><td>{e(p['why'])}</td><td>{e(BASIS_TEXT.get(p['basis'], p['basis']))}</td><td>{e(p['verify_first'])}</td></tr>" for p in L["next_hop_picks"])
            + "</table></section>")


# ----------------------------------------------------------------- markdown
def to_markdown(L: dict[str, Any]) -> str:
    s, v, cur = L["subject"], L["valuation"], L["valuation"]["current"]
    ccy = cur["currency"]
    out: list[str] = []
    w = out.append
    w(f"# {s['company_name']}（{s['resolved_symbol']}）· Serenity 框架卡点透镜")
    w("")
    w("<!-- section:verdict -->")
    w(f"> **{TIER_TEXT[L['research_tier']]}** · {L['one_liner']}")
    w(f"> 截止 {L['research_cutoff'][:10]} · 类型 `{s['company_type']}` · 市值 {fmt_money(cur['market_cap'], ccy)}（{cur['price_as_of'][:10]}）")
    w("")
    w("<!-- section:thirty-sec -->")
    w("## 30 秒看懂")
    w(L["thirty_second_summary"])
    w("")
    w(f"**分级理由：** {L['tier_reason']}")
    if L.get("rerate_triggers"):
        w("")
        w("**重估触发条件：** " + "；".join(L["rerate_triggers"]))
    w("")
    if L.get("schema_version") == "6.0":
        out.extend(md_v6_head(L))
    w("<!-- section:capex -->")
    w("## 1. 资本开支确定性")
    w(f"- 需求来源：`{L['capex_certainty']['demand_source']}`")
    w(f"- {L['capex_certainty']['statement']} {cite(L['capex_certainty']['evidence_ids'])}")
    w("")
    w("<!-- section:chain -->")
    w(f"## 2. 卡点地图：{L['chain_map']['theme']}")
    for layer in L["chain_map"]["layers"]:
        nodes = []
        for n in layer["nodes"]:
            tag = "**" if n.get("is_subject") else ""
            t = f" `{n['ticker']}`" if n.get("ticker") else ""
            st = f"（{n['listing_status']}）" if n.get("listing_status") not in (None, "listed") else ""
            nodes.append(f"{tag}{n['name']}{tag}{t}{st}：{n['role']}")
        w(f"- **{LAYER_TEXT[layer['layer']]}**：" + "；".join(nodes))
    c = L["chokepoint_of_chokepoint"]
    w("")
    w("<!-- section:chokepoint -->")
    w(f"**卡点中的卡点**（{c['status']}）：{c['node']} — {c['statement']} {cite(c['evidence_ids'])}")
    w("")
    if L["archetype_hits"]:
        w("| 卡点原型 | 命中 | 理由 |")
        w("|---|---|---|")
        for a in L["archetype_hits"]:
            w(f"| {a['archetype']} | {a['applies']} | {a['why']} {cite(a.get('evidence_ids'))} |")
        w("")
    w("<!-- section:gates -->")
    w("## 3. 三道闸门")
    for k, g in L["gates"].items():
        w(f"- {GATE_NAME.get(k, k)}：{GATE_TEXT[g['status']]} — {g['why']} {cite(g.get('evidence_ids'))}")
    w("")
    w("<!-- section:valuation -->")
    w(f"## 4. 估值不对称（尺子：`{v['ruler']}`）")
    w(f"现价 {cur['price']} {ccy} × 股本 {cur['shares_outstanding']:,.0f} = 市值 {fmt_money(cur['market_cap'], ccy)} {cite(cur['evidence_ids'])}")
    w("")
    w("| 情景（假设） | 期限 | 收入 | 倍数 | 隐含市值 | 隐含每股 | 相对现价 | 叙事 |")
    w("|---|---|---|---|---|---|---|---|")
    for sc in v["scenarios"]:
        a = sc["assumptions"]
        mult = f"{a['multiple']}x {a['multiple_basis']}" + (f" @ {a['net_margin']:.0%} 净利率" if a.get("net_margin") is not None and a["multiple_basis"] == "pe" else "")
        w(f"| {sc['name']} | {sc['horizon_years']}y | {fmt_money(a['revenue'], ccy)} | {mult} | {fmt_money(sc['implied_market_cap'], ccy)} | {sc['implied_per_share']:.2f} | {sc['vs_current_pct']:+.1f}% | {sc['narrative']} |")
    asym = v.get("asymmetry")
    if asym:
        w("")
        w(f"TAM {fmt_money(asym['tam'], ccy)}（{asym.get('tam_year', '')}，{asym.get('tam_source', '')}）；市值/TAM = {asym.get('mcap_to_tam')}；市值/可获取收入 = {asym.get('mcap_to_capturable_revenue')}")
    if v.get("comparables"):
        w("")
        w("同层对照：" + "；".join(f"`{x['ticker']}` {x['note']}" for x in v["comparables"]))
    w("")
    w("> 情景是“要成立需要什么”的假设推演，不是目标价、收益预测或交易建议。")
    w("")
    w("<!-- section:signals -->")
    w("## 5. 先行信号（不等财报）")
    for sig in L["leading_signals"]:
        w(f"- **{sig['signal']}**（{sig['type']}）— 确认：{sig['confirms_if']}；否定：{sig['refutes_if']}" + (f"；下次检查：{sig['next_check']}" if sig.get("next_check") else ""))
    if L["osint_leads"]:
        w("")
        w("**OSINT 线索：** " + "；".join(f"{o['lead']}（{o['source_type']}, {o['status']}）" for o in L["osint_leads"]))
    w("")
    m = L["serenity_memory"]
    w("<!-- section:memory -->")
    w("## 6. Serenity 公开言论记录（时点）")
    w(f"状态：`{m['status']}`" + (f" · 当前 `{m.get('current_state')}` · 首提 {m.get('first_mention')} · 最近 {m.get('last_mention')} · 提及 {m.get('mention_count')} 次" if m["status"] == "available" else ""))
    for item in m.get("timeline", []):
        w(f"- {item['date']} `{item['action']}`{'/' + item['stance'] if item.get('stance') else ''} · post {item['post_id']}" + (f" · {item['summary']}" if item.get("summary") else ""))
    if m.get("archive_through"):
        w(f"\n档案覆盖至 {m['archive_through'][:10]}；此后 Serenity 是否有新表态未知（沉默不等于卖出或看空）。")
    w(f"\n{m['note']}")
    w("")
    sv = L["serenity_view"]
    w("<!-- section:serenity-view -->")
    w("## 7. 按 Serenity 框架会怎么看")
    w(f"框架是否关注：**{sv['would_he_care']}** — {sv['why']}（规则：{', '.join(sv['playbook_rules'])}）")
    w("")
    if L.get("schema_version") == "6.0":
        out.extend(md_v6_next_hop(L))
    w("<!-- section:red-flags -->")
    w("## 8. 红旗筛查")
    for f in L["red_flags"]:
        w(f"- [{f['severity']}] {f['flag']}：**{f['triggered']}** — {f['detail']} {cite(f.get('evidence_ids'))}")
    w("")
    rt = L["red_team"]
    w("<!-- section:red-team -->")
    w("## 9. 红队：杀死这个判断的最短路径")
    w(f"1. 为什么可能不是真瓶颈？{rt['not_real_bottleneck']}")
    w(f"2. 为什么可能不变现？{rt['not_monetized']}")
    w(f"3. 市场是否已定价？{rt['already_priced']}")
    w(f"4. 更优替代：`{rt['better_alternative']['ticker']}` — {rt['better_alternative']['why']}")
    w(f"\n**最大杀点：** {rt['biggest_kill_shot']}")
    w("")
    w("<!-- section:falsification -->")
    w("## 10. 证伪条件")
    for f in L["falsification"]:
        mc = f" `机器可检: {f['metric']} {f['operator']} {f['threshold']}`" if f["machine_checkable"] else ""
        w(f"- {f['condition']}{mc}" + (f"（检查：{f['check_by']}）" if f.get("check_by") else "")
          + (f"（{f['exit_rule']}）" if f.get("exit_rule") else ""))
    w("")
    w("<!-- section:evidence -->")
    w("## 证据")
    for ev in L["evidence"]:
        w(f"- [{ev['evidence_id']}] {ev['title']} — {ev['locator']}（{ev['published_at'][:10]}，{ev['source_type']}）")
    if L.get("audit_link"):
        al = L["audit_link"]
        w(f"\n审计层：research_output `{al.get('research_output_id', '')}`，bundle 校验 {'通过' if al.get('bundle_validated') else '未运行'}")
    w("")
    w("<!-- section:disclaimer -->")
    w(f"---\n⚠️ {L['disclaimer']}")
    w("")
    if FRAMEWORK_NOTICE not in L["disclaimer"]:  # fixed footer; skip when the lens already carries it verbatim
        w(FRAMEWORK_NOTICE)
        w("")
    w(f"<!-- serenity-lens lens_id={L['lens_id']} sha256={lens_hash(L)} -->")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------- html
CSS = """
:root{--bg:#fffbeb;--card:#ffffff;--line:#f3e3b3;--fg:#1f1a12;--mut:#7a6a4f;--acc:#15803d;--amb:#b45309;--red:#b91c1c;--blue:#1d4ed8;--brand:#c2410c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,Segoe UI,Roboto,"Noto Sans SC",sans-serif}
main{max-width:1080px;margin:0 auto;padding:28px 20px 60px}h1{font-size:26px;margin:0 0 6px}h2{font-size:18px;margin:0 0 12px;color:var(--brand)}
section{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:14px 0;box-shadow:0 2px 10px rgba(180,130,20,.06)}
.mut{color:var(--mut)}#evidence li{overflow-wrap:anywhere}.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-weight:600;margin-right:8px}
.green{background:#dcfce7;color:var(--acc)}.amber{background:#fef3c7;color:var(--amb)}.red{background:#fee2e2;color:var(--red)}
.layer{display:flex;gap:10px;align-items:stretch;margin:8px 0}.lname{min-width:120px;color:var(--mut);font-size:13px;padding-top:6px}
.nodes{display:flex;flex-wrap:wrap;gap:8px}.node{border:1px solid var(--line);border-radius:10px;padding:6px 10px;background:#fffdf5;font-size:13px;max-width:300px}
.node.subj{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc) inset}.node b{display:block}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
.bar{height:10px;border-radius:6px;background:linear-gradient(90deg,#fbbf24,var(--brand))}.bear .bar{background:linear-gradient(90deg,#fca5a5,var(--red))}
.cur{color:var(--amb);font-weight:600}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px}
.kill{border-left:3px solid var(--red);padding-left:10px}.foot{font-size:12px;color:var(--mut)}code{color:var(--blue)}
.tl{border-left:2px solid var(--line);margin-left:6px;padding-left:12px}.tl div{margin:4px 0}
"""


def to_html(L: dict[str, Any]) -> str:
    s, v, cur = L["subject"], L["valuation"], L["valuation"]["current"]
    ccy = cur["currency"]
    tier = L["research_tier"]
    p: list[str] = []
    w = p.append
    w(f"<!doctype html><html lang='zh'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>")
    w(f"<title>{e(s['resolved_symbol'])} · Serenity 框架卡点透镜</title><style>{CSS}</style></head><body><main>")
    w(f"<section id='verdict'><span class='pill {tier}'>{e(TIER_TEXT[tier])}</span><span class='mut'>截止 {e(L['research_cutoff'][:10])} · {e(s['company_type'])} · 市值 {e(fmt_money(cur['market_cap'], ccy))}</span>")
    w(f"<h1>{e(s['company_name'])}（{e(s['resolved_symbol'])}）</h1><p><b>{e(L['one_liner'])}</b></p><p class='mut'>分级理由：{e(L['tier_reason'])}</p>")
    if L.get("rerate_triggers"):
        w("<p class='mut'>重估触发：" + "；".join(e(x) for x in L["rerate_triggers"]) + "</p>")
    w("</section>")
    w(f"<section id='thirty-sec'><h2>30 秒看懂</h2><p>{e(L['thirty_second_summary'])}</p></section>")
    cc = L["capex_certainty"]
    if L.get("schema_version") == "6.0":
        w(html_v6_head(L))
    w(f"<section id='capex'><h2>1 · 资本开支确定性</h2><p><code>{e(cc['demand_source'])}</code> {e(cc['statement'])} <span class='mut'>{e(cite(cc['evidence_ids']))}</span></p></section>")
    w(f"<section id='chain'><h2>2 · 卡点地图：{e(L['chain_map']['theme'])}</h2>")
    for layer in L["chain_map"]["layers"]:
        w(f"<div class='layer'><div class='lname'>{e(LAYER_TEXT[layer['layer']])}{(' · ' + e(layer['taxonomy_code'])) if layer.get('taxonomy_code') else ''}</div><div class='nodes'>")
        for n in layer["nodes"]:
            cls = "node subj" if n.get("is_subject") else "node"
            arche = (" · " + ", ".join(n.get("archetypes", []))) if n.get("archetypes") else ""
            w(f"<div class='{cls}'><b>{e(n['name'])}{(' · ' + e(n['ticker'])) if n.get('ticker') else ''}</b>{e(n['role'])}<span class='mut'>{e(arche)}</span></div>")
        w("</div></div>")
    w("</section>")
    c = L["chokepoint_of_chokepoint"]
    w(f"<section id='chokepoint'><h2>卡点中的卡点 · {e(c['status'])}</h2><p><b>{e(c['node'])}</b> — {e(c['statement'])} <span class='mut'>{e(cite(c['evidence_ids']))}</span></p>")
    if L["archetype_hits"]:
        w("<table><tr><th>原型</th><th>命中</th><th>理由</th></tr>" + "".join(
            f"<tr><td>{e(a['archetype'])}</td><td>{e(a['applies'])}</td><td>{e(a['why'])}</td></tr>" for a in L["archetype_hits"]) + "</table>")
    w("</section>")
    w("<section id='gates'><h2>3 · 三道闸门</h2><div class='grid'>" + "".join(
        f"<div><b>{e(GATE_NAME.get(k, k))}</b><br>{e(GATE_TEXT[g['status']])}<br><span class='mut'>{e(g['why'])}</span></div>" for k, g in L["gates"].items()) + "</div></section>")
    mx = max([sc["implied_per_share"] for sc in v["scenarios"]] + [cur["price"]]) or 1
    w(f"<section id='valuation'><h2>4 · 估值不对称 · 尺子 {e(v['ruler'])}</h2><p>现价 <span class='cur'>{e(cur['price'])} {e(ccy)}</span> × 股本 {cur['shares_outstanding']:,.0f} = {e(fmt_money(cur['market_cap'], ccy))}</p><table>")
    w("<tr><th>情景（假设）</th><th>隐含每股</th><th></th><th>相对现价</th><th>关键假设</th></tr>")
    for sc in v["scenarios"]:
        a = sc["assumptions"]
        width = max(2, int(sc["implied_per_share"] / mx * 100))
        cls = "bear" if sc["vs_current_pct"] < 0 else ""
        assum = f"收入 {fmt_money(a['revenue'], ccy)} · {a['multiple']}x {a['multiple_basis']}" + (f" · 净利率 {a['net_margin']:.0%}" if a.get("net_margin") is not None and a["multiple_basis"] == "pe" else "") + f" · {sc['horizon_years']}y"
        w(f"<tr class='{cls}'><td>{e(sc['name'])}</td><td>{sc['implied_per_share']:.2f}</td><td style='width:30%'><div class='bar' style='width:{width}%'></div></td><td>{sc['vs_current_pct']:+.1f}%</td><td>{e(assum)}<br><span class='mut'>{e(sc['narrative'])}</span></td></tr>")
    w(f"<tr><td class='cur'>现价</td><td class='cur'>{cur['price']:.2f}</td><td><div class='bar' style='width:{max(2, int(cur['price'] / mx * 100))}%;background:var(--amb)'></div></td><td></td><td></td></tr></table>")
    asym = v.get("asymmetry")
    if asym:
        w(f"<p class='mut'>TAM {e(fmt_money(asym['tam'], ccy))}（{e(asym.get('tam_source', ''))}）· 市值/TAM {e(asym.get('mcap_to_tam'))} · 市值/可获取收入 {e(asym.get('mcap_to_capturable_revenue'))}</p>")
    w("<p class='foot'>情景是“要成立需要什么”的假设推演，不是目标价、收益预测或交易建议。</p></section>")
    w("<section id='signals'><h2>5 · 先行信号</h2><table><tr><th>信号</th><th>确认</th><th>否定</th><th>下次检查</th></tr>" + "".join(
        f"<tr><td><b>{e(x['signal'])}</b><br><span class='mut'>{e(x['type'])}</span></td><td>{e(x['confirms_if'])}</td><td>{e(x['refutes_if'])}</td><td>{e(x.get('next_check', ''))}</td></tr>" for x in L["leading_signals"]) + "</table>")
    if L["osint_leads"]:
        w("<p class='mut'>OSINT：" + "；".join(f"{e(o['lead'])}（{e(o['status'])}）" for o in L["osint_leads"]) + "</p>")
    w("</section>")
    m = L["serenity_memory"]
    w(f"<section id='memory'><h2>6 · Serenity 公开言论记录（时点）· {e(m['status'])}</h2>")
    if m["status"] == "available":
        w(f"<p>当前 <b>{e(m.get('current_state'))}</b> · 首提 {e(m.get('first_mention'))} · 最近 {e(m.get('last_mention'))} · {e(m.get('mention_count'))} 次</p><div class='tl'>")
        for it in m.get("timeline", []):
            w(f"<div><code>{e(it['date'])}</code> {e(it['action'])}{('/' + e(it['stance'])) if it.get('stance') else ''} · <a style='color:var(--blue)' href='https://x.com/i/status/{e(it['post_id'])}'>post</a> {e(it.get('summary', ''))}</div>")
        w("</div>")
    if m.get("archive_through"):
        w(f"<p class='mut'>档案覆盖至 {e(m['archive_through'][:10])}；此后 Serenity 是否有新表态未知（沉默不等于卖出或看空）。</p>")
    w(f"<p class='mut'>{e(m['note'])}</p></section>")
    sv = L["serenity_view"]
    w(f"<section id='serenity-view'><h2>7 · 按 Serenity 框架会怎么看</h2><p>框架是否关注：<b>{e(sv['would_he_care'])}</b> — {e(sv['why'])}</p><p class='mut'>规则：{e(', '.join(sv['playbook_rules']))}</p></section>")
    if L.get("schema_version") == "6.0":
        w(html_v6_next_hop(L))
    w("<section id='red-flags'><h2>8 · 红旗筛查</h2><table><tr><th>红旗</th><th>级别</th><th>触发</th><th>说明</th></tr>" + "".join(
        f"<tr><td>{e(f['flag'])}</td><td>{e(f['severity'])}</td><td>{e(f['triggered'])}</td><td>{e(f['detail'])}</td></tr>" for f in L["red_flags"]) + "</table></section>")
    rt = L["red_team"]
    w(f"<section id='red-team'><h2>9 · 红队</h2><ol><li>不是真瓶颈？{e(rt['not_real_bottleneck'])}</li><li>不变现？{e(rt['not_monetized'])}</li><li>已定价？{e(rt['already_priced'])}</li><li>更优替代 <code>{e(rt['better_alternative']['ticker'])}</code>：{e(rt['better_alternative']['why'])}</li></ol><p class='kill'><b>最大杀点：</b>{e(rt['biggest_kill_shot'])}</p></section>")
    w("<section id='falsification'><h2>10 · 证伪条件</h2><ul>" + "".join(
        f"<li>{e(f['condition'])}" + (f" <code>{e(f['metric'])} {e(f['operator'])} {e(f['threshold'])}</code>" if f["machine_checkable"] else "")
        + (f" <span class='mut'>{e(f['exit_rule'])}</span>" if f.get("exit_rule") else "") + "</li>" for f in L["falsification"]) + "</ul></section>")
    w("<section id='evidence'><h2>证据</h2><ul>" + "".join(
        f"<li>[{e(x['evidence_id'])}] {e(x['title'])} — <span class='mut'>{e(x['locator'])} · {e(x['published_at'][:10])}</span></li>" for x in L["evidence"]) + "</ul></section>")
    notice = "" if FRAMEWORK_NOTICE in L["disclaimer"] else f"<br><b>{e(FRAMEWORK_NOTICE)}</b>"
    w(f"<section id='disclaimer' class='foot'>⚠️ {e(L['disclaimer'])}{notice}<br>lens {e(L['lens_id'])} · sha256 {lens_hash(L)[:16]}…</section>")
    w(f"<script type='application/json' id='lens-data' data-sha256='{lens_hash(L)}'>{html.escape(canonical(L), quote=False)}</script>")
    w("</main></body></html>")
    return "\n".join(p)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lens", type=Path)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--stem", help="output file stem (default: lens file stem)")
    args = ap.parse_args(argv)
    L = json.loads(args.lens.read_text(encoding="utf-8"))
    errors = validate(L)
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print("Refusing to render an invalid lens. Run scripts/serenity_lens.py compute, fix, and re-validate.")
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.stem or args.lens.stem
    (args.out_dir / f"{stem}.md").write_text(to_markdown(L), encoding="utf-8")
    (args.out_dir / f"{stem}.html").write_text(to_html(L), encoding="utf-8")
    print(f"OK: rendered {stem}.md and {stem}.html in {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

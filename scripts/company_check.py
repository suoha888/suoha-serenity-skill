#!/usr/bin/env python3
"""Company health check for any listed company (v7.1), network-free.

The chokepoint lens only fits part of the market.  This check works for every
company with a live snapshot (A-shares, Hong Kong, US first; other venues get
what their data allows).  It reads one snapshot written by
``connectors/live_data.py`` and computes, mechanically and with the formula
recorded next to every number:

  growth         revenue / profit YoY, non-recurring profit gap (A-shares)
  profitability  gross margin, net margin, ROE (TTM profit / parent equity)
  cash quality   OCF / net profit, FCF and SBC load (US)
  balance sheet  liabilities / assets, goodwill / equity, net cash
  working cap.   receivables and inventory growth vs revenue growth, contract liabilities
  shareholders   share-count change, share pledge (A-shares), dividend yield
  sector         bank NPL / coverage / CET1 (A-shares)
  valuation      P/E, P/E ex non-recurring, P/B, P/S, P/FCF, dividend yield

Statuses are screens -- ok / watch / flag / info / na -- never buy or sell
conclusions.  Thresholds live in RULES so they are visible and testable.
Company type is routed first (bank, insurer, broker, real estate, utility,
general) because leverage, margins and cash flow mean different things there.

  python scripts/company_check.py SNAPSHOT.json [--md out.md] [--json out.json]
  python scripts/company_check.py PACK_DIR          # uses pack.json's subject snapshot
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

CHECK_VERSION = "company-check-v2"
FINANCIAL = {"bank", "insurer", "broker", "financial_other"}
RULES = {  # id: (watch, flag) thresholds; direction is in the check code
    "G1_revenue_yoy": (0.0, -10.0),
    "G2_profit_yoy": (0.0, -20.0),
    "G3_non_recurring_gap_pct": (20.0, 50.0),
    "P1_gross_margin_change_pp": (-3.0, -8.0),
    "P3_roe_pct": (8.0, 3.0),
    "C1_ocf_to_profit": (0.7, 0.3),
    "C3_sbc_to_revenue_pct": (10.0, 20.0),
    "B1_liabilities_to_assets_pct": (70.0, 85.0),
    "B2_goodwill_to_equity_pct": (30.0, 50.0),
    "W1_receivables_minus_revenue_growth_pp": (20.0, 50.0),
    "W2_inventory_minus_revenue_growth_pp": (20.0, 50.0),
    "W3_contract_liabilities_yoy_pct": (-15.0, -40.0),
    "D1_share_change_pct": (5.0, 10.0),
    "D2_pledge_ratio_pct": (15.0, 30.0),
    "R1_cash_runway_months": (24.0, 12.0),
    "V1_ps_when_growth_below_40pct": (15.0, 30.0),
    "V1r_ps_in_ramp_stage": (30.0, 60.0),
    "S1_bank_npl_pct": (1.8, 3.0),
    "S2_bank_provision_coverage_pct": (180.0, 150.0),
    "S3_bank_cet1_pct": (9.5, 8.0),
}
ZH_ITEM = {"receivables": "应收账款", "inventory": "存货"}
MATERIAL_SHARE_OF_REVENUE = 0.05  # working-capital checks only when the item is >= 5% of TTM revenue
CN_INDUSTRY_ROUTES = (("银行", "bank"), ("保险", "insurer"), ("证券", "broker"), ("多元金融", "financial_other"),
                      ("房地产", "real_estate"), ("电力", "utility"), ("燃气", "utility"), ("水务", "utility"))


def _num(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _period_gap_days(a: str | None, b: str | None) -> int | None:
    try:
        return abs((date.fromisoformat(str(a)[:10]) - date.fromisoformat(str(b)[:10])).days)
    except (TypeError, ValueError):
        return None


def _pct(a: float | None, b: float | None) -> float | None:
    return round((a / b - 1) * 100, 2) if a is not None and b not in (None, 0) and b > 0 else None


def _ratio(a: float | None, b: float | None, scale: float = 1.0) -> float | None:
    return round(a / b * scale, 4) if a is not None and b not in (None, 0) else None


# ---------------------------------------------------------------- routing
def route(snap: dict[str, Any]) -> dict[str, Any]:
    lf = snap.get("local_financials") or {}
    org = str(lf.get("org_type") or "")
    industry = str(((lf.get("pledge") or {}).get("industry")) or "")
    for word, kind in (("银行", "bank"), ("保险", "insurer"), ("证券", "broker")):
        if word in org:
            return {"type": kind, "basis": f"aggregator org_type {org}"}
    for word, kind in CN_INDUSTRY_ROUTES:
        if word in industry:
            return {"type": kind, "basis": f"industry {industry}"}
    sic = (snap.get("sec_profile") or {}).get("sic_code") or (snap.get("filings") or {}).get("sic_code")
    try:
        code = int(sic) if sic else None
    except (TypeError, ValueError):
        code = None
    if code is not None:
        kind = ("bank" if 6000 <= code < 6200 else "broker" if 6200 <= code < 6300 else "insurer" if 6300 <= code < 6420
                else "reit" if code == 6798 else "real_estate" if 6500 <= code < 6600 else "financial_other" if 6700 <= code < 6800
                else "utility" if 4900 <= code < 5000 else "general")
        return {"type": kind, "basis": f"SEC SIC {code} ({(snap.get('sec_profile') or {}).get('sic')})"}
    return {"type": "general", "basis": "no sector marker in the snapshot; treated as an operating company"}


# ---------------------------------------------------------------- metrics
def extract(snap: dict[str, Any]) -> dict[str, Any]:
    """One flat metric dict from whichever statement source the snapshot has."""
    f = snap.get("fundamentals") or {}
    s = f.get("summary", {}) if f.get("status") == "ok" else {}
    lf = snap.get("local_financials") or {}
    m: dict[str, Any] = {"evidence_ids": []}
    if lf.get("status") == "ok" and lf.get("periods"):
        p = lf["periods"][0]
        t = lf.get("ttm") or {}
        bal = (lf.get("balance") or {}) if (lf.get("balance") or {}).get("status") == "ok" else {}
        b, ya = bal.get("latest") or {}, bal.get("year_ago") or {}
        m.update(source=f"{lf['provider']} (aggregator)", currency=lf.get("reporting_currency"), period_end=p["period_end"],
                 period_label=p.get("label"),
                 revenue_ttm=(t.get("revenue") or {}).get("value"), revenue_ttm_basis=(t.get("revenue") or {}).get("basis"),
                 revenue_yoy_pct=p.get("revenue_yoy_pct"), profit_yoy_pct=p.get("net_profit_yoy_pct"),
                 sq_revenue_yoy_pct=p.get("sq_revenue_yoy_pct"), sq_profit_yoy_pct=p.get("sq_net_profit_yoy_pct"),
                 profit_ttm=(t.get("net_profit_parent") or {}).get("value"),
                 profit_deducted_ttm=(t.get("net_profit_deducted") or {}).get("value"),
                 profit_period=p.get("net_profit_parent"), profit_deducted_period=p.get("net_profit_deducted"),
                 gross_profit_ttm=(t.get("gross_profit") or {}).get("value"), gross_margin_pct=p.get("gross_margin_pct"),
                 ocf_ttm=(t.get("operating_cash_flow") or {}).get("value"),
                 equity=b.get("equity_parent") or p.get("equity_parent"), total_assets=b.get("total_assets") or p.get("total_assets"),
                 total_liabilities=b.get("total_liabilities") or p.get("total_liabilities"),
                 debt_to_assets_pct=p.get("debt_to_assets_pct"), goodwill=b.get("goodwill"),
                 cash=(b.get("cash") or 0) + (b.get("short_term_deposits") or 0) if b.get("cash") is not None else None,
                 borrowings=sum(b.get(k) or 0 for k in ("short_term_borrowings", "long_term_borrowings", "bonds_payable",
                                                          "current_portion_noncurrent_liab")) if b else None,
                 receivables=b.get("accounts_receivable") if b.get("accounts_receivable") is not None else b.get("notes_and_accounts_receivable"),
                 receivables_ya=ya.get("accounts_receivable") if ya.get("accounts_receivable") is not None else ya.get("notes_and_accounts_receivable"),
                 inventory=b.get("inventory"), inventory_ya=ya.get("inventory"),
                 contract_liabilities=b.get("contract_liabilities"), contract_liabilities_ya=ya.get("contract_liabilities"),
                 balance_end=b.get("period_end"), balance_ya_end=ya.get("period_end"),
                 shares_total=p.get("shares_total"),
                 bank_npl_pct=p.get("bank_npl_ratio_pct"), bank_coverage_pct=p.get("bank_provision_coverage_pct"),
                 bank_cet1_pct=p.get("bank_cet1_ratio_pct"))
        if m["equity"] is None and p.get("total_equity") is not None:
            m["equity"] = p["total_equity"]
        if p.get("revenue_yoy_pct") is None and m["revenue_ttm"] is None:
            m["revenue_yoy_pct"] = s.get("revenue_yoy_pct")
        pl = lf.get("pledge") or {}
        if pl.get("status") == "ok":
            m["pledge_ratio_pct"], m["pledge_as_of"] = pl.get("pledge_ratio_pct"), pl.get("as_of")
        dv = lf.get("dividends") or {}
        if dv.get("status") == "ok":
            m["dps_ttm"], m["dps_currency"] = dv.get("dps_ttm"), dv.get("currency")
        if p.get("dps_fy_hkd") is not None:
            m["dps_ttm"], m["dps_currency"], m["dps_basis"] = p["dps_fy_hkd"], "HKD", "latest fiscal-year DPS (HKD) per provider"
        m["evidence_ids"] += [e for e in (f"E-LIVE-FIN-{lf['venue']}", f"E-LIVE-BAL-{lf['venue']}", "E-LIVE-PLEDGE", "E-LIVE-DIV")
                              if any(x.get("evidence_id") == e for x in snap.get("evidence", []))]
    elif s:
        def last(key: str) -> float | None:
            return _num((s.get(key) or {}).get("value"))
        gm = (s.get("gross_margin_quarterly") or [{}])[-1]
        m.update(source=("sec_companyfacts" if f.get("provider") == "sec_companyfacts" else f.get("provider")),
                 currency=s.get("reporting_currency"),
                 period_end=(s.get("revenue_latest_quarter") or {}).get("end") or ((s.get("revenue_quarterly") or [{}])[-1]).get("as_of"),
                 revenue_ttm=s.get("revenue_ttm"),
                 revenue_ttm_basis=(s.get("revenue_ttm_basis") or "sum of last four quarters") if s.get("revenue_ttm") else None,
                 revenue_yoy_pct=s.get("revenue_yoy_pct"),
                 revenue_ttm_yoy_pct=_pct(s.get("revenue_ttm"), s.get("revenue_ttm_year_ago")),
                 profit_yoy_pct=(_pct(s.get("net_income_ttm"), s.get("net_income_ttm_year_ago"))
                                 if (s.get("net_income_ttm_year_ago") or 0) > 0 else None),
                 profit_yoy_basis="TTM net income vs TTM a year earlier",
                 profit_ttm=s.get("net_income_ttm"), gross_profit_ttm=s.get("gross_profit_ttm"), gross_margin_pct=gm.get("pct"),
                 gross_margin_change_pp=s.get("gross_margin_change_yoy_pp"),
                 ocf_ttm=s.get("operating_cash_flow_ttm"), capex_ttm=s.get("capex_ttm"), sbc_ttm=s.get("sbc_ttm"),
                 dividends_paid_ttm=s.get("dividends_paid_ttm"), buybacks_ttm=s.get("buybacks_ttm"),
                 equity=last("equity_latest"), total_assets=last("total_assets_latest"), total_liabilities=last("total_liabilities_latest"),
                 goodwill=last("goodwill_latest"), cash=(s.get("cash_and_st_investments") or {}).get("value"),
                 borrowings=last("total_debt_latest"),
                 receivables=last("receivables_latest"), receivables_ya=last("receivables_year_ago"),
                 inventory=last("inventory_latest"), inventory_ya=last("inventory_year_ago"),
                 contract_liabilities=last("contract_liabilities_latest"), contract_liabilities_ya=last("contract_liabilities_year_ago"),
                 balance_end=(s.get("equity_latest") or {}).get("end"), balance_ya_end=(s.get("equity_year_ago") or {}).get("end"))
        m["evidence_ids"] += [e for e in ("E-LIVE-FIN",) if any(x.get("evidence_id") == e for x in snap.get("evidence", []))]
    if s.get("share_count_change_pct_vs_4_obs_ago") is not None:
        m["share_change_pct"] = s["share_count_change_pct_vs_4_obs_ago"]
    if m.get("gross_margin_change_pp") is None and s.get("gross_margin_change_yoy_pp") is not None:
        m["gross_margin_change_pp"] = s["gross_margin_change_yoy_pp"]
    if m.get("total_liabilities") is not None and m.get("total_assets"):
        m["debt_to_assets_pct"] = round(m["total_liabilities"] / m["total_assets"] * 100, 2)
    return m


def _fx(snap: dict[str, Any], from_ccy: str | None, to_ccy: str | None) -> float | None:
    if not from_ccy or not to_ccy:
        return None
    if from_ccy == to_ccy:
        return 1.0
    rates = (snap.get("usd_view") or {}).get("rates") or {}

    def usd(c: str) -> float | None:
        return 1.0 if c == "USD" else _num((rates.get(c) or {}).get("rate"))
    a, b = usd(from_ccy), usd(to_ccy)
    return a / b if a and b else None


def valuation(snap: dict[str, Any], m: dict[str, Any]) -> dict[str, Any]:
    mc = snap.get("market_current") or {}
    q = snap.get("quote") or {}
    price, qccy = _num(mc.get("price")), mc.get("currency")
    if price is None and q.get("status") == "ok":
        price, qccy = _num(q.get("price")), q.get("currency")
    out: dict[str, Any] = {"price": price, "quote_currency": qccy, "reporting_currency": m.get("currency")}
    if price is None:
        return {**out, "status": "na", "note": "no price"}
    shares, basis = _num(m.get("shares_total")), "total shares from the statements (all share lines at this line's price)"
    if mc.get("ah_lines") and _num(mc.get("shares_outstanding")):
        # A+H: market_current already priced each line at its own price; use the line-equivalent share count
        shares, basis = _num(mc["shares_outstanding"]), mc.get("shares_basis") or "A+H: each share line at its own price (line-equivalent shares)"
    if shares is None:
        shares, basis = _num(mc.get("shares_outstanding")), "latest reported shares (market_current)"
    if mc.get("market_cap_withheld") and _num(m.get("shares_total")) is None:
        return {**out, "status": "na", "note": "market cap withheld: " + mc["market_cap_withheld"]}
    if not shares:
        return {**out, "status": "na", "note": "no share count"}
    fx = _fx(snap, qccy, m.get("currency"))
    out.update(shares=shares, shares_basis=basis, market_cap_quote_ccy=round(price * shares, 2))
    if fx is None:
        return {**out, "status": "na", "note": f"no FX from {qccy} to {m.get('currency')}"}
    cap = price * shares * fx
    out["market_cap_reporting_ccy"] = round(cap, 2)
    if fx != 1.0:
        out["fx"] = {"pair": f"{qccy}{m.get('currency')}", "rate": round(fx, 6), "source": "usd_view spot rates"}

    def multiple(denom: Any) -> float | None:
        d = _num(denom)
        return round(cap / d, 2) if d and d > 0 else None
    out.update(pe_ttm=multiple(m.get("profit_ttm")), pe_deducted_ttm=multiple(m.get("profit_deducted_ttm")),
               pb=multiple(m.get("equity")), ps_ttm=multiple(m.get("revenue_ttm")))
    if m.get("ocf_ttm") is not None and m.get("capex_ttm") is not None:
        out["p_fcf_ttm"] = multiple(m["ocf_ttm"] - m["capex_ttm"])
    if _num(m.get("profit_ttm")) is not None and m["profit_ttm"] <= 0:
        out["pe_note"] = "loss-making on a TTM basis: P/E not meaningful"
    dps, dccy = _num(m.get("dps_ttm")), m.get("dps_currency")
    if dps is not None and dccy:
        fxd = _fx(snap, dccy, qccy)
        if fxd:
            out["dividend_yield_pct"] = round(dps * fxd / price * 100, 2)
            out["dividend_basis"] = m.get("dps_basis") or "pre-tax cash dividends with ex-date in the last 365 days"
    elif _num(m.get("dividends_paid_ttm")) and out.get("market_cap_reporting_ccy"):
        out["dividend_yield_pct"] = round(m["dividends_paid_ttm"] / cap * 100, 2)
        out["dividend_basis"] = "dividends paid (cash-flow statement, TTM) / market cap"
    if _num(m.get("buybacks_ttm")):
        out["buyback_yield_pct"] = round(m["buybacks_ttm"] / cap * 100, 2)
    q2 = (snap.get("exchange") or {}).get("second_quote") or {}
    if q2.get("status") == "ok" and _num(q2.get("pe_ttm")) and out.get("pe_ttm"):
        diff = round((out["pe_ttm"] / q2["pe_ttm"] - 1) * 100, 1)
        out["pe_cross_check"] = {"second_source": q2.get("provider"), "pe_ttm": q2["pe_ttm"], "diff_pct": diff,
                                 "status": "agree" if abs(diff) <= 10 else "differs"}
    ah = (snap.get("exchange") or {}).get("ah_premium") or {}
    if ah.get("status") == "ok":
        out["ah_premium_pct"] = ah["premium_pct"]
    out["status"] = "ok"
    out["basis"] = "price x shares, converted to the reporting currency; denominators are TTM where available"
    return out


# ---------------------------------------------------------------- checks
def _grade(value: float | None, rule: str, higher_is_worse: bool) -> str:
    if value is None:
        return "na"
    watch, flag = RULES[rule]
    if higher_is_worse:
        return "flag" if value >= flag else "watch" if value >= watch else "ok"
    return "flag" if value <= flag else "watch" if value <= watch else "ok"


def checks(m: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    fin = kind in FINANCIAL
    out: list[dict[str, Any]] = []

    def add(cid: str, area: str, label: str, value: Any, unit: str, status: str, formula: str, why: str = "") -> None:
        out.append({"id": cid, "area": area, "label": label, "value": value, "unit": unit, "status": status,
                    "formula": formula, **({"why": why} if why else {})})
    rev_g = m.get("revenue_yoy_pct") if m.get("revenue_yoy_pct") is not None else m.get("revenue_ttm_yoy_pct")
    add("G1", "growth", "收入同比", rev_g, "%", _grade(rev_g, "G1_revenue_yoy", False),
        "最新报告期累计收入同比（A/H 聚合源）或最新季度同比（SEC/Yahoo）")
    if m.get("sq_revenue_yoy_pct") is not None:
        add("G1q", "growth", "单季收入同比", m["sq_revenue_yoy_pct"], "%", _grade(m["sq_revenue_yoy_pct"], "G1_revenue_yoy", False),
            "最新单季 vs 去年同季（聚合源单季口径）")
    add("G2", "growth", "归母净利同比", m.get("profit_yoy_pct"), "%", _grade(m.get("profit_yoy_pct"), "G2_profit_yoy", False),
        "TTM 净利润 vs 一年前 TTM（SEC；上年为亏损时不计算）" if m.get("profit_yoy_basis") else "最新报告期累计归母净利润同比")
    if m.get("profit_period") and m.get("profit_deducted_period") is not None:
        gap = round(abs(m["profit_period"] - m["profit_deducted_period"]) / abs(m["profit_period"]) * 100, 2)
        add("G3", "growth", "非经常性损益占净利", gap, "%", _grade(gap, "G3_non_recurring_gap_pct", True),
            "|归母净利 − 扣非净利| / |归母净利|", "占比高说明利润靠一次性项目")
    if not fin:
        add("P1", "profitability", "毛利率", m.get("gross_margin_pct"), "%", "info", "毛利 / 收入（最新期）")
        if m.get("gross_margin_change_pp") is not None:
            add("P1d", "profitability", "毛利率同比变化", m["gross_margin_change_pp"], "pp",
                _grade(m["gross_margin_change_pp"], "P1_gross_margin_change_pp", False), "最新季度毛利率 − 去年同季")
    nm = _ratio(m.get("profit_ttm"), m.get("revenue_ttm"), 100)
    add("P2", "profitability", "净利率（TTM）", round(nm, 2) if nm is not None else None, "%", "info" if nm is not None else "na",
        "TTM 净利润 / TTM 收入")
    roe = _ratio(m.get("profit_ttm"), m.get("equity"), 100)
    add("P3", "profitability", "ROE（TTM）", round(roe, 2) if roe is not None else None, "%", _grade(roe, "P3_roe_pct", False),
        "TTM 归母净利润 / 期末归母权益（未取平均）")
    if not fin:
        cq = _ratio(m.get("ocf_ttm"), m.get("profit_ttm"))
        st = "na"
        if cq is not None and m.get("profit_ttm") and m["profit_ttm"] > 0:
            st = _grade(cq, "C1_ocf_to_profit", False)
        elif m.get("profit_ttm") is not None and m["profit_ttm"] <= 0:
            st = "info"
        add("C1", "cash", "经营现金流 / 净利润（TTM）", round(cq, 2) if cq is not None else None, "x", st,
            "TTM 经营活动现金流净额 / TTM 净利润", "长期 <0.7 说明利润没有变成现金")
        if m.get("ocf_ttm") is not None and m.get("capex_ttm") is not None:
            fcf = m["ocf_ttm"] - m["capex_ttm"]
            add("C2", "cash", "自由现金流（TTM）", round(fcf, 0), m.get("currency") or "", "watch" if fcf < 0 else "ok",
                "TTM 经营现金流 − TTM 资本开支")
    sbc = _ratio(m.get("sbc_ttm"), m.get("revenue_ttm"), 100)
    if sbc is not None:
        add("C3", "cash", "股权激励费用 / 收入（TTM）", round(sbc, 2), "%", _grade(sbc, "C3_sbc_to_revenue_pct", True),
            "TTM 股权激励费用 / TTM 收入", "高 SBC 是隐性稀释")
    if not fin:
        add("B1", "balance", "资产负债率", m.get("debt_to_assets_pct"), "%",
            _grade(m.get("debt_to_assets_pct"), "B1_liabilities_to_assets_pct", True) if kind not in ("real_estate", "utility", "reit") else "info",
            "总负债 / 总资产", "地产/公用事业天然高杠杆，仅作参考" if kind in ("real_estate", "utility", "reit") else "")
    gw = _ratio(m.get("goodwill"), m.get("equity"), 100)
    if not (fin and gw is None):
        add("B2", "balance", "商誉 / 归母权益", round(gw, 2) if gw is not None else (0.0 if m.get("goodwill") is None and m.get("equity") and m.get("balance_end") else None),
            "%", _grade(gw, "B2_goodwill_to_equity_pct", True) if gw is not None else ("ok" if m.get("equity") and m.get("balance_end") else "na"),
            "期末商誉 / 期末归母权益", "商誉大意味着减值风险")
    if not fin and m.get("cash") is not None and m.get("borrowings") is not None:
        add("B3", "balance", "净现金（现金 − 有息负债）", round(m["cash"] - m["borrowings"], 0), m.get("currency") or "", "info",
            "现金及等价物(+短期存款/短投) − 短借 − 长借 − 应付债券")
    rev_growth = rev_g
    for cid, key, label, rule in (("W1", "receivables", "应收增速 − 收入增速", "W1_receivables_minus_revenue_growth_pp"),
                                  ("W2", "inventory", "存货增速 − 收入增速", "W2_inventory_minus_revenue_growth_pp")):
        if fin:
            continue
        g = _pct(m.get(key), m.get(f"{key}_ya"))
        material = m.get(key) is not None and m.get("revenue_ttm") and m[key] >= MATERIAL_SHARE_OF_REVENUE * m["revenue_ttm"]
        val = round(g - rev_growth, 2) if g is not None and rev_growth is not None else None
        # v8.1: a fiscal-year balance sheet against a later quarter's revenue growth is not a like-for-like test
        lag = _period_gap_days(m.get("balance_end"), m.get("period_end"))
        misaligned = lag is not None and lag > 100
        note = ("" if material else f"{ZH_ITEM[key]}不足 TTM 收入的 5%，只作参考")
        if misaligned and val is not None:
            note = (note + "；" if note else "") + f"资产负债表期末 {m.get('balance_end')} 与收入期末 {m.get('period_end')} 相差 {lag} 天，口径不一致，只作参考"
        add(cid, "working_capital", label, val, "pp",
            _grade(val, rule, True) if material and not misaligned else ("info" if val is not None else "na"),
            f"{ZH_ITEM[key]}同比（{m.get('balance_ya_end')}→{m.get('balance_end')}）− 收入同比", note)
    cl = _pct(m.get("contract_liabilities"), m.get("contract_liabilities_ya"))
    if cl is not None and not fin:
        cl_material = bool(m.get("revenue_ttm")) and (m.get("contract_liabilities") or 0) >= 0.01 * m["revenue_ttm"]
        add("W3", "working_capital", "合同负债/预收同比", cl, "%",
            _grade(cl, "W3_contract_liabilities_yoy_pct", False) if cl_material else "info",
            "期末合同负债 / 去年同期 − 1",
            "上升=客户预付增加（需求领先信号）；大降需追问" if cl_material else "合同负债不足 TTM 收入的 1%，基数小，百分比只作参考")
    add("D1", "shareholders", "股本变化（约一年）", m.get("share_change_pct"), "%", _grade(m.get("share_change_pct"), "D1_share_change_pct", True),
        "最新股本 / 4 个观测点前 − 1", "持续增发=稀释")
    if m.get("pledge_ratio_pct") is not None:
        add("D2", "shareholders", "股权质押比例", m["pledge_ratio_pct"], "%", _grade(m["pledge_ratio_pct"], "D2_pledge_ratio_pct", True),
            f"中国结算质押股数 / 总股本（截至 {m.get('pledge_as_of')}）", "高质押在股价下跌时有平仓风险")
    if kind == "bank":
        for cid, key, label, rule, worse in (("S1", "bank_npl_pct", "不良贷款率", "S1_bank_npl_pct", True),
                                             ("S2", "bank_coverage_pct", "拨备覆盖率", "S2_bank_provision_coverage_pct", False),
                                             ("S3", "bank_cet1_pct", "核心一级资本充足率", "S3_bank_cet1_pct", False)):
            add(cid, "sector", label, m.get(key), "%", _grade(m.get(key), rule, worse), "聚合源银行专项指标（最新报告期）")
    return out


# ---------------------------------------------------------------- v9 stage layer
RAMP_MIN_REVENUE_GROWTH = 25.0     # loss-making but revenue growing >= 25% y/y -> ramp / qualification stage
PER_SHARE_GROWTH_EXCEPTION = 20.0  # dilution downgraded to watch when revenue per share still grows >= 20%
MIN_SCORED_CHECKS = 3  # fewer scored rows than this = not enough data to call the check "clean"
FINANCING_LADDER = "ATM（持续、无上限，最差）< 溢价可转债 < 定增 < 客户预付/长约（最好）"
STAGE_ZH = {"ramp": "认证/放量期", "cyclical_high": "周期高利润期", "loss_no_growth": "亏损且不增长", "operating": "常规经营期"}


def stage(m: dict[str, Any], val: dict[str, Any], kind: str) -> dict[str, Any]:
    """Which stage the numbers put the company in, and which KPIs that stage is judged on.

    Serenity-style rule: a company in qualification/ramp is judged on orders, qualification and capacity,
    not on current profit; what can kill it is cash runway and the kind of dilution it uses."""
    if kind in FINANCIAL:
        return {"stage": "operating", "basis": "financial company", "kpis": ["ROE", "P/B", "资产质量"]}
    rev_g = m.get("revenue_yoy_pct") if m.get("revenue_yoy_pct") is not None else m.get("revenue_ttm_yoy_pct")
    profit = _num(m.get("profit_ttm"))
    pe = _num(val.get("pe_ttm"))
    if profit is not None and profit <= 0 and rev_g is not None and rev_g >= RAMP_MIN_REVENUE_GROWTH:
        return {"stage": "ramp", "basis": f"TTM 亏损且收入同比 {rev_g:.0f}% ≥ {RAMP_MIN_REVENUE_GROWTH:.0f}%",
                "kpis": ["认证/客户导入进度", "订单与长约（可取消比例）", "产能与良率爬坡", "现金跑道", "融资方式"]}
    if profit is not None and profit <= 0 and (rev_g is None or rev_g < 10):
        return {"stage": "loss_no_growth", "basis": "TTM 亏损且收入增速 < 10%" if rev_g is not None else "TTM 亏损且无收入增速数据",
                "kpis": ["现金跑道", "融资方式与稀释", "收入能否恢复增长"]}
    pg = m.get("profit_yoy_pct")
    if pe is not None and pe <= 12 and pg is not None and pg >= 100:
        return {"stage": "cyclical_high", "basis": f"净利同比 {pg:.0f}% 且 P/E(TTM) {pe:.1f}x",
                "kpis": ["价格/ASP 能否持续", "持续时间（长约年限）", "成本上升与利润回落情景", "囤货 vs 结构性短缺"]}
    return {"stage": "operating", "basis": "常规口径", "kpis": ["收入增速", "利润率", "现金转换", "估值"]}


def apply_stage(rows: list[dict[str, Any]], m: dict[str, Any], val: dict[str, Any], st: dict[str, Any], kind: str) -> None:
    by = {r["id"]: r for r in rows}
    if st["stage"] == "ramp":
        for cid in ("G2", "P3", "C1"):
            r = by.get(cid)
            if r and r["status"] in ("flag", "watch"):
                r["stage_adjusted_from"] = r["status"]
                r["status"] = "info"
                r["why"] = ((r.get("why") + "；") if r.get("why") else "") + "认证/放量期：当期利润不是关键 KPI，改看订单、认证、产能、现金跑道与融资方式"
    if kind not in FINANCIAL and m.get("ocf_ttm") is not None and m.get("capex_ttm") is not None and m.get("cash") is not None:
        fcf = m["ocf_ttm"] - m["capex_ttm"]
        if fcf < 0:
            months = round(m["cash"] / (-fcf / 12.0), 1)
            rows.append({"id": "R1", "area": "cash", "label": "现金跑道（月）", "value": months, "unit": "月",
                         "status": _grade(months, "R1_cash_runway_months", False),
                         "formula": "现金及短投 / (−TTM 自由现金流 / 12)",
                         "why": "跑道短 = 近期必须融资；融资方式决定稀释好坏：" + FINANCING_LADDER})
    d1 = by.get("D1")
    rev_g = m.get("revenue_yoy_pct") if m.get("revenue_yoy_pct") is not None else m.get("revenue_ttm_yoy_pct")
    if d1 and d1["status"] in ("flag", "watch") and d1.get("value") is not None:
        why = "核实融资方式：" + FINANCING_LADDER
        if rev_g is not None:
            ps = round(((1 + rev_g / 100) / (1 + d1["value"] / 100) - 1) * 100, 1)
            why = f"每股收入同比 {ps:+.1f}%；" + why
            if d1["status"] == "flag" and ps >= PER_SHARE_GROWTH_EXCEPTION:
                d1["stage_adjusted_from"] = "flag"
                d1["status"] = "watch"
                why = "增长快于稀释（例外规则：融资用于扩产且每股收入仍高增长）；" + why
        d1["why"] = why
    ps_ttm, g = _num(val.get("ps_ttm")), rev_g
    if st["stage"] != "ramp" and ps_ttm is not None and g is not None and g < 40:
        rows.append({"id": "V1", "area": "valuation", "label": "P/S（增速 < 40% 时）", "value": ps_ttm, "unit": "x",
                     "status": _grade(ps_ttm, "V1_ps_when_growth_below_40pct", True),
                     "formula": "市值 / TTM 收入，仅在收入增速 < 40% 时打分",
                     "why": "好公司 ≠ 好价格：增速不够时高 P/S 需要更强的前瞻证据"})
    elif st["stage"] == "ramp" and ps_ttm is not None:
        rows.append({"id": "V1", "area": "valuation", "label": "P/S（认证/放量期）", "value": ps_ttm, "unit": "x",
                     "status": _grade(ps_ttm, "V1r_ps_in_ramp_stage", True),
                     "formula": "市值 / TTM 收入；放量期阈值放宽，但极端倍数仍要求订单/长约能覆盖",
                     "why": "放量期不看当期利润，但好公司 ≠ 好价格：倍数要能被已签订单和产能爬坡解释"})


def verify_list(rows: list[dict[str, Any]], st: dict[str, Any]) -> list[str]:
    """Things a human must confirm in primary filings before trusting the mechanical result."""
    out = ["瓶颈/主题业务占总收入的比例（分部披露；占比小=敞口被稀释）",
           "近 12 个月融资：方式（" + FINANCING_LADDER + "）、规模/市值、用途、价格；未用完的 ATM/储架额度",
           "前五大客户集中度与长约条款（期限、可取消比例、预付款）"]
    if st["stage"] == "ramp":
        out.append("认证阶段与时间表（样品→认证→小批量→量产），以公司原话为准")
    if st["stage"] == "cyclical_high":
        out.append("单期年化利润做压力测试：成本上升、利润减半、价格回到正常三种情景")
    for r in rows:
        if r["status"] == "flag":
            out.append(f"{r['id']} {r['label']}：到定期报告原文核对口径与一次性因素")
    return out


def check(snap: dict[str, Any]) -> dict[str, Any]:
    kind = route(snap)
    m = extract(snap)
    rows = checks(m, kind["type"])
    val = valuation(snap, m)
    st = stage(m, val, kind["type"])
    apply_stage(rows, m, val, st, kind["type"])
    counts = {k: sum(1 for r in rows if r["status"] == k) for k in ("flag", "watch", "ok", "info", "na")}
    data_status = "ok" if (counts["ok"] + counts["watch"] + counts["flag"]) >= MIN_SCORED_CHECKS else "insufficient"
    notes = ["机械体检：每项都附公式与阈值（RULES），状态只是“该去看什么”，不是买卖结论。"]
    if data_status == "insufficient":
        notes.insert(0, "数据不足：可打分的项目少于 %d 项，0 个红旗不代表“干净”，请先补数据（ETF/基金/新股/停牌常见）。" % MIN_SCORED_CHECKS)
    if m.get("source", "").endswith("(aggregator)"):
        notes.append("A 股/港股财务来自聚合源（东方财富 F10），决定性数字请到巨潮/披露易定期报告原文核对。")
    if kind["type"] in FINANCIAL:
        notes.append("金融类公司：毛利率、现金流、资产负债率不适用，改看 ROE、P/B 与（银行）资产质量指标。")
    return {"check_version": CHECK_VERSION, "symbol": (snap.get("subject") or {}).get("symbol"),
            "name": (snap.get("quote") or {}).get("name") or (snap.get("local_financials") or {}).get("name"),
            "retrieved_at": snap.get("retrieved_at"), "company_type": kind, "source": m.get("source"),
            "currency": m.get("currency"), "period_end": m.get("period_end"), "evidence_ids": m.get("evidence_ids", []),
            "stage": st, "data_status": data_status, "checks": rows, "valuation": val, "counts": counts, "verify": verify_list(rows, st), "rules": RULES, "notes": notes}


# ---------------------------------------------------------------- rendering
ICON = {"flag": "🚩", "watch": "👀", "ok": "✅", "info": "ℹ️", "na": "—"}
TYPE_ZH = {"bank": "银行", "insurer": "保险", "broker": "券商", "financial_other": "其他金融", "real_estate": "地产",
           "reit": "REIT", "utility": "公用事业", "general": "一般经营企业"}


def _fmt(v: Any, unit: str) -> str:
    if v is None:
        return "—"
    if isinstance(v, (int, float)) and abs(v) >= 1e6:
        for div, suf in ((1e12, "万亿"), (1e8, "亿")):
            if abs(v) >= div:
                return f"{v / div:,.2f}{suf} {unit}".strip()
    if isinstance(v, float):
        return f"{v:,.2f}{unit}" if unit in ("%", "pp", "x") else f"{v:,.2f} {unit}".strip()
    return f"{v}{unit}" if unit in ("%", "pp", "x") else f"{v} {unit}".strip()


def to_markdown(r: dict[str, Any], heading: str = "##") -> str:
    ct = r["company_type"]
    L = [f"{heading} 公司体检（通用框架 · {CHECK_VERSION}）", "",
         f"- 类型路由：**{TYPE_ZH.get(ct['type'], ct['type'])}**（依据：{ct['basis']}）",
         f"- 数据：{r.get('source') or '—'}，报告期 {r.get('period_end') or '—'}，币种 {r.get('currency') or '—'}；证据 {', '.join(r.get('evidence_ids') or []) or '—'}",
         *( [f"- 阶段：**{STAGE_ZH.get(r['stage']['stage'], r['stage']['stage'])}**（{r['stage']['basis']}）；该阶段看：{'、'.join(r['stage']['kpis'])}"] if r.get('stage') else [] ),
         f"- 结果：🚩 {r['counts']['flag']} · 👀 {r['counts']['watch']} · ✅ {r['counts']['ok']} · ℹ️ {r['counts']['info']} · — {r['counts']['na']}", "",
         "| 项目 | 数值 | 状态 | 公式 / 说明 |", "|---|---|---|---|"]
    for c in r["checks"]:
        extra = f"；{c['why']}" if c.get("why") else ""
        L.append(f"| {c['id']} {c['label']} | {_fmt(c['value'], c['unit'])} | {ICON[c['status']]} | {c['formula']}{extra} |")
    v = r["valuation"]
    L += ["", f"**估值（{v.get('reporting_currency') or '—'} 口径）**", ""]
    if v.get("status") != "ok":
        L.append(f"- 未计算：{v.get('note')}")
    else:
        bits = [f"市值 {_fmt(v.get('market_cap_reporting_ccy'), v.get('reporting_currency') or '')}"]
        for key, label in (("pe_ttm", "P/E(TTM)"), ("pe_deducted_ttm", "P/E 扣非"), ("pb", "P/B"), ("ps_ttm", "P/S"), ("p_fcf_ttm", "P/FCF")):
            if v.get(key) is not None:
                bits.append(f"{label} {v[key]:.1f}x")
        if v.get("dividend_yield_pct") is not None:
            bits.append(f"股息率 {v['dividend_yield_pct']:.2f}%")
        if v.get("buyback_yield_pct") is not None:
            bits.append(f"回购收益率 {v['buyback_yield_pct']:.2f}%")
        if v.get("ah_premium_pct") is not None:
            bits.append(f"A/H 溢价 {v['ah_premium_pct']:+.1f}%")
        L.append("- " + " · ".join(bits))
        L.append(f"- 股本口径：{v.get('shares_basis')}" + (f"；汇率 {v['fx']['pair']} {v['fx']['rate']}" if v.get("fx") else ""))
        if v.get("pe_note"):
            L.append(f"- 注：{v['pe_note']}")
        if v.get("pe_cross_check"):
            pc = v["pe_cross_check"]
            L.append(f"- P/E 第二来源（{pc['second_source']}）{pc['pe_ttm']}x，差 {pc['diff_pct']}%（{pc['status']}）")
    if r.get("verify"):
        L += ["", "**需核实清单（到定期报告/公告原文确认）**", ""] + [f"- [ ] {x}" for x in r["verify"]]
    L += [""] + [f"> {n}" for n in r["notes"]] + [""]
    return "\n".join(L)


def _load(path: Path) -> dict[str, Any]:
    if path.is_dir():
        pack = json.loads((path / "pack.json").read_text(encoding="utf-8"))
        return json.loads(Path(pack["snapshots"][pack["subject"]]).read_text(encoding="utf-8"))
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("source", type=Path, help="snapshot JSON or pack directory")
    p.add_argument("--md", type=Path)
    p.add_argument("--json", dest="json_out", type=Path)
    args = p.parse_args(argv)
    result = check(_load(args.source))
    if args.json_out:
        args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = to_markdown(result)
    if args.md:
        args.md.write_text(md, encoding="utf-8")
    if not args.md and not args.json_out:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Financial statements for mainland A-shares and Hong Kong listings (v7.1).

Yahoo's time series only carries revenue / gross profit / share count for most
A-share and Hong Kong issuers.  This module adds the rest of the statements from
the Eastmoney F10 datacenter -- an *aggregator* that normalises the periodic
reports filed on CNINFO (mainland) and HKEXnews (Hong Kong):

  block         A-shares (.SS/.SZ/.BJ)                      Hong Kong (.HK)
  ------------  ------------------------------------------  ---------------------------------
  periods       revenue, gross profit, parent net profit,   revenue, gross profit, holder
                non-recurring-adjusted profit, OCF, ROE,     profit, OCF, ROE, debt ratio,
                debt ratio, single-quarter YoY/QoQ, bank     EPS/BPS, latest FY DPS (HKD)
                metrics (NPL, coverage, CET1)
  balance       goodwill, receivables, inventory, contract   same, from the long-format
                liabilities, cash, borrowings (YoY pair)     HK balance sheet
  pledge        CSDC share-pledge ratio (weekly)            -
  dividends     implemented cash dividends per share         -

Every block is fetched through ``live_data.Fetcher`` (allowlisted, cached,
read-only GET), carries its source URL, and is labelled
``provider_kind="aggregator"`` with a pointer to the primary filing system.
Year-to-date figures are converted to TTM mechanically (YTD + prior FY - prior
YTD); the arithmetic basis is always recorded.  Aggregated numbers are leads:
confirm any figure that drives a conclusion in the periodic report itself.
"""
from __future__ import annotations

import json
import urllib.parse
from datetime import date, datetime, timedelta
from typing import Any

import live_data as L

EM = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
PROVIDER = "eastmoney_f10"
PRIMARY = {"CN": "CNINFO periodic reports (www.cninfo.com.cn)", "HK": "HKEXnews financial statements (www1.hkexnews.hk)"}
CN_SUFFIX = {"SS": "SH", "SZ": "SZ", "BJ": "BJ"}

CN_MAIN = {  # Eastmoney column -> normalised key
    "TOTALOPERATEREVE": "revenue", "MLR": "gross_profit", "PARENTNETPROFIT": "net_profit_parent",
    "KCFJCXSYJLR": "net_profit_deducted", "NETCASH_OPERATE_PK": "operating_cash_flow",
    "TOTAL_ASSETS_PK": "total_assets", "TOTAL_EQUITY_PK": "total_equity", "EPSJB": "eps_basic", "BPS": "bps",
    "ROEJQ": "roe_pct", "XSMLL": "gross_margin_pct", "XSJLL": "net_margin_pct", "ZCFZL": "debt_to_assets_pct",
    "TOTALOPERATEREVETZ": "revenue_yoy_pct", "PARENTNETPROFITTZ": "net_profit_yoy_pct",
    "KCFJCXSYJLRTZ": "deducted_profit_yoy_pct", "DJD_TOI_YOY": "sq_revenue_yoy_pct", "DJD_DPNP_YOY": "sq_net_profit_yoy_pct",
    "DJD_TOI_QOQ": "sq_revenue_qoq_pct", "DJD_DPNP_QOQ": "sq_net_profit_qoq_pct", "TOTAL_SHARE": "shares_total",
    "NONPERLOAN": "bank_npl_ratio_pct", "BLDKBBL": "bank_provision_coverage_pct", "HXYJBCZL": "bank_cet1_ratio_pct",
    "NEWCAPITALADER": "bank_capital_adequacy_pct", "TOTALDEPOSITS": "bank_total_deposits", "GROSSLOANS": "bank_gross_loans",
}
HK_MAIN = {
    "OPERATE_INCOME": "revenue", "GROSS_PROFIT": "gross_profit", "HOLDER_PROFIT": "net_profit_parent",
    "NETCASH_OPERATE": "operating_cash_flow", "TOTAL_ASSETS": "total_assets", "TOTAL_LIABILITIES": "total_liabilities",
    "TOTAL_PARENT_EQUITY": "equity_parent", "BASIC_EPS": "eps_basic", "BPS": "bps", "ROE_AVG": "roe_pct",
    "GROSS_PROFIT_RATIO": "gross_margin_pct", "NET_PROFIT_RATIO": "net_margin_pct", "DEBT_ASSET_RATIO": "debt_to_assets_pct",
    "OPERATE_INCOME_YOY": "revenue_yoy_pct", "HOLDER_PROFIT_YOY": "net_profit_yoy_pct", "ISSUED_COMMON_SHARES": "shares_total",
    "DPS_HKD": "dps_fy_hkd", "ACCOUNTS_RECE_TDAYS": "receivable_days", "INVENTORY_TDAYS": "inventory_days",
}
CN_BALANCE = {
    "GOODWILL": "goodwill", "ACCOUNTS_RECE": "accounts_receivable", "NOTE_ACCOUNTS_RECE": "notes_and_accounts_receivable",
    "INVENTORY": "inventory", "CONTRACT_LIAB": "contract_liabilities", "ADVANCE_RECEIVABLES": "advance_receipts",
    "MONETARYFUNDS": "cash", "SHORT_LOAN": "short_term_borrowings", "LONG_LOAN": "long_term_borrowings",
    "BOND_PAYABLE": "bonds_payable", "NONCURRENT_LIAB_1YEAR": "current_portion_noncurrent_liab",
    "TOTAL_ASSETS": "total_assets", "TOTAL_LIABILITIES": "total_liabilities", "TOTAL_PARENT_EQUITY": "equity_parent",
}
HK_BALANCE = {
    "商誉": "goodwill", "应收帐款": "accounts_receivable", "存货": "inventory", "递延收入(流动)": "contract_liabilities",
    "现金及等价物": "cash", "短期存款": "short_term_deposits", "短期贷款": "short_term_borrowings", "长期贷款": "long_term_borrowings",
    "应付票据(非流动)": "bonds_payable", "总资产": "total_assets", "总负债": "total_liabilities", "股东权益": "equity_parent",
}


def secucode(symbol: str) -> tuple[str, str]:
    """('CN'|'HK', Eastmoney SECUCODE) for a Yahoo-style symbol."""
    sym = symbol.strip().upper()
    code, _, suffix = sym.rpartition(".")
    if suffix in CN_SUFFIX:
        return "CN", f"{code}.{CN_SUFFIX[suffix]}"
    if suffix == "HK":
        return "HK", f"{code.zfill(5)}.HK"
    raise ValueError(f"not_cn_or_hk:{symbol}")


def em_url(report: str, filt: str, size: int, sort: str | None = None, columns: str = "ALL") -> str:
    q = {"reportName": report, "columns": columns, "filter": filt, "pageNumber": "1", "pageSize": str(size)}
    if sort:
        q.update(sortColumns=sort, sortTypes="-1")
    return EM + "?" + urllib.parse.urlencode(q)


def em_rows(fetcher: L.Fetcher, url: str, kind: str = "venue_list") -> list[dict[str, Any]]:
    data = json.loads(fetcher.get(url, kind).decode("utf-8"))
    rows = ((data or {}).get("result") or {}).get("data") or []
    if not rows:
        raise KeyError(f"eastmoney_no_rows:{(data or {}).get('message') or 'empty'}")
    return rows


def _day(v: Any) -> str | None:
    return str(v)[:10] if v else None


def _num(v: Any) -> float | None:
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def _months(start: str | None, end: str) -> int:
    if not start:  # A-shares: December fiscal year, cumulative from 1 January
        return int(end[5:7])
    d = (date.fromisoformat(end) - date.fromisoformat(start)).days
    return max(1, round(d / 30.44))


def _norm_period(row: dict[str, Any], mapping: dict[str, str], venue: str) -> dict[str, Any]:
    end = _day(row.get("REPORT_DATE"))
    out: dict[str, Any] = {"period_end": end, "period_months": _months(_day(row.get("START_DATE")) if venue == "HK" else None, end),
                           "label": row.get("REPORT_DATE_NAME") or row.get("REPORT_TYPE"),
                           "notice_date": _day(row.get("NOTICE_DATE"))}
    for col, key in mapping.items():
        v = _num(row.get(col))
        if v is not None:
            out[key] = round(v, 6) if abs(v) < 1e6 else v
    return out


def ttm(periods: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    """TTM from cumulative (YTD) periods: latest YTD + prior full year - prior-year YTD."""
    rows = [p for p in periods if p.get(key) is not None]
    if not rows:
        return None
    cur = rows[0]
    if cur["period_months"] >= 12:
        return {"value": cur[key], "basis": f"FY {cur['period_end']}"}
    cend = date.fromisoformat(cur["period_end"])
    prior = next((p for p in rows[1:] if p["period_months"] == cur["period_months"]
                  and abs((cend - date.fromisoformat(p["period_end"])).days - 365) <= 7), None)
    if not prior:
        return None
    annual = next((p for p in rows[1:] if p["period_months"] >= 12
                   and date.fromisoformat(prior["period_end"]) < date.fromisoformat(p["period_end"]) < cend), None)
    if not annual:
        return None
    return {"value": cur[key] + annual[key] - prior[key],
            "basis": f"YTD {cur['period_end']} + FY {annual['period_end']} - YTD {prior['period_end']}"}


def _yahoo_check(periods: list[dict[str, Any]], yahoo_summary: dict[str, Any] | None) -> dict[str, Any]:
    """Second-source check: aggregator revenue for the latest period vs the sum of Yahoo quarters."""
    yq = (yahoo_summary or {}).get("revenue_quarterly") or []
    if not periods or not yq:
        return {"status": "not_comparable", "note": "no Yahoo quarterly revenue to compare"}
    for p in periods[:4]:
        if p.get("revenue") is None:
            continue
        end = date.fromisoformat(p["period_end"])
        start = end - timedelta(days=int(p["period_months"] * 30.44) - 10)
        inside = [q for q in yq if start < date.fromisoformat(q["as_of"][:10]) <= end + timedelta(days=5)]
        if len(inside) * 3 != p["period_months"]:
            continue
        total = sum(q["value"] for q in inside)
        diff = (p["revenue"] / total - 1) * 100 if total else None
        ccy = inside[-1].get("currency")
        return {"status": "match" if diff is not None and abs(diff) <= 2 else "mismatch", "period_end": p["period_end"],
                "aggregator_revenue": p["revenue"], "yahoo_revenue": total, "diff_pct": round(diff, 2) if diff is not None else None,
                "yahoo_currency": ccy}
    return {"status": "not_comparable", "note": "no period where Yahoo quarters cover the aggregator period"}


def _balance_cn(fetcher: L.Fetcher, code: str) -> dict[str, Any]:
    url = em_url("RPT_F10_FINANCE_GBALANCE", f'(SECUCODE="{code}")', 6, "REPORT_DATE")
    rows = em_rows(fetcher, url)
    norm = [{"period_end": _day(r.get("REPORT_DATE")), **{k: _num(r.get(c)) for c, k in CN_BALANCE.items() if _num(r.get(c)) is not None}}
            for r in rows]
    return _balance_pair(norm, url)


def _balance_hk(fetcher: L.Fetcher, code: str, ends: list[str]) -> dict[str, Any]:
    norm = []
    url0 = None
    for end in ends:
        url = em_url("RPT_HKF10_FN_BALANCE_PC", f"(SECUCODE=\"{code}\")(REPORT_DATE='{end}')", 200,
                     columns="STD_ITEM_NAME,AMOUNT,REPORT_DATE")
        url0 = url0 or url
        try:
            rows = em_rows(fetcher, url)
        except KeyError:
            continue
        rec: dict[str, Any] = {"period_end": end}
        for r in rows:
            key = HK_BALANCE.get(str(r.get("STD_ITEM_NAME")))
            if key and _num(r.get("AMOUNT")) is not None:
                rec[key] = _num(r.get("AMOUNT"))
        norm.append(rec)
    if not norm:
        raise KeyError("hk_balance_unavailable")
    return _balance_pair(norm, url0 or EM)


def _balance_pair(norm: list[dict[str, Any]], url: str) -> dict[str, Any]:
    latest = norm[0]
    lend = date.fromisoformat(latest["period_end"])
    prior = next((r for r in norm[1:] if abs((lend - date.fromisoformat(r["period_end"])).days - 365) <= 7), None)
    out = {"status": "ok", "latest": latest, "source_url": url}
    if prior:
        out["year_ago"] = prior
    return out


def _pledge_cn(fetcher: L.Fetcher, code: str) -> dict[str, Any]:
    url = em_url("RPT_CSDC_LIST", f'(SECUCODE="{code}")', 1, "TRADE_DATE")
    r = em_rows(fetcher, url)[0]
    return {"status": "ok", "as_of": _day(r.get("TRADE_DATE")), "pledge_ratio_pct": _num(r.get("PLEDGE_RATIO")),
            "pledge_deals": r.get("PLEDGE_DEAL_NUM"), "industry": r.get("INDUSTRY"), "basis": "CSDC weekly pledge statistics (% of total shares)",
            "source_url": url}


def _dividends_cn(fetcher: L.Fetcher, code: str, now: datetime) -> dict[str, Any]:
    url = em_url("RPT_SHAREBONUS_DET", f'(SECUCODE="{code}")', 10, "REPORT_DATE")
    try:
        rows = em_rows(fetcher, url)
    except KeyError:
        return {"status": "ok", "items": [], "dps_ttm": 0.0, "note": "no dividend records", "source_url": url}
    items = []
    for r in rows:
        per10 = _num(r.get("PRETAX_BONUS_RMB"))
        items.append({"report_period": _day(r.get("REPORT_DATE")), "ex_date": _day(r.get("EX_DIVIDEND_DATE")),
                      "cash_per_share_pretax": round(per10 / 10, 6) if per10 else None,
                      "progress": r.get("ASSIGN_PROGRESS"), "plan": r.get("IMPL_PLAN_PROFILE")})
    cutoff = (now - timedelta(days=365)).date().isoformat()
    paid = [x for x in items if x["ex_date"] and x["ex_date"] >= cutoff and x["cash_per_share_pretax"]
            and x["ex_date"] <= now.date().isoformat()]
    return {"status": "ok", "items": items[:6], "dps_ttm": round(sum(x["cash_per_share_pretax"] for x in paid), 6),
            "dps_ttm_basis": f"pre-tax cash dividends with ex-date in ({cutoff}, {now.date().isoformat()}]",
            "currency": "CNY", "source_url": url}


def financials(fetcher: L.Fetcher, symbol: str, yahoo_summary: dict[str, Any] | None = None,
               now: datetime | None = None) -> dict[str, Any]:
    """Normalised statement block for one A-share / HK symbol; sub-blocks degrade independently."""
    now = now or L.utc_now()
    venue, code = secucode(symbol)
    if venue == "CN":
        url = em_url("RPT_F10_FINANCE_MAINFINADATA", f'(SECUCODE="{code}")', 9, "REPORT_DATE")
        mapping = CN_MAIN
    else:
        url = em_url("RPT_HKF10_FN_MAININDICATOR", f'(SECUCODE="{code}")', 10, "REPORT_DATE")
        mapping = HK_MAIN
    raw = em_rows(fetcher, url)
    periods = [_norm_period(r, mapping, venue) for r in raw]
    head = raw[0]
    out: dict[str, Any] = {
        "provider": PROVIDER, "provider_kind": "aggregator", "venue": venue, "secucode": code,
        "name": head.get("SECURITY_NAME_ABBR"), "org_type": head.get("ORG_TYPE"),
        "primary_check": PRIMARY[venue], "source_url": url, "periods": periods[:9],
    }
    xcheck = _yahoo_check(periods, yahoo_summary)
    out["yahoo_cross_check"] = xcheck
    field_ccy = head.get("CURRENCY")
    if venue == "CN":
        out["reporting_currency"], out["currency_basis"] = field_ccy or "CNY", "provider CURRENCY field"
    elif xcheck.get("status") == "match" and xcheck.get("yahoo_currency"):
        out["reporting_currency"], out["currency_basis"] = xcheck["yahoo_currency"], "matched Yahoo revenue (financialCurrency)"
    elif (yahoo_summary or {}).get("reporting_currency"):
        out["reporting_currency"] = yahoo_summary["reporting_currency"]
        out["currency_basis"] = "Yahoo reporting currency (aggregator revenue not cross-checked)"
    else:
        out["reporting_currency"], out["currency_basis"] = None, f"unconfirmed (provider field says {field_ccy}, which is the listing currency for many HK issuers)"
    if venue == "HK":
        out["listing_currency_field"] = field_ccy
    out["ttm"] = {k: v for k in ("revenue", "gross_profit", "net_profit_parent", "net_profit_deducted", "operating_cash_flow")
                  if (v := ttm(periods, k))}
    if venue == "CN":
        fin_template = (out["org_type"] or "通用") == "通用"
        out["balance"] = L.section(lambda: _balance_cn(fetcher, code)) if fin_template else \
            {"status": "unavailable", "error": f"template_{out['org_type']}: bank/insurer/broker balance sheet not parsed; use sector metrics"}
        out["pledge"] = L.section(lambda: _pledge_cn(fetcher, code))
        out["dividends"] = L.section(lambda: _dividends_cn(fetcher, code, now))
    else:
        ends = [periods[0]["period_end"]]
        ya = next((p["period_end"] for p in periods[1:] if abs((date.fromisoformat(periods[0]["period_end"]) -
                                                                  date.fromisoformat(p["period_end"])).days - 365) <= 7), None)
        if ya:
            ends.append(ya)
        out["balance"] = L.section(lambda: _balance_hk(fetcher, code, ends))
    return out


def evidence(fin: dict[str, Any], retrieved: str) -> list[dict[str, Any]]:
    """Lens evidence rows for the financial block (source_type market_data: aggregator, not the filing)."""
    if fin.get("status") != "ok" or not fin.get("periods"):
        return []
    p = fin["periods"][0]
    ccy = fin.get("reporting_currency") or "?"
    pub = L.day_iso(p.get("notice_date") or p["period_end"])

    def big(v: Any) -> str:
        return f"{v:,.0f}" if isinstance(v, (int, float)) else "n/a"
    ev = [{"evidence_id": f"E-LIVE-FIN-{fin['venue']}", "title": (
        f"[{fin['provider']} aggregator] {fin.get('name')} {p.get('label') or p['period_end']}: revenue {big(p.get('revenue'))} {ccy} "
        f"(YoY {p.get('revenue_yoy_pct')}%), parent net profit {big(p.get('net_profit_parent'))} (YoY {p.get('net_profit_yoy_pct')}%), "
        f"OCF {big(p.get('operating_cash_flow'))}; confirm in {fin['primary_check']}"),
        "locator": fin["source_url"], "published_at": pub, "retrieved_at": retrieved, "source_type": "market_data"}]
    bal = fin.get("balance") or {}
    if bal.get("status") == "ok":
        b = bal["latest"]
        ev.append({"evidence_id": f"E-LIVE-BAL-{fin['venue']}", "title": (
            f"[{fin['provider']} aggregator] balance sheet {b['period_end']}: equity {big(b.get('equity_parent'))}, goodwill {big(b.get('goodwill'))}, "
            f"receivables {big(b.get('accounts_receivable'))}, inventory {big(b.get('inventory'))}, contract liabilities {big(b.get('contract_liabilities'))}"),
            "locator": bal["source_url"], "published_at": L.day_iso(b["period_end"]), "retrieved_at": retrieved, "source_type": "market_data"})
    pl = fin.get("pledge") or {}
    if pl.get("status") == "ok" and pl.get("as_of"):
        ev.append({"evidence_id": "E-LIVE-PLEDGE", "title": f"CSDC share-pledge ratio {pl.get('pledge_ratio_pct')}% of total shares as of {pl['as_of']} (via {fin['provider']})",
                   "locator": pl["source_url"], "published_at": L.day_iso(pl["as_of"]), "retrieved_at": retrieved, "source_type": "market_data"})
    dv = fin.get("dividends") or {}
    paid = [x for x in dv.get("items", []) if x.get("ex_date")]
    if dv.get("status") == "ok" and paid:
        ev.append({"evidence_id": "E-LIVE-DIV", "title": f"Cash dividends: TTM {dv.get('dps_ttm')} CNY/share pre-tax; latest ex-date {paid[0]['ex_date']} ({paid[0].get('plan')})",
                   "locator": dv["source_url"], "published_at": L.day_iso(paid[0]["ex_date"]), "retrieved_at": retrieved, "source_type": "market_data"})
    return ev


def warnings(fin: dict[str, Any], now: datetime | None = None) -> list[str]:
    w: list[str] = []
    if fin.get("status") != "ok":
        if fin.get("error"):
            w.append(f"local_financials_unavailable: {fin['error']}")
        return w
    w.append(f"financials_from_aggregator: {fin['provider']} normalises filed reports; confirm decisive figures in {fin['primary_check']}")
    x = fin.get("yahoo_cross_check") or {}
    if x.get("status") == "mismatch" and (fin.get("org_type") or "通用") not in ("通用", "一般企业"):
        w.append(f"aggregator_vs_yahoo_revenue_definition_differs_{x['period_end']}: {x['diff_pct']}% — {fin['org_type']} revenue "
                 "definitions differ between sources; use the filed report")
    elif x.get("status") == "mismatch":
        w.append(f"aggregator_vs_yahoo_revenue_mismatch_{x['period_end']}: {x['diff_pct']}% — check restatement, scope or currency")
    if not fin.get("reporting_currency"):
        w.append("hk_reporting_currency_unconfirmed: " + fin.get("currency_basis", ""))
    p = (fin.get("periods") or [{}])[0]
    if p.get("period_end") and now and (now.date() - date.fromisoformat(p["period_end"])).days > 200:
        w.append(f"local_financials_older_than_200_days:{p['period_end']}")
    if "net_profit_parent" not in (fin.get("ttm") or {}):
        w.append("net_profit_ttm_unavailable: prior-year periods missing; ratios use the latest period only")
    return w

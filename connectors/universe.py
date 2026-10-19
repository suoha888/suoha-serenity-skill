#!/usr/bin/env python3
"""Listing universe for name <-> code resolution (v7.1): A-shares, Hong Kong, US.

Sources (official lists first; the aggregator only adds simplified names and A+H links):
  A-shares  CNINFO stock list            https://www.cninfo.com.cn/new/data/szse_stock.json
  HK        HKEXnews active stock lists  https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_{c,e}.json
            Eastmoney HK profiles        simplified-Chinese short names + organisation codes
  US        SEC ticker/exchange map      https://www.sec.gov/files/company_tickers_exchange.json
  A+H       an A-share line and an H-share line sharing one Eastmoney organisation code

Writes assets/universe/{cn,hk,us,ah}.json (compact rows + as_of + source URLs).
All requests go through ``live_data.Fetcher``.  The runtime never needs the
network for name lookup: scripts/ticker_normalizer.py reads these files.

  python connectors/universe.py build            # refresh all lists (about 40 requests)
  python connectors/universe.py build --only us
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_data as L  # noqa: E402
import cnhk_fin as C  # noqa: E402

OUT = L.ROOT / "assets" / "universe"
CNINFO_LIST = "https://www.cninfo.com.cn/new/data/szse_stock.json"
HKEX_TC = "https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_c.json"
HKEX_EN = "https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_e.json"
SEC_EXCH = "https://www.sec.gov/files/company_tickers_exchange.json"
CN_EXCH = {"60": "SS", "68": "SS", "90": "SS", "00": "SZ", "30": "SZ", "20": "SZ"}


def cn_symbol(code: str) -> str:
    return f"{code}.{CN_EXCH.get(code[:2], 'BJ')}"


def hk_symbol(code: str) -> str:
    return f"{int(code):04d}.HK"


def _pages(fetcher: L.Fetcher, report: str, filt: str | None, columns: str, limit: int = 30) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in range(1, limit + 1):
        q = {"reportName": report, "columns": columns, "pageNumber": str(page), "pageSize": "500"}
        if filt:
            q["filter"] = filt
        data = json.loads(fetcher.get(C.EM + "?" + L.urllib.parse.urlencode(q), "venue_static").decode("utf-8"))
        res = (data or {}).get("result") or {}
        rows += res.get("data") or []
        if page >= int(res.get("pages") or 0):
            break
    return rows


def build_cn(fetcher: L.Fetcher) -> dict[str, Any]:
    data = json.loads(fetcher.get(CNINFO_LIST, "venue_static").decode("utf-8"))
    rows = sorted(([x["code"], cn_symbol(x["code"]), x["zwjc"], x.get("pinyin") or "", x.get("orgId") or ""]
                   for x in data["stockList"] if x.get("category") == "A股"), key=lambda r: r[0])
    return {"market": "CN", "fields": ["code", "symbol", "name", "pinyin", "cninfo_org_id"], "rows": rows,
            "source_urls": [CNINFO_LIST], "note": "CNINFO list (A-shares incl. STAR, ChiNext, BSE); may lag new listings/delistings by days"}


def build_hk(fetcher: L.Fetcher) -> tuple[dict[str, Any], dict[str, str]]:
    tc = json.loads(fetcher.get(HKEX_TC, "venue_static").decode("utf-8"))
    en = {x["c"]: x["n"] for x in json.loads(fetcher.get(HKEX_EN, "venue_static").decode("utf-8"))}
    prof = _pages(fetcher, "RPT_HKF10_INFO_ORGPROFILE", None, "SECUCODE,ORG_CODE,SECURITY_NAME_ABBR")
    sc = {r["SECUCODE"].split(".")[0]: r for r in prof if r.get("SECUCODE")}
    rows, org = [], {}
    for x in tc:
        code = x["c"]
        if not code.isdigit() or int(code) >= 10000 or 4000 <= int(code) < 6030:
            continue  # warrants/CBBCs live above 10000; 04000-06029 are debt securities
        p = sc.get(code) or {}
        rows.append([code, hk_symbol(code), x["n"], p.get("SECURITY_NAME_ABBR") or "", en.get(code, "")])
        if p.get("ORG_CODE"):
            org[code] = p["ORG_CODE"]
    rows.sort(key=lambda r: r[0])
    return ({"market": "HK", "fields": ["code", "symbol", "name_tc", "name_sc", "name_en"], "rows": rows,
             "source_urls": [HKEX_TC, HKEX_EN, C.EM + "?reportName=RPT_HKF10_INFO_ORGPROFILE"],
             "note": "HKEX active securities below 10000 excluding the 04000-06029 debt range (shares, ETFs, REITs); simplified names from the Eastmoney HK profile"}, org)


def build_us(fetcher: L.Fetcher) -> dict[str, Any]:
    data = fetcher.json(SEC_EXCH, "sec_map")
    f = data["fields"]
    rows = sorted(([r[f.index("ticker")], r[f.index("name")], r[f.index("exchange")] or "", r[f.index("cik")]]
                   for r in data["data"] if r[f.index("ticker")]), key=lambda r: r[0])
    return {"market": "US", "fields": ["ticker", "name", "exchange", "cik"], "rows": rows, "source_urls": [SEC_EXCH],
            "note": "SEC registrants with a listed ticker; Chinese names for popular US names live in assets/ticker-aliases.seed.json"}


def build_ah(fetcher: L.Fetcher, cn: dict[str, Any], hk_org: dict[str, str], fy_end: str) -> dict[str, Any]:
    rows = _pages(fetcher, "RPT_F10_FINANCE_MAINFINADATA", f"(REPORT_DATE='{fy_end}')", "SECUCODE,ORG_CODE,SECURITY_NAME_ABBR")
    names = {r[0]: r[2] for r in cn["rows"]}
    a_by_org: dict[str, str] = {}
    for r in rows:
        code = str(r.get("SECUCODE", "")).split(".")[0]
        if code in names and r.get("ORG_CODE"):
            a_by_org[r["ORG_CODE"]] = code
    pairs = sorted(([cn_symbol(a_by_org[o]), hk_symbol(h), names[a_by_org[o]]] for h, o in hk_org.items() if o in a_by_org),
                   key=lambda r: r[0])
    return {"market": "AH", "fields": ["a_symbol", "h_symbol", "name"], "rows": pairs,
            "source_urls": [C.EM + "?reportName=RPT_F10_FINANCE_MAINFINADATA", C.EM + "?reportName=RPT_HKF10_INFO_ORGPROFILE"],
            "note": f"A-share and H-share lines sharing one issuer organisation code (A-share FY {fy_end} filers)"}


def write(name: str, block: dict[str, Any], as_of: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.json"
    payload = {"universe_version": "1", "as_of": as_of, **block, "count": len(block["rows"])}
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--only", choices=["cn", "hk", "us", "ah"], action="append")
    b.add_argument("--cache", type=Path, default=L.ROOT / ".cache" / "live")
    args = p.parse_args(argv)
    fetcher = L.Fetcher(cache_dir=args.cache)
    now = L.utc_now()
    as_of = now.date().isoformat()
    only = set(args.only or ["cn", "hk", "us", "ah"])
    done: dict[str, Any] = {}
    cn = build_cn(fetcher) if only & {"cn", "ah"} else None
    if cn and "cn" in only:
        done["cn"] = str(write("cn", cn, as_of))
    if only & {"hk", "ah"}:
        hk, org = build_hk(fetcher)
        if "hk" in only:
            done["hk"] = str(write("hk", hk, as_of))
        if "ah" in only and cn:
            done["ah"] = str(write("ah", build_ah(fetcher, cn, org, f"{now.year - 1}-12-31"), as_of))
    if "us" in only:
        done["us"] = str(write("us", build_us(fetcher), as_of))
    print(json.dumps({"as_of": as_of, "written": done}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

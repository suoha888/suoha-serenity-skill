#!/usr/bin/env python3
"""Exchange-native data for non-US listings (v6.3).

All network access goes through ``live_data.Fetcher`` (allowlisted, cached,
read-only), so this module adds sources without adding a second gateway.

Coverage (no key needed unless stated):

  venue      second-source quote     disclosures                     extra
  ---------  ----------------------  ------------------------------  -------------------------
  CN (.SS/.SZ/.BJ)  Tencent quote    CNINFO announcements            title flags
  HK (.HK)          Tencent quote    HKEXnews title search           title flags
  TW (.TW/.TWO)     -                -                               TWSE/TPEx monthly revenue
  JP (.T)           -                TDnet timely disclosure (~30d)  EDINET (EDINET_API_KEY)
  KR (.KS/.KQ)      -                DART (DART_API_KEY)             title flags
  US                SEC lives in live_data.py; ETF holdings via SEC N-PORT here

Every item carries its source URL and an exchange timestamp converted to UTC.
Title flags are keyword leads (dilution, guidance change, major contract,
insider/major-holder change, delisting/going-concern risk, buyback, periodic
report); they are prompts to open the document, never conclusions.
"""
from __future__ import annotations

import io
import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from html import unescape
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import live_data as L

# These venues have used fixed offsets since 1992. Windows may lack IANA data;
# modern disclosures must not require a third-party Python package.
FALLBACK_VENUES = set()
def venue_timezone(venue, name, hours):
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        FALLBACK_VENUES.add(venue)
        return timezone(timedelta(hours=hours), name)

TZ = {v: venue_timezone(v, name, hours) for v, name, hours in (
    ("CN", "Asia/Shanghai", 8), ("HK", "Asia/Hong_Kong", 8),
    ("TW", "Asia/Taipei", 8), ("JP", "Asia/Tokyo", 9), ("KR", "Asia/Seoul", 9))}
SUFFIX_VENUE = {"SS": "CN", "SZ": "CN", "BJ": "CN", "HK": "HK", "TW": "TW", "TWO": "TW", "T": "JP",
                "KS": "KR", "KQ": "KR"}
OTHER_SYSTEMS = {"L": "RNS (London Stock Exchange)", "PA": "Euronext / AMF", "AS": "Euronext / AFM", "DE": "Bundesanzeiger / DGAP",
                 "ST": "Nasdaq Nordic / FI", "TO": "SEDAR+", "V": "SEDAR+", "AX": "ASX announcements", "SW": "SIX",
                 "MI": "Borsa Italiana / CONSOB", "CO": "Nasdaq Copenhagen", "OL": "Oslo Børs NewsWeb"}
SYSTEM_NAME = {"CN": "CNINFO", "HK": "HKEXnews", "TW": "TWSE/TPEx OpenAPI", "JP": "TDnet / EDINET", "KR": "DART"}

# keyword -> flag; matched case-insensitively against announcement titles
TITLE_FLAGS: dict[str, tuple[str, str, str]] = {
    # flag: (regex, direction, doctrine rule)
    "dilution": (r"定增|非公开发行|向特定对象发行|可转换公司债|可转债|配股|增发|placing|subscription of new|convertible|rights issue|open offer|"
                 r"第三者割当|新株予約権|公募|売出し|転換社債|유상증자|전환사채|신주인수권|現金增資|轉換公司債|私募", "check", "PB-FIN-01"),
    "insider_or_holder_change": (r"减持|股东.*变动|权益变动|控股股东|disclosure of interests|大量保有|主要株主|최대주주|임원ㆍ주요주주|董事.*持股|内部人", "check", "PB-SIG-10"),
    "major_contract": (r"重大合同|中标|签订.*合同|日常经营重大|major transaction|very substantial|大型受注|資本業務提携|業務提携|단일판매|공급계약|重大訂單", "positive", "PB-SIG-05"),
    "guidance_change": (r"业绩预告|业绩快报|业绩预增|业绩预减|profit warning|positive profit alert|inside information|業績予想の修正|上方修正|下方修正|잠정실적|영업실적", "check", "PB-SIG-03"),
    "listing_or_going_concern_risk": (r"退市|\*st|持续经营|风险警示|going concern|suspension|継続企業の前提|上場廃止|감사의견|관리종목|上市.*終止", "negative", "PB-PHASE-01"),
    "debt_issuance": (r"issue of debt securities|notes due|发行.*债券|公司债券|中期票据|社債|회사채|公司債", "check", "PB-FIN-01"),
    "buyback": (r"回购|share buyback|repurchase|自己株式|자기주식|庫藏股", "positive", "PB-FIN-09"),
    "capacity_or_capex": (r"扩产|产能|募投|新建.*项目|投资.*项目|capacity|設備投資|増産|시설투자|擴產", "check", "PB-CAP-04"),
    "periodic_report": (r"年度报告|半年度报告|季度报告|annual report|interim report|quarterly report|決算短信|有価証券報告書|四半期報告書|半期報告書|"
                        r"사업보고서|분기보고서|반기보고서|年報|季報", "info", "PB-DATA-01"),
}


def venue_of(symbol: str) -> dict[str, Any]:
    sym = symbol.strip().upper()
    if "." not in sym:
        return {"venue": "US", "code": sym, "suffix": ""}
    code, suffix = sym.rsplit(".", 1)
    venue = SUFFIX_VENUE.get(suffix)
    if venue:
        return {"venue": venue, "code": code, "suffix": suffix, "system": SYSTEM_NAME[venue]}
    return {"venue": "OTHER", "code": code, "suffix": suffix, "system": OTHER_SYSTEMS.get(suffix, "the exchange's official disclosure system")}


def _utc(local: datetime, venue: str) -> str:
    if venue in FALLBACK_VENUES and local.year < 1992:
        raise ValueError("Historical timestamps before 1992 require system IANA timezone data")
    return L.iso(local.replace(tzinfo=TZ[venue]).astimezone(timezone.utc))


def _clean(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(title or ""))).strip()


def title_flags(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for flag, (rx, direction, rule) in TITLE_FLAGS.items():
        hits = [i for i in items if re.search(rx, i.get("title", ""), re.I)]
        if hits:
            out.append({"flag": flag, "direction": direction, "doctrine": rule, "count": len(hits),
                        "latest": {k: hits[0].get(k) for k in ("title", "published_at", "url")},
                        "urls": [h.get("url") for h in hits[:5] if h.get("url")]})
    return out


# ---------------------------------------------------------------- quotes
def tencent_code(symbol: str) -> str:
    v = venue_of(symbol)
    if v["venue"] == "CN":
        prefix = {"SS": "sh", "SZ": "sz", "BJ": "bj"}[v["suffix"]]
        return prefix + v["code"]
    if v["venue"] == "HK":
        return "hk" + v["code"].zfill(5)
    raise KeyError(f"tencent_unsupported_venue:{symbol}")


def parse_tencent(raw: bytes, symbol: str, url: str) -> dict[str, Any]:
    text = raw.decode("gbk", "replace")
    m = re.search(r'="([^"]*)"', text)
    if not m or "~" not in m.group(1):
        raise KeyError("tencent_no_result")
    f = m.group(1).split("~")
    venue = venue_of(symbol)["venue"]

    def num(i: int) -> float | None:
        try:
            return float(f[i]) if f[i] not in ("", "-") else None
        except (IndexError, ValueError):
            return None
    if venue == "CN":
        when = datetime.strptime(f[30], "%Y%m%d%H%M%S")
        shares, ccy, pe, pb = num(73), (f[82] if len(f) > 82 and f[82] else "CNY"), num(39), num(46)
    else:
        when = datetime.strptime(f[30], "%Y/%m/%d %H:%M:%S")
        shares, ccy, pe, pb = num(70), (f[75] if len(f) > 75 and f[75] else "HKD"), num(39), None
    cap_e8 = num(45)
    return {"provider": "tencent", "symbol": symbol, "name": f[1], "price": num(3), "previous_close": num(4),
            "price_as_of": _utc(when, venue), "currency": ccy,
            "market_cap": round(cap_e8 * 1e8, 2) if cap_e8 else None, "shares_total": shares,
            "pe_ttm": pe, "pb": pb, "source_url": url}


def tencent_quote(fetcher: L.Fetcher, symbol: str) -> dict[str, Any]:
    url = f"https://qt.gtimg.cn/q={tencent_code(symbol)}"
    return parse_tencent(fetcher.get(url, "venue_quote"), symbol, url)


def cross_check(primary: dict[str, Any], second: dict[str, Any], tolerance_pct: float = 1.5) -> dict[str, Any]:
    """Compare two independent quotes; a mismatch is a warning, never silently averaged."""
    if primary.get("status") != "ok" or second.get("status") != "ok":
        return {"status": "not_compared", "reason": "one source unavailable"}
    p1, p2 = primary.get("price"), second.get("price")
    if not p1 or not p2:
        return {"status": "not_compared", "reason": "price missing"}
    diff = round((p2 / p1 - 1) * 100, 3)
    t1, t2 = L.parse_dt(primary.get("price_as_of")), L.parse_dt(second.get("price_as_of"))
    lag_h = round(abs((t1 - t2).total_seconds()) / 3600, 1) if t1 and t2 else None
    ok = abs(diff) <= tolerance_pct
    return {"status": "agree" if ok else "mismatch", "price_diff_pct": diff, "timestamp_gap_hours": lag_h,
            "tolerance_pct": tolerance_pct, "second_source": second.get("provider"),
            "note": None if ok else "quotes disagree beyond tolerance: check session, currency, share line, or a stale feed"}


# ---------------------------------------------------------------- disclosures
def cninfo_announcements(fetcher: L.Fetcher, symbol: str, days: int = 180, limit: int = 30,
                         now: datetime | None = None) -> dict[str, Any]:
    v = venue_of(symbol)
    code = v["code"]
    now = now or L.utc_now()
    search = "https://www.cninfo.com.cn/new/information/topSearch/query"
    hits = json.loads(fetcher.get(search, "venue_static", form={"keyWord": code, "maxNum": "5"}).decode("utf-8"))
    org = next((h for h in hits if h.get("code") == code), None)
    if not org:
        raise KeyError(f"cninfo_org_not_found:{code}")
    url = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
    start = (now - timedelta(days=days)).date().isoformat()
    form = {"stock": f"{code},{org['orgId']}", "tabName": "fulltext", "pageSize": str(limit), "pageNum": "1",
            "column": "sse" if v["suffix"] == "SS" else "szse", "category": "", "plate": "",
            "seDate": f"{start}~{now.date().isoformat()}", "searchkey": "", "secid": "", "sortName": "",
            "sortType": "", "isHLtitle": "true"}
    data = json.loads(fetcher.get(url, "venue_list", form=form).decode("utf-8"))
    items = []
    for a in data.get("announcements") or []:
        if a.get("secCode") != code:
            continue
        ts = datetime.fromtimestamp(a["announcementTime"] / 1000, timezone.utc)
        items.append({"title": _clean(a.get("announcementTitle")), "published_at": L.iso(ts),
                      "url": "https://static.cninfo.com.cn/" + a["adjunctUrl"] if a.get("adjunctUrl") else None,
                      "id": a.get("announcementId")})
    return {"system": "CNINFO", "issuer": org.get("zwjc"), "org_id": org["orgId"], "total": data.get("totalAnnouncement"),
            "items": items, "flags": title_flags(items), "source_url": url + f"?stock={code}"}


def hkex_announcements(fetcher: L.Fetcher, symbol: str, days: int = 180, limit: int = 30,
                       now: datetime | None = None) -> dict[str, Any]:
    code = venue_of(symbol)["code"].zfill(5)
    now = now or L.utc_now()
    pre = f"https://www1.hkexnews.hk/search/prefix.do?&callback=callback&lang=EN&type=A&name={code}&market=SEHK"
    raw = fetcher.get(pre, "venue_static").decode("utf-8", "replace")
    m = re.search(r"callback\((.*)\);?\s*$", raw.strip(), re.S)
    info = json.loads(m.group(1)) if m else {}
    stock = next((s for s in info.get("stockInfo", []) if s.get("code") == code), None)
    if not stock:
        raise KeyError(f"hkex_stock_not_found:{code}")
    start = (now - timedelta(days=days)).strftime("%Y%m%d")
    url = ("https://www1.hkexnews.hk/search/titleSearchServlet.do?sortDir=0&sortByOptions=DateTime&category=0&market=SEHK"
           f"&stockId={stock['stockId']}&documentType=-1&fromDate={start}&toDate={now.strftime('%Y%m%d')}&title=&searchType=0"
           f"&t1code=-2&t2Gcode=-2&t2code=-2&rowRange={limit}&lang=E")
    data = json.loads(fetcher.get(url, "venue_list").decode("utf-8"))
    rows = json.loads(data.get("result") or "[]")
    items = []
    for r in rows:
        when = datetime.strptime(r["DATE_TIME"], "%d/%m/%Y %H:%M")
        items.append({"title": _clean(r.get("LONG_TEXT") or r.get("TITLE")) + (f" — {_clean(r.get('TITLE'))}" if r.get("TITLE") and r.get("LONG_TEXT") else ""),
                      "published_at": _utc(when, "HK"), "url": "https://www1.hkexnews.hk" + r["FILE_LINK"], "id": r.get("NEWS_ID")})
    return {"system": "HKEXnews", "issuer": stock.get("name"), "total": data.get("recordCnt"), "items": items,
            "flags": title_flags(items), "source_url": url}


_TDNET_ROW = re.compile(r'kjTime"[^>]*>([^<]+)</td>.*?kjCode"[^>]*>([^<]+)</td>.*?kjName"[^>]*>([^<]+)</td>.*?kjTitle"[^>]*>'
                        r'<a href="([^"]+)"[^>]*>(.*?)</a>', re.S)


def parse_tdnet_page(html: str, day: date) -> tuple[list[dict[str, Any]], int]:
    total = re.search(r"全(\d+)件", html)
    rows = []
    for t, code, name, href, title in _TDNET_ROW.findall(html):
        hh, mm = (int(x) for x in t.strip().split(":"))
        rows.append({"code": code.strip(), "name": name.strip(), "title": _clean(title),
                     "published_at": _utc(datetime(day.year, day.month, day.day, hh, mm), "JP"),
                     "url": "https://www.release.tdnet.info/inbs/" + href})
    return rows, int(total.group(1)) if total else len(rows)


def tdnet_disclosures(fetcher: L.Fetcher, symbol: str, days: int = 14, now: datetime | None = None) -> dict[str, Any]:
    """TDnet keeps about one month online; older items need EDINET or the issuer IR page."""
    code = venue_of(symbol)["code"]
    td_code = code + "0" if len(code) == 4 else code
    now = now or L.utc_now()
    today = now.astimezone(TZ["JP"]).date()
    days_list = [today - timedelta(days=i) for i in range(min(days, 31) + 1)]
    days_list = [d for d in days_list if d.weekday() < 5]

    def one_day(d: date) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        page, pages = 1, 1
        while page <= pages and page <= 10:
            url = f"https://www.release.tdnet.info/inbs/I_list_{page:03d}_{d.strftime('%Y%m%d')}.html"
            try:
                html = fetcher.get(url, "venue_list" if d >= today - timedelta(days=1) else "venue_doc").decode("utf-8", "replace")
            except L.SourceError:
                break
            rows, total = parse_tdnet_page(html, d)
            pages = max(1, -(-total // 100))
            out += [r for r in rows if r["code"] == td_code]
            page += 1
        return out

    with ThreadPoolExecutor(max_workers=4) as pool:
        items = [r for chunk in pool.map(one_day, days_list) for r in chunk]
    items.sort(key=lambda r: r["published_at"], reverse=True)
    return {"system": "TDnet", "window_days": days, "items": items, "flags": title_flags(items),
            "source_url": "https://www.release.tdnet.info/inbs/I_main_00.html",
            "note": "TDnet keeps ~31 days; use EDINET (EDINET_API_KEY) for statutory filings beyond that."}


def edinet_documents(fetcher: L.Fetcher, symbol: str, days: int = 30, key: str | None = None,
                     now: datetime | None = None) -> dict[str, Any]:
    key = key or os.environ.get("EDINET_API_KEY")
    if not key:
        return {"status": "needs_key", "system": "EDINET", "error": "set EDINET_API_KEY (free registration at EDINET)"}
    code = venue_of(symbol)["code"]
    sec_code = code + "0" if len(code) == 4 else code
    now = now or L.utc_now()
    today = now.astimezone(TZ["JP"]).date()
    dates = [today - timedelta(days=i) for i in range(days + 1)]

    def one(d: date) -> list[dict[str, Any]]:
        url = f"https://api.edinet-fsa.go.jp/api/v2/documents.json?date={d.isoformat()}&type=2&Subscription-Key={key}"
        try:
            data = json.loads(fetcher.get(url, "venue_doc" if d < today else "venue_list").decode("utf-8"))
        except (L.SourceError, ValueError):
            return []
        out = []
        for r in data.get("results") or []:
            if r.get("secCode") == sec_code:
                when = datetime.strptime(r["submitDateTime"], "%Y-%m-%d %H:%M")
                out.append({"title": r.get("docDescription") or "", "published_at": _utc(when, "JP"),
                            "url": f"https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?{r['docID']}", "id": r["docID"]})
        return out

    with ThreadPoolExecutor(max_workers=4) as pool:
        items = [r for chunk in pool.map(one, dates) for r in chunk]
    items.sort(key=lambda r: r["published_at"], reverse=True)
    return {"system": "EDINET", "items": items, "flags": title_flags(items),
            "source_url": "https://api.edinet-fsa.go.jp/api/v2/documents.json"}


def dart_filings(fetcher: L.Fetcher, symbol: str, days: int = 365, key: str | None = None,
                 now: datetime | None = None) -> dict[str, Any]:
    key = key or os.environ.get("DART_API_KEY")
    if not key:
        return {"status": "needs_key", "system": "DART", "error": "set DART_API_KEY (free registration at opendart.fss.or.kr)"}
    stock = venue_of(symbol)["code"]
    now = now or L.utc_now()
    raw = fetcher.get(f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={key}", "venue_static")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        root = ET.fromstring(z.read(z.namelist()[0]))
    corp = next((e.findtext("corp_code") for e in root.iter("list") if (e.findtext("stock_code") or "").strip() == stock), None)
    if not corp:
        raise KeyError(f"dart_corp_code_not_found:{stock}")
    bgn = (now - timedelta(days=days)).strftime("%Y%m%d")
    url = (f"https://opendart.fss.or.kr/api/list.json?crtfc_key={key}&corp_code={corp}&bgn_de={bgn}"
           f"&end_de={now.strftime('%Y%m%d')}&page_count=100")
    data = json.loads(fetcher.get(url, "venue_list").decode("utf-8"))
    if data.get("status") not in ("000", "013"):
        raise KeyError(f"dart_error:{data.get('status')}:{data.get('message')}")
    items = [{"title": r.get("report_nm", "").strip(), "published_at": _utc(datetime.strptime(r["rcept_dt"], "%Y%m%d"), "KR"),
              "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={r['rcept_no']}", "id": r["rcept_no"]}
             for r in data.get("list") or []]
    return {"system": "DART", "corp_code": corp, "items": items, "flags": title_flags(items),
            "source_url": url.replace(key, "<key>")}


def _roc_month(text: str) -> str:
    y, m = int(text[:-2]) + 1911, int(text[-2:])
    return f"{y:04d}-{m:02d}"


def taiwan_monthly_revenue(fetcher: L.Fetcher, symbol: str) -> dict[str, Any]:
    v = venue_of(symbol)
    url = ("https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O" if v["suffix"] == "TWO"
           else "https://openapi.twse.com.tw/v1/opendata/t187ap05_L")
    rows = json.loads(fetcher.get(url, "venue_static").decode("utf-8"))
    row = next((r for r in rows if r.get("公司代號") == v["code"]), None)
    if not row:
        raise KeyError(f"monthly_revenue_not_found:{v['code']}")

    def k(field: str) -> float | None:
        try:
            return float(row[field])
        except (KeyError, ValueError, TypeError):
            return None
    month = _roc_month(row["資料年月"])
    rev = k("營業收入-當月營收")
    return {"system": "TPEx" if v["suffix"] == "TWO" else "TWSE", "company": row.get("公司名稱"), "industry": row.get("產業別"),
            "month": month, "revenue": rev * 1000 if rev is not None else None, "currency": "TWD",
            "mom_pct": round(k("營業收入-上月比較增減(%)"), 2) if k("營業收入-上月比較增減(%)") is not None else None,
            "yoy_pct": round(k("營業收入-去年同月增減(%)"), 2) if k("營業收入-去年同月增減(%)") is not None else None,
            "ytd_yoy_pct": round(k("累計營業收入-前期比較增減(%)"), 2) if k("累計營業收入-前期比較增減(%)") is not None else None,
            "published_at": L.day_iso(f"{int(row['出表日期'][:-4]) + 1911}-{row['出表日期'][-4:-2]}-{row['出表日期'][-2:]}"),
            "unit_note": "source reports thousands of TWD; converted to TWD", "source_url": url}


def exchange_block(fetcher: L.Fetcher, symbol: str, quote: dict[str, Any] | None = None,
                   days: int = 180, now: datetime | None = None) -> dict[str, Any]:
    """Everything exchange-native for one non-US symbol, each part degrading independently."""
    v = venue_of(symbol)
    out: dict[str, Any] = {"venue": v["venue"], "system": v.get("system"), "code": v["code"]}
    if v["venue"] in ("CN", "HK"):
        q2 = L.section(lambda: tencent_quote(fetcher, symbol))
        out["second_quote"] = q2
        out["quote_check"] = cross_check(quote or {}, q2)
        fn = cninfo_announcements if v["venue"] == "CN" else hkex_announcements
        out["disclosures"] = L.section(lambda: fn(fetcher, symbol, days=days, now=now))
    elif v["venue"] == "TW":
        out["monthly_revenue"] = L.section(lambda: taiwan_monthly_revenue(fetcher, symbol))
        out["disclosures"] = {"status": "unavailable", "error": "no_free_api: read MOPS (mops.twse.com.tw) for material information"}
    elif v["venue"] == "JP":
        td = L.section(lambda: tdnet_disclosures(fetcher, symbol, days=31, now=now))
        ed = L.section(lambda: edinet_documents(fetcher, symbol, now=now))
        if ed.get("status") == "ok" and td.get("status") == "ok":
            merged = sorted(td["items"] + ed["items"], key=lambda r: r["published_at"], reverse=True)
            td = {**td, "system": "TDnet + EDINET", "items": merged, "flags": title_flags(merged)}
        out["disclosures"] = td
        out["edinet"] = {k: ed[k] for k in ("status", "error") if k in ed} if ed.get("status") != "ok" else {"status": "ok"}
    elif v["venue"] == "KR":
        out["disclosures"] = L.section(lambda: dart_filings(fetcher, symbol, now=now))
    else:
        out["disclosures"] = {"status": "unavailable", "error": f"no_connector: read {v.get('system')}"}
    return out


# ---------------------------------------------------------------- ETF holdings (SEC N-PORT)
def fund_series(fetcher: L.Fetcher, etf: str) -> dict[str, Any]:
    data = fetcher.json("https://www.sec.gov/files/company_tickers_mf.json", "sec_map")
    fields = data["fields"]
    for row in data["data"]:
        rec = dict(zip(fields, row))
        if str(rec.get("symbol", "")).upper() == etf.upper():
            return {"cik": int(rec["cik"]), "series_id": rec["seriesId"], "class_id": rec["classId"]}
    raise KeyError(f"fund_not_in_sec_map:{etf} (SEC lists open-end funds/ETFs registered under the 1940 Act; UITs such as SPY are absent)")


def parse_nport(raw: bytes) -> dict[str, Any]:
    root = ET.fromstring(raw)
    ns = {"n": root.tag.split("}")[0].strip("{")}
    gen = root.find(".//n:genInfo", ns)
    fund = root.find(".//n:fundInfo", ns)

    def t(node: Any, tag: str) -> str | None:
        el = node.find(f"n:{tag}", ns) if node is not None else None
        return el.text.strip() if el is not None and el.text else None
    holdings = []
    for s in root.findall(".//n:invstOrSec", ns):
        isin = s.find("n:identifiers/n:isin", ns)
        ticker = s.find("n:identifiers/n:ticker", ns)
        try:
            pct = float(t(s, "pctVal") or "nan")
        except ValueError:
            pct = None
        holdings.append({"name": t(s, "name"), "title": t(s, "title"), "cusip": t(s, "cusip"),
                         "isin": isin.get("value") if isin is not None else None,
                         "ticker": ticker.get("value") if ticker is not None else None,
                         "pct": round(pct, 4) if pct == pct and pct is not None else None,
                         "value_usd": float(t(s, "valUSD") or 0), "country": t(s, "invCountry"),
                         "asset_cat": t(s, "assetCat")})
    holdings.sort(key=lambda h: -(h["pct"] or 0))
    return {"fund": t(gen, "seriesName"), "registrant": t(gen, "regName"), "series_id": t(gen, "seriesId"),
            "period_end": t(gen, "repPdDate"), "net_assets_usd": float(t(fund, "netAssets") or 0), "holdings": holdings}


def etf_holdings(fetcher: L.Fetcher, etf: str) -> dict[str, Any]:
    fs = fund_series(fetcher, etf)
    atom = fetcher.get(f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={fs['series_id']}&type=NPORT-P"
                       "&dateb=&owner=include&count=5&output=atom", "sec").decode("utf-8", "replace")
    links = re.findall(r"<filing-href>(.*?)</filing-href>", atom)
    dates = re.findall(r"<filing-date>(.*?)</filing-date>", atom)
    if not links:
        raise KeyError(f"no_nport_filings:{etf}")
    index = fetcher.get(links[0], "sec_doc").decode("utf-8", "replace")
    docs = [d for d in re.findall(r'href="(/Archives/[^"]+primary_doc\.xml)"', index) if "xsl" not in d]
    if not docs:
        raise KeyError("nport_primary_doc_missing")
    url = "https://www.sec.gov" + docs[0]
    parsed = parse_nport(fetcher.get(url, "sec_doc"))
    return {"etf": etf.upper(), **fs, **parsed, "filed": dates[0] if dates else None, "source_url": url,
            "note": "N-PORT holdings are quarter-end and filed ~60 days later; weights are a dated snapshot."}

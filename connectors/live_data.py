#!/usr/bin/env python3
"""Live market and filing connector for suoha-serenity-skill (v7).

This module owns the ONLY network gateway in the skill (``Fetcher``).
``connectors/venues.py`` adds exchange-native sources but routes every request
through the same Fetcher. It performs read-only HTTPS requests (GET, plus a few
form POSTs to public search endpoints) against an explicit host allowlist of
free, public sources and returns JSON with a source URL and timestamps for every
datum, so the agent can cite it and the lens validator can check freshness.

Sources (no API key needed):
  * SEC EDGAR: ticker->CIK map, submissions (filings, 8-K items, 13G/13D,
    Form 4, S-3/424B5 shelf + ATM radar), XBRL companyfacts, full-text search.
  * Yahoo Finance chart + fundamentals-timeseries (global quotes, shares,
    revenue, gross profit) for any exchange suffix (SIVE.ST, 6451.TW, ...).
  * Google News RSS for dated headlines (leads only, never facts).
  * Exchange-native (venues.py): CNINFO (A-shares), HKEXnews (HK), TDnet (JP),
    TWSE/TPEx monthly revenue (TW), Tencent second-source quotes (CN/HK),
    SEC N-PORT ETF holdings; EDINET / DART when EDINET_API_KEY / DART_API_KEY
    are set.

Every value is a lead to verify; this connector never ranks, recommends, or
infers an investment conclusion. Offline or blocked sources degrade to
{"status": "unavailable", "error": ...} instead of failing the whole run.

Usage (fast path first):
  python connectors/live_data.py pack MU --out-dir work/mu            # subject + atlas peers + 10-K/10-Q excerpts
  python connectors/live_data.py pack TSM --adr-ratio 5 --out-dir work/tsm
  python connectors/live_data.py batch MU 000660.KS 005930.KS WDC --out-dir work/peers
  python connectors/live_data.py filing-text --ticker MU --latest 10-K --preset contracts
  python connectors/live_data.py fx TWD
  python connectors/live_data.py snapshot AXTI --out work/AXTI.live.json
  python connectors/live_data.py snapshot SIVE --news-query "Sivers Semiconductors"
  python connectors/live_data.py quote 6451.TW
  python connectors/live_data.py filings AXTI --forms 8-K,424B5,S-3
  python connectors/live_data.py fts '"sole source" OR "single source"' --ticker AXTI
  python connectors/live_data.py news "indium phosphide shortage"
  python connectors/live_data.py exchange 300308.SZ                   # CNINFO announcements + flags + 2nd quote
  python connectors/live_data.py etf-holdings SMH --top 30

Set SEC_USER_AGENT="Your Name your@email" (SEC fair-access policy).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import threading
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

CONNECTOR_VERSION = "8.0.1"
ALLOWED_HOSTS = frozenset({
    "www.sec.gov",
    "data.sec.gov",
    "efts.sec.gov",
    "query1.finance.yahoo.com",
    "query2.finance.yahoo.com",
    "news.google.com",
    # exchange disclosure systems and second-source quotes (connectors/venues.py)
    "qt.gtimg.cn",                 # Tencent quotes: A-shares, Hong Kong (second source)
    "www.cninfo.com.cn",           # CNINFO: mainland China announcements (CSRC-designated)
    "static.cninfo.com.cn",        # CNINFO announcement PDFs
    "www1.hkexnews.hk",            # HKEXnews: Hong Kong announcements
    "openapi.twse.com.tw",         # TWSE OpenAPI: monthly revenue, listed companies
    "www.tpex.org.tw",             # TPEx OpenAPI: monthly revenue for OTC-listed companies
    "www.release.tdnet.info",      # TDnet: Japan timely disclosure
    "api.edinet-fsa.go.jp",        # EDINET: Japan statutory filings (free key)
    "opendart.fss.or.kr",          # DART: Korea filings (free key)
    # v7.1: A-share / Hong Kong statements (aggregator; connectors/cnhk_fin.py)
    "datacenter.eastmoney.com",    # Eastmoney F10 datacenter: normalised CNINFO/HKEX periodic-report data
})
# Hosts whose public search endpoints only accept a form POST.  The body is a
# read-only query (keyword / date range); every other host is GET-only.
FORM_POST_HOSTS = frozenset({
    "www.cninfo.com.cn",
})
DEFAULT_UA = "suoha-serenity-skill/7.1 research contact@example.com"  # override via SEC_USER_AGENT
BROWSER_UA = "Mozilla/5.0"
TIMEOUT = 20
CACHE_TTL = {"sec_map": 86400, "sec": 3600, "sec_doc": 7 * 86400, "yahoo": 600, "news": 900, "efts": 3600,
             "venue_quote": 300, "venue_list": 3600, "venue_static": 86400, "venue_doc": 7 * 86400}
MAX_WORKERS = 6

DILUTION_FORMS = {"S-3", "S-3ASR", "S-3/A", "S-1", "S-1/A", "F-3", "F-3ASR", "F-1", "F-1/A",
                  "424B5", "424B3", "424B4", "424B7", "EFFECT"}
OWNERSHIP_FORMS = {"SC 13G", "SC 13G/A", "SC 13D", "SC 13D/A", "SCHEDULE 13G", "SCHEDULE 13G/A",
                   "SCHEDULE 13D", "SCHEDULE 13D/A"}
INSIDER_FORMS = {"4", "4/A", "144"}
REPORT_FORMS = {"10-K", "10-Q", "20-F", "40-F", "6-K", "10-K/A", "10-Q/A"}
EIGHT_K_ITEMS = {
    "1.01": "material definitive agreement", "1.02": "termination of material agreement",
    "2.01": "acquisition/disposition", "2.02": "results of operations", "2.03": "new debt obligation",
    "3.01": "listing/delisting notice", "3.02": "unregistered equity sale", "3.03": "modification of holder rights",
    "5.02": "officer/director change", "5.03": "charter/bylaw amendment", "7.01": "Reg FD disclosure",
    "8.01": "other events", "9.01": "exhibits",
}
DOCTRINE_FTS = {
    "supply_concentration": '"sole source" OR "single source" OR "sole supplier" OR "single supplier" OR "limited number of suppliers"',
    "customer_concentration": '"largest customer" OR "one customer accounted" OR "two customers accounted" OR "customer concentration"',
    "atm_program": '"at-the-market" OR "at the market offering" OR "equity distribution agreement" OR "sales agreement"',
    "capacity_signal": '"capacity constrained" OR "supply constrained" OR "lead times" OR "sold out" OR "allocation"',
    "going_concern": '"substantial doubt" OR "going concern"',
}

SEC_REVENUE_TAGS = ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet",
                    "RevenueFromContractWithCustomerIncludingAssessedTax", "Revenue")
SEC_TAGS = {
    "gross_profit": ("GrossProfit",),
    "cost_of_revenue": ("CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfSales"),
    "operating_income": ("OperatingIncomeLoss", "ProfitLossFromOperatingActivities"),
    "net_income": ("NetIncomeLoss", "ProfitLoss"),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities", "CashFlowsFromUsedInOperatingActivities"),
    "capex": ("PaymentsToAcquirePropertyPlantAndEquipment", "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"),
    "rnd": ("ResearchAndDevelopmentExpense",),
    # v7.1: quality-of-earnings and shareholder-return lines
    "sbc": ("ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"),
    "dividends_paid": ("PaymentsOfDividends", "PaymentsOfDividendsCommonStock"),
    "buybacks": ("PaymentsForRepurchaseOfCommonStock",),
}
SEC_INSTANT_TAGS = {
    "cash": ("CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "CashAndCashEquivalents"),
    "short_term_investments": ("ShortTermInvestments", "MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"),
    "total_debt": ("LongTermDebt", "LongTermDebtNoncurrent", "ConvertibleNotesPayable", "Borrowings"),
    "inventory": ("InventoryNet", "Inventories"),
    "equity": ("StockholdersEquity", "Equity"),
    # v7.1: balance-sheet quality
    "total_assets": ("Assets",),
    "total_liabilities": ("Liabilities",),
    "receivables": ("AccountsReceivableNetCurrent", "ReceivablesNetCurrent", "TradeAndOtherCurrentReceivables"),
    "goodwill": ("Goodwill",),
    "contract_liabilities": ("ContractWithCustomerLiabilityCurrent", "ContractWithCustomerLiability", "DeferredRevenueCurrent"),
}
FPI_FORMS = {"20-F", "20-F/A", "40-F", "40-F/A", "6-K"}
DOMESTIC_REPORT_FORMS = {"10-K", "10-Q", "10-K/A", "10-Q/A"}
# Yahoo quotes some listings in minor units; prices are converted to the major unit.
MINOR_UNITS = {"GBp": ("GBP", 100.0), "GBX": ("GBP", 100.0), "ZAc": ("ZAR", 100.0), "ZAC": ("ZAR", 100.0),
               "ILA": ("ILS", 100.0)}
# Listings where "price x reported shares" is known to mis-state equity value.
#   approx     -> classes convert ~1:1; summed cover counts are a fair approximation
#   partial    -> another listed class is excluded; value is understated
#   unreliable -> classes are not economically equal; market cap is withheld
SHARE_CLASS_NOTES = {
    "GOOGL": ("approx", "Alphabet Class A/B/C cover counts are summed; one class price x all classes approximates group value."),
    "GOOG": ("approx", "Alphabet Class A/B/C cover counts are summed; one class price x all classes approximates group value."),
    "META": ("approx", "Meta Class A + unlisted Class B (1:1 convertible) are summed."),
    "BRK-A": ("unreliable", "Berkshire Class B = 1/1500 Class A; summed cover counts are not comparable. Compute A-equivalent shares by hand."),
    "BRK-B": ("unreliable", "Berkshire Class B = 1/1500 Class A; summed cover counts are not comparable. Compute B-equivalent shares by hand."),
    "005930.KS": ("partial", "Samsung Electronics preferred shares (005935.KS) are excluded; common-only value understates group equity."),
    "005935.KS": ("partial", "Samsung preferred line only; add common (005930.KS) for group value."),
    "005380.KS": ("partial", "Hyundai Motor preferred lines (005385/005387/005389.KS) are excluded."),
    "RDS-A": ("unreliable", "Legacy dual-line listing; use the unified SHEL line."),
}
FILING_TERM_PRESETS: dict[str, dict[str, str]] = {
    "contracts": {
        "take_or_pay": r"take[- ]or[- ]pay",
        "remaining_performance_obligations": r"remaining performance obligations?",
        "customer_deposits": r"customer (?:deposits?|prepayments?|advances?)|advances? from customers|contract liabilit(?:y|ies)",
        "prepayment": (r"(?:customer|advance|capacity|supply|wafer)[^.]{0,60}prepay(?:ment|ments|ed)\b"
                       r"|prepay(?:ment|ments|ed)\b[^.]{0,60}(?:customer|capacity|supply|wafer)"),
        "capacity_reservation": r"capacity (?:reservation|reserve|commitment)s?|reserv(?:e|ed|ation of) (?:production |manufacturing )?capacity",
        "long_term_supply_agreement": r"long[- ]term (?:supply|purchase|volume) (?:agreement|arrangement|contract|commitment)s?",
        "sole_source": r"sole[- ]source|single[- ]source|sole supplier|single supplier",
        "customer_concentration": (r"(?:one|two|three|four|five|\d+) (?:of our )?customers? (?:each )?accounted for|largest customers?\b"
                                   r"|customers?[^.]{0,40}accounted for (?:approximately |about |more than )?\d+(?:\.\d+)?%"),
    },
    "risk": {
        "going_concern": r"substantial doubt[^.]{0,120}going concern|going concern (?:basis|uncertaint|qualification|explanatory)",
        "material_weakness": r"(?:identified|disclosed|existence of|remediat\w*)[^.]{0,40}material weakness|material weakness(?:es)? (?:in|was|were|has|have)\b",
        "export_controls": r"export (?:control|license|licence|restriction)s?",
        "at_the_market": r"at[- ]the[- ]market (?:offering|program|sales)|equity distribution agreement",
        "default_covenant": r"covenant (?:breach|violation|waiver)|event of default",
    },
}
FILING_TERM_PRESETS["all"] = {**FILING_TERM_PRESETS["contracts"], **FILING_TERM_PRESETS["risk"]}

YAHOO_TYPES = ("quarterlyOrdinarySharesNumber", "quarterlyTotalRevenue", "quarterlyGrossProfit",
               "quarterlyOperatingIncome", "quarterlyNetIncome", "quarterlyCashAndCashEquivalents",
               "quarterlyTotalDebt", "quarterlyOperatingCashFlow", "quarterlyCapitalExpenditure",
               "annualTotalRevenue", "annualGrossProfit", "quarterlyMarketCap")


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if dt else None


def day_iso(day: str | None) -> str | None:
    """'2026-03-31' -> '2026-03-31T00:00:00Z' (lens evidence uses ISO date-times)."""
    if not day:
        return None
    return day if "T" in day else f"{day}T00:00:00Z"


class SourceError(RuntimeError):
    pass


class _AllowlistRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse to follow a redirect that leaves the HTTPS allow-list."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        target = urllib.parse.urlparse(newurl)
        if target.scheme != "https" or target.hostname not in ALLOWED_HOSTS:
            raise SourceError(f"redirect_off_allowlist:{target.hostname}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_AllowlistRedirect)


class Fetcher:
    """Allowlisted, cached, read-only HTTPS GET. Inject a fake in tests."""

    def __init__(self, cache_dir: Path | None = None, offline: bool = False, sec_ua: str | None = None):
        self.cache_dir = cache_dir
        self.offline = offline
        self.sec_ua = sec_ua or os.environ.get("SEC_USER_AGENT") or DEFAULT_UA
        self._last_sec = 0.0
        self._lock = threading.Lock()
        self._url_locks: dict[str, threading.Lock] = {}
        self._mem: dict[str, bytes] = {}  # per-process memo: parallel callers share one request per URL
        self.log: list[dict[str, Any]] = []

    def _note(self, entry: dict[str, Any]) -> None:
        with self._lock:
            self.log.append(entry)

    def _cache_path(self, url: str, form: bytes | None = None) -> Path | None:
        if not self.cache_dir:
            return None
        key = url.encode() + (b"\n" + form if form else b"")
        return self.cache_dir / (hashlib.sha256(key).hexdigest()[:32] + ".cache")

    def get(self, url: str, kind: str, form: dict[str, str] | None = None) -> bytes:
        """GET, or a form POST for search endpoints that only accept POST (still read-only queries)."""
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise SourceError(f"host_not_allowlisted:{parsed.hostname}")
        if form is not None and parsed.hostname not in FORM_POST_HOSTS:
            raise SourceError(f"form_post_not_allowlisted:{parsed.hostname}")
        data = urllib.parse.urlencode(form).encode() if form is not None else None
        memo_key = url + ("\n" + data.decode() if data else "")
        with self._lock:
            url_lock = self._url_locks.setdefault(memo_key, threading.Lock())
        with url_lock:
            if memo_key in self._mem:
                self._note({"url": url, "cache": "memo"})
                return self._mem[memo_key]
            body = self._get(url, kind, parsed) if data is None else self._get(url, kind, parsed, data)
            self._mem[memo_key] = body
            return body

    def _get(self, url: str, kind: str, parsed: urllib.parse.ParseResult, data: bytes | None = None) -> bytes:
        cache = self._cache_path(url, data)
        ttl = CACHE_TTL.get(kind, 600)
        if cache and cache.is_file() and (time.time() - cache.stat().st_mtime) < ttl:
            self._note({"url": url, "cache": "hit"})
            return cache.read_bytes()
        if self.offline:
            if cache and cache.is_file():
                self._note({"url": url, "cache": "stale_offline"})
                return cache.read_bytes()
            raise SourceError("offline_mode_no_cache")
        is_sec = parsed.hostname.endswith("sec.gov")
        if is_sec:  # SEC fair access: <= 10 req/s, enforced across threads
            with self._lock:
                wait = 0.12 - (time.time() - self._last_sec)
                if wait > 0:
                    time.sleep(wait)
                self._last_sec = time.time()
        headers = {"User-Agent": self.sec_ua if is_sec else BROWSER_UA, "Accept-Encoding": "gzip"}
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
                with _OPENER.open(req, timeout=TIMEOUT) as resp:  # noqa: S310 (allowlisted)
                    final_host = urllib.parse.urlparse(resp.geturl()).hostname
                    if final_host not in ALLOWED_HOSTS:
                        raise SourceError(f"redirect_off_allowlist:{final_host}")
                    body = resp.read()
                    if resp.headers.get("Content-Encoding") == "gzip":
                        body = gzip.decompress(body)
                if cache:
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    tmp = cache.with_suffix(f".{threading.get_ident()}.tmp")
                    tmp.write_bytes(body)
                    os.replace(tmp, cache)  # atomic: parallel readers never see a half-written file
                self._note({"url": url, "cache": "miss"})
                return body
            except urllib.error.HTTPError as exc:
                last_exc = exc
                if exc.code in (404, 401, 403):
                    break
                if exc.code == 429 and "query1.finance.yahoo.com" in url:
                    url = url.replace("query1.finance.yahoo.com", "query2.finance.yahoo.com")
                time.sleep(1.5 * (attempt + 1))
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_exc = exc
                time.sleep(1.0 + attempt)
        raise SourceError(f"fetch_failed:{type(last_exc).__name__}:{last_exc}")

    def json(self, url: str, kind: str) -> Any:
        return json.loads(self.get(url, kind).decode("utf-8"))


def section(fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Run one source; never let one failure kill the snapshot."""
    try:
        out = fn()
        out.setdefault("status", "ok")
        return out
    except (SourceError, KeyError, ValueError, TypeError, IndexError, ET.ParseError) as exc:
        return {"status": "unavailable", "error": f"{type(exc).__name__}:{exc}"}


# ---------------------------------------------------------------- symbols
def resolve_symbol(ticker: str, yahoo: str | None = None) -> dict[str, Any]:
    if yahoo:
        suffix = yahoo.split(".", 1)[1] if "." in yahoo else ""
        return {"input": ticker, "symbol": yahoo, "us_listed": suffix == "", "review_needed": False,
                "reason": "explicit --yahoo symbol"}
    try:
        from ticker_normalizer import SEED_PATH, load_aliases, normalize  # type: ignore
        res = normalize(ticker, load_aliases([SEED_PATH]))
    except Exception as exc:  # pragma: no cover - normalizer missing
        res = {"input": ticker, "symbol": ticker.upper().lstrip("$"), "review_needed": True, "reason": f"normalizer_error:{exc}"}
    symbol = res.get("symbol") or ticker.strip().upper().lstrip("$")
    res["symbol"] = symbol
    # FX / index style Yahoo symbols (KRW=X, ^SOX) are never SEC registrants.
    res["us_listed"] = not any(ch in symbol for ch in ".=^")
    return res


def sec_cik(fetcher: Fetcher, symbol: str) -> dict[str, Any]:
    data = fetcher.json("https://www.sec.gov/files/company_tickers_exchange.json", "sec_map")
    fields = data["fields"]
    want = symbol.upper().replace(".", "-")
    for row in data["data"]:
        rec = dict(zip(fields, row))
        if str(rec.get("ticker", "")).upper() == want:
            return {"cik": int(rec["cik"]), "name": rec.get("name"), "exchange": rec.get("exchange"),
                    "source_url": "https://www.sec.gov/files/company_tickers_exchange.json"}
    raise KeyError(f"ticker_not_in_sec_map:{symbol}")


# ---------------------------------------------------------------- yahoo
def yahoo_quote(fetcher: Fetcher, symbol: str) -> dict[str, Any]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range=1y&interval=1d"
    data = fetcher.json(url, "yahoo")
    result = (data.get("chart") or {}).get("result")
    if not result:
        raise KeyError(f"yahoo_no_result:{(data.get('chart') or {}).get('error')}")
    r = result[0]
    meta = r["meta"]
    ts = r.get("timestamp") or []
    closes = ((r.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    series = [(t, c) for t, c in zip(ts, closes) if c is not None]
    price = meta.get("regularMarketPrice") or (series[-1][1] if series else None)
    when = meta.get("regularMarketTime") or (series[-1][0] if series else None)

    def ret(days: int) -> float | None:
        if not series or price is None:
            return None
        cutoff = series[-1][0] - days * 86400
        past = [c for t, c in series if t <= cutoff]
        return round((price / past[-1] - 1) * 100, 2) if past else None

    hi = max((c for _, c in series), default=None)
    lo = min((c for _, c in series), default=None)
    return {
        "symbol": symbol, "name": meta.get("longName") or meta.get("shortName"),
        "exchange": meta.get("fullExchangeName") or meta.get("exchangeName"),
        "currency": meta.get("currency"), "price": price,
        "price_as_of": iso(datetime.fromtimestamp(when, timezone.utc)) if when else None,
        "fifty_two_week_high": meta.get("fiftyTwoWeekHigh") or hi,
        "fifty_two_week_low": meta.get("fiftyTwoWeekLow") or lo,
        "drawdown_from_52w_high_pct": round((price / (meta.get("fiftyTwoWeekHigh") or hi) - 1) * 100, 2) if price and (meta.get("fiftyTwoWeekHigh") or hi) else None,
        "return_pct": {"1m": ret(30), "3m": ret(91), "6m": ret(182), "1y": ret(360)},
        "source_url": url,
    }


def daily_closes(fetcher: Fetcher, symbol: str, range_: str = "5y") -> list[tuple[str, float]]:
    """Daily closes as (YYYY-MM-DD, close), oldest first; used by forward tracking."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range={range_}&interval=1d"
    data = fetcher.json(url, "yahoo")
    result = (data.get("chart") or {}).get("result")
    if not result:
        raise KeyError(f"yahoo_no_result:{(data.get('chart') or {}).get('error')}")
    r = result[0]
    ts = r.get("timestamp") or []
    closes = ((r.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    return [(datetime.fromtimestamp(t, timezone.utc).date().isoformat(), float(c))
            for t, c in zip(ts, closes) if c is not None]


def yahoo_fundamentals(fetcher: Fetcher, symbol: str, now: datetime | None = None) -> dict[str, Any]:
    now = now or utc_now()
    p2 = (int(now.timestamp()) // 86400 + 1) * 86400  # day-rounded so the cache key is stable
    p1 = p2 - 86400 * 900
    url = ("https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/"
           f"{urllib.parse.quote(symbol)}?type={','.join(YAHOO_TYPES)}&period1={p1}&period2={p2}")
    data = fetcher.json(url, "yahoo")
    out: dict[str, list[dict[str, Any]]] = {}
    for item in data["timeseries"]["result"]:
        typ = item["meta"]["type"][0]
        rows = [x for x in (item.get(typ) or []) if x]
        out[typ] = [{"as_of": x["asOfDate"], "value": x["reportedValue"]["raw"],
                     "currency": x.get("currencyCode")} for x in rows]
    shares = (out.get("quarterlyOrdinarySharesNumber") or [])
    rev_q = out.get("quarterlyTotalRevenue") or []
    gp_q = out.get("quarterlyGrossProfit") or []
    summary: dict[str, Any] = {}
    if shares:
        summary["shares_outstanding"] = shares[-1]["value"]
        summary["shares_as_of"] = shares[-1]["as_of"]
        if len(shares) >= 5 and shares[-5]["value"]:
            summary["share_count_change_pct_vs_4_obs_ago"] = round((shares[-1]["value"] / shares[-5]["value"] - 1) * 100, 2)
    if rev_q:
        summary["revenue_quarterly"] = rev_q[-8:]
        summary["reporting_currency"] = rev_q[-1].get("currency")
        summary["revenue_ttm"] = ttm(rev_q)
        summary["revenue_yoy_pct"] = yoy_pct(rev_q)
        if summary["revenue_ttm"] is None:
            summary["revenue_ttm_note"] = "quarter gap in provider series; TTM not computed"
        if len(rev_q) >= 2 and rev_q[-2]["value"] and 80 <= (_d(rev_q[-1]) - _d(rev_q[-2])).days <= 100:
            summary["revenue_qoq_pct"] = round((rev_q[-1]["value"] / rev_q[-2]["value"] - 1) * 100, 2)
    rev_a = out.get("annualTotalRevenue") or []
    if rev_a:
        summary["revenue_annual_latest"] = rev_a[-1]
        summary.setdefault("reporting_currency", rev_a[-1].get("currency"))
        if len(rev_a) >= 2 and rev_a[-2]["value"]:
            summary["revenue_annual_yoy_pct"] = round((rev_a[-1]["value"] / rev_a[-2]["value"] - 1) * 100, 2)
        gm_a = _margins(rev_a, out.get("annualGrossProfit") or [])
        if len(gm_a) >= 2:
            summary["gross_margin_annual_change_pp"] = round(gm_a[-1]["pct"] - gm_a[-2]["pct"], 2)
    gm = _margins(rev_q, gp_q)
    if gm:
        summary["gross_margin_quarterly"] = gm[-8:]
        prior = [g for g in gm[:-1] if 350 <= (_d(gm[-1]) - _d(g)).days <= 380]
        if prior:
            summary["gross_margin_change_yoy_pp"] = round(gm[-1]["pct"] - prior[-1]["pct"], 2)
        if rev_q and gm[-1]["as_of"] != rev_q[-1]["as_of"]:
            summary["gross_margin_period_lag"] = {"gross_margin_end": gm[-1]["as_of"], "revenue_end": rev_q[-1]["as_of"]}
    return {"provider": "yahoo_timeseries", "summary": summary, "series": out, "source_url": url}


def _d(x: dict[str, Any]) -> datetime:
    return datetime.fromisoformat((x.get("end") or x.get("as_of"))[:10])


def ttm(series: list[dict[str, Any]]) -> float | None:
    """Sum of the last four quarters only if they are consecutive (no gaps)."""
    if len(series) < 4:
        return None
    last4 = series[-4:]
    gaps = [(_d(b) - _d(a)).days for a, b in zip(last4, last4[1:])]
    return sum(x["value"] for x in last4) if all(80 <= g <= 100 for g in gaps) else None


def yoy_pct(series: list[dict[str, Any]]) -> float | None:
    """Latest quarter vs the quarter ~one year earlier (date-matched, not index-matched)."""
    if len(series) < 2:
        return None
    last = series[-1]
    for x in reversed(series[:-1]):
        if 350 <= (_d(last) - _d(x)).days <= 380 and x["value"]:
            return round((last["value"] / x["value"] - 1) * 100, 2)
    return None


def _margins(rev: list[dict[str, Any]], num: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by = {x["as_of"]: x["value"] for x in rev}
    res = []
    for x in num:
        r = by.get(x["as_of"])
        if r:
            res.append({"as_of": x["as_of"], "pct": round(x["value"] / r * 100, 2)})
    return res


# ---------------------------------------------------------------- SEC
def sec_submissions(fetcher: Fetcher, cik: int, limit: int = 250) -> dict[str, Any]:
    url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
    data = fetcher.json(url, "sec")
    r = data["filings"]["recent"]
    rows = []
    for i in range(min(limit, len(r["form"]))):
        acc = r["accessionNumber"][i]
        doc = r["primaryDocument"][i]
        rows.append({
            "form": r["form"][i], "filed": r["filingDate"][i],
            "report_date": r.get("reportDate", [""] * (i + 1))[i] or None,
            "items": [s for s in (r.get("items", [""] * (i + 1))[i] or "").split(",") if s],
            "accession": acc,
            "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{doc}" if doc else
                   f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/",
            "description": r.get("primaryDocDescription", [""] * (i + 1))[i],
        })
    return {"name": data.get("name"), "sic": data.get("sicDescription"), "sic_code": data.get("sic"), "exchanges": data.get("exchanges"),
            "fiscal_year_end": data.get("fiscalYearEnd"), "state_of_incorporation": data.get("stateOfIncorporation"),
            "filings": rows, "source_url": url}


def filing_radar(subs: dict[str, Any], now: datetime | None = None, days: int = 400) -> dict[str, Any]:
    """Group recent filings into doctrine radars: dilution, ownership, insider, 8-K events."""
    now = now or utc_now()
    floor = (now - timedelta(days=days)).date().isoformat()
    recent = [f for f in subs["filings"] if f["filed"] >= floor]
    dilution = [f for f in recent if f["form"] in DILUTION_FORMS]
    ownership = [f for f in recent if f["form"] in OWNERSHIP_FORMS]
    insider = [f for f in recent if f["form"] in INSIDER_FORMS]
    reports = [f for f in recent if f["form"] in REPORT_FORMS]
    events = []
    for f in recent:
        if f["form"].startswith("8-K") or f["form"] == "6-K":
            events.append({**f, "item_labels": [EIGHT_K_ITEMS.get(i, i) for i in f["items"]]})
    flags = []
    shelf = [f for f in dilution if f["form"] in {"S-3", "S-3ASR", "F-3", "F-3ASR", "S-1", "F-1"}]
    takedowns = [f for f in dilution if f["form"].startswith("424B")]
    if shelf:
        flags.append({"flag": "shelf_registration_on_file", "count": len(shelf), "latest": shelf[0]["filed"],
                      "doctrine": "PB-FIN-01", "check": "Read the S-3/424B5 for size vs market cap and whether an ATM sales agreement exists."})
    def _near_101(filed: str) -> bool:
        d0 = datetime.fromisoformat(filed)
        return any("1.01" in e["items"] and abs((datetime.fromisoformat(e["filed"]) - d0).days) <= 2 for e in events)

    underwritten = [f for f in takedowns if _near_101(f["filed"])]
    for f in takedowns:
        f["likely_underwritten"] = f in underwritten
    if len(takedowns) >= 2:
        flags.append({"flag": "repeated_prospectus_takedowns", "count": len(takedowns), "latest": takedowns[0]["filed"],
                      "likely_underwritten": len(underwritten), "doctrine": "PB-FIN-02",
                      "check": ("Serial 424B supplements: an 8-K item 1.01 within 2 days usually marks an underwritten "
                                "follow-on (read the price vs today); without it, suspect an active ATM and size the overhang.")})
    if any("3.02" in e["items"] for e in events):
        flags.append({"flag": "unregistered_equity_sale_8k_3_02", "doctrine": "PB-FIN-03",
                      "check": "Private placement/PIPE: who bought, price vs market, lockup, warrants."})
    if any("1.01" in e["items"] for e in events):
        flags.append({"flag": "material_agreement_8k_1_01", "doctrine": "PB-SIG-02",
                      "check": "Open the 8-K exhibit: customer/supply/financing agreement? counterparty quality?"})
    if ownership:
        flags.append({"flag": "beneficial_owner_filings", "count": len(ownership), "latest": ownership[0]["filed"],
                      "doctrine": "PB-SIG-09", "check": "New 13G/13D filers = institutional discovery or activist; read filer name and %."})
    form4 = [f for f in insider if f["form"].startswith("4")]
    if form4:
        flags.append({"flag": "insider_form4_activity", "count": len(form4), "latest": form4[0]["filed"],
                      "doctrine": "PB-SIG-10", "check": "Classify open-market buys (code P) vs sales/grants; buys after a run-up are rarer signals."})
    return {"window_days": days, "dilution": dilution[:20], "ownership": ownership[:20], "insider": insider[:30],
            "reports": reports[:8], "events_8k": events[:25], "flags": flags}


def _sec_series(facts: dict[str, Any], tags: tuple[str, ...], instant: bool) -> tuple[str | None, list[dict[str, Any]]]:
    """Rows for the candidate tag with the most recent period end.

    Filers switch tags over time (e.g. CostOfRevenue -> CostOfGoodsAndServicesSold);
    taking the first tag that has any rows silently returns a stale series.
    """
    found = [(name, rows, max(r["end"] for r in rows)) for name, rows in _sec_series_all(facts, tags, instant)]
    if not found:
        return None, []
    newest = max(end for _, _, end in found)
    floor = (datetime.fromisoformat(newest) - timedelta(days=100)).date().isoformat()
    for name, rows, end in found:  # priority order, but never a tag that stopped ~a quarter+ ago
        if end >= floor:
            return name, rows
    return found[0][0], found[0][1]


def _sec_series_all(facts: dict[str, Any], tags: tuple[str, ...], instant: bool):
    for taxonomy in ("us-gaap", "ifrs-full"):
        pool = facts.get("facts", {}).get(taxonomy, {})
        for tag in tags:
            node = pool.get(tag)
            if not node:
                continue
            for unit, vals in node.get("units", {}).items():
                if "/" in unit:
                    continue
                rows = []
                for v in vals:
                    if v.get("form") not in {"10-K", "10-Q", "20-F", "40-F", "10-K/A", "10-Q/A", "6-K"}:
                        continue
                    if instant:
                        if "start" in v:
                            continue
                        rows.append({"end": v["end"], "value": v["val"], "filed": v.get("filed"), "unit": unit})
                    else:
                        if "start" not in v:
                            continue
                        span = (datetime.fromisoformat(v["end"]) - datetime.fromisoformat(v["start"])).days
                        rows.append({"start": v["start"], "end": v["end"], "days": span, "value": v["val"],
                                     "filed": v.get("filed"), "unit": unit})
                if rows:
                    yield f"{taxonomy}:{tag}", rows
                    break


def _quarterly(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Distinct quarterly values by period end.

    Uses explicit ~3-month facts first; otherwise derives quarters from
    year-to-date chains sharing a fiscal-year start (6M-3M, 9M-6M, FY-9M),
    which is how cash-flow statements are reported in 10-Qs.
    """
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for r in sorted(rows, key=lambda x: x.get("filed") or ""):
        latest[(r["start"], r["end"])] = r  # later filings (restatements) win
    q: dict[str, dict[str, Any]] = {}
    for r in latest.values():
        if 80 <= r["days"] <= 100:
            q[r["end"]] = {**r}
    by_start: dict[str, list[dict[str, Any]]] = {}
    for r in latest.values():
        if 80 <= r["days"] <= 380:
            by_start.setdefault(r["start"], []).append(r)
    for start, chain in by_start.items():
        chain.sort(key=lambda x: x["days"])
        prev = None
        for r in chain:
            if prev is not None and r["end"] not in q and 70 <= (r["days"] - prev["days"]) <= 110:
                q[r["end"]] = {**r, "days": r["days"] - prev["days"], "value": r["value"] - prev["value"], "derived": "YTD-diff"}
            prev = r
    return [{"end": k, "value": v["value"], "unit": v["unit"], **({"derived": v["derived"]} if "derived" in v else {})}
            for k, v in sorted(q.items())]


def sec_facts(fetcher: Fetcher, cik: int) -> dict[str, Any]:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    facts = fetcher.json(url, "sec")
    out: dict[str, Any] = {"provider": "sec_companyfacts", "source_url": url, "tags": {}}
    tag, rows = _sec_series(facts, SEC_REVENUE_TAGS, instant=False)
    rev_q = _quarterly(rows) if rows else []
    # Some filers switch revenue tags over time; merge additional tags for missing periods.
    if rows:
        for alt in SEC_REVENUE_TAGS:
            t2, r2 = _sec_series(facts, (alt,), instant=False)
            if t2 and t2 != tag and r2:
                have = {x["end"] for x in rev_q}
                rev_q = sorted(rev_q + [x for x in _quarterly(r2) if x["end"] not in have], key=lambda x: x["end"])
    out["tags"]["revenue"] = tag
    series: dict[str, list[dict[str, Any]]] = {"revenue": rev_q}
    for key, tags in SEC_TAGS.items():
        t, r = _sec_series(facts, tags, instant=False)
        out["tags"][key] = t
        series[key] = _quarterly(r) if r else []
    for key, tags in SEC_INSTANT_TAGS.items():
        t, r = _sec_series(facts, tags, instant=True)
        out["tags"][key] = t
        dedup: dict[str, dict[str, Any]] = {}
        for x in sorted(r, key=lambda x: x.get("filed") or ""):
            dedup[x["end"]] = {"end": x["end"], "value": x["value"], "unit": x["unit"]}
        series[key] = [dedup[k] for k in sorted(dedup)]
    dei = facts.get("facts", {}).get("dei", {}).get("EntityCommonStockSharesOutstanding", {})
    series["shares_outstanding_dei"] = group_dei_shares(dei)[-8:]
    out["series"] = {k: v[-12:] for k, v in series.items()}
    out["summary"] = summarize_sec(series)
    return out


def group_dei_shares(dei: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per cover-page date.  Multi-class issuers (GOOGL, META, BRK)
    report one dei value per class on the same end/accession; those are summed
    and flagged instead of keeping an arbitrary single class."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for _unit, vals in dei.get("units", {}).items():
        for v in vals:
            key = (v["end"], v.get("accn") or v.get("filed") or "")
            groups.setdefault(key, []).append(v)
    by_end: dict[str, dict[str, Any]] = {}
    for (end, _acc), vals in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[1][0].get("filed") or "")):
        distinct = sorted({int(v["val"]) for v in vals})
        row = {"end": end, "value": sum(distinct), "filed": vals[0].get("filed"), "form": vals[0].get("form")}
        if len(distinct) > 1:
            row["classes"] = len(distinct)
            row["class_values"] = distinct
        by_end[end] = row  # later filing for the same end wins
    return [by_end[k] for k in sorted(by_end)]


def summarize_sec(series: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    s: dict[str, Any] = {}
    rev = series.get("revenue") or []
    if rev:
        s["revenue_latest_quarter"] = rev[-1]
        s["reporting_currency"] = rev[-1]["unit"]
        s["revenue_ttm"] = ttm(rev)
        s["revenue_yoy_pct"] = yoy_pct(rev)
        if len(rev) >= 2 and rev[-2]["value"]:
            s["revenue_qoq_pct"] = round((rev[-1]["value"] / rev[-2]["value"] - 1) * 100, 2)
    gp = series.get("gross_profit") or []
    if rev and gp and gp[-1]["end"] < rev[-1]["end"] and series.get("cost_of_revenue") and series["cost_of_revenue"][-1]["end"] == rev[-1]["end"]:
        gp = []  # GrossProfit tag went stale; rebuild from revenue - cost
    if not gp and series.get("cost_of_revenue") and rev:
        cost = {x["end"]: x["value"] for x in series["cost_of_revenue"]}
        gp = [{"end": x["end"], "value": x["value"] - cost[x["end"]], "unit": x["unit"]} for x in rev if x["end"] in cost]
    if gp and rev:
        by = {x["end"]: x["value"] for x in rev}
        gm = [{"end": x["end"], "pct": round(x["value"] / by[x["end"]] * 100, 2)} for x in gp if by.get(x["end"])]
        s["gross_margin_quarterly"] = gm[-8:]
        if gm and gm[-1]["end"] != rev[-1]["end"]:
            s["gross_margin_period_lag"] = {"gross_margin_end": gm[-1]["end"], "revenue_end": rev[-1]["end"]}
        prior = [g for g in gm[:-1] if 350 <= (_d(gm[-1]) - _d(g)).days <= 380]
        if prior:
            s["gross_margin_change_yoy_pp"] = round(gm[-1]["pct"] - prior[-1]["pct"], 2)
    op = series.get("operating_income") or []
    if op and rev:
        by = {x["end"]: x["value"] for x in rev}
        s["operating_margin_quarterly"] = [{"end": x["end"], "pct": round(x["value"] / by[x["end"]] * 100, 2)}
                                           for x in op if by.get(x["end"])][-8:]
    cash = (series.get("cash") or [])
    sti = {x["end"]: x["value"] for x in (series.get("short_term_investments") or [])}
    if cash:
        last = cash[-1]
        s["cash_and_st_investments"] = {"end": last["end"], "value": last["value"] + sti.get(last["end"], 0)}
    ocf = series.get("operating_cash_flow") or []
    capex = {x["end"]: x["value"] for x in (series.get("capex") or [])}
    if ocf:
        fcf = [{"end": x["end"], "value": x["value"] - capex.get(x["end"], 0)} for x in ocf[-4:]]
        s["fcf_last_4q"] = fcf
        burn = -sum(x["value"] for x in fcf) / max(len(fcf), 1)
        if burn > 0 and "cash_and_st_investments" in s:
            s["runway_quarters_at_avg_fcf_burn"] = round(s["cash_and_st_investments"]["value"] / burn, 1)
    debt = series.get("total_debt") or []
    if debt:
        s["total_debt_latest"] = debt[-1]
    # v7.1: TTM flows and year-ago balance pairs for scripts/company_check.py
    flows = {"net_income": series.get("net_income"), "operating_income": op, "operating_cash_flow": ocf,
             "capex": series.get("capex"), "sbc": series.get("sbc"), "rnd": series.get("rnd"),
             "dividends_paid": series.get("dividends_paid"), "buybacks": series.get("buybacks"), "gross_profit": gp}
    for key, rows in flows.items():
        val = ttm(rows or [])
        if val is not None and rows and rev and abs((_d(rows[-1]) - _d(rev[-1])).days) <= 10:
            s[f"{key}_ttm"] = val
    for key, rows in (("revenue", rev), ("net_income", series.get("net_income"))):
        if not rows:
            continue
        ya = [x for x in rows if (_d(rows[-1]) - _d(x)).days >= 350]
        if ya and 350 <= (_d(rows[-1]) - _d(ya[-1])).days <= 380 and ttm(ya) is not None:
            s[f"{key}_ttm_year_ago"] = ttm(ya)
    for key in ("equity", "total_assets", "total_liabilities", "receivables", "inventory", "goodwill", "contract_liabilities", "cash"):
        rows = series.get(key) or []
        if not rows:
            continue
        s[f"{key}_latest"] = {"end": rows[-1]["end"], "value": rows[-1]["value"]}
        prior = [x for x in rows[:-1] if 350 <= (_d(rows[-1]) - _d(x)).days <= 380]
        if prior:
            s[f"{key}_year_ago"] = {"end": prior[-1]["end"], "value": prior[-1]["value"]}
    sh = series.get("shares_outstanding_dei") or []
    if sh:
        s["shares_outstanding"] = sh[-1]["value"]
        s["shares_as_of"] = sh[-1]["end"]
        if sh[-1].get("classes"):
            s["share_classes_summed"] = sh[-1]["classes"]
        if len(sh) >= 5 and sh[-5]["value"]:
            s["share_count_change_pct_vs_4_obs_ago"] = round((sh[-1]["value"] / sh[-5]["value"] - 1) * 100, 2)
    return s


def efts_search(fetcher: Fetcher, query: str, cik: int | None = None, forms: str | None = None,
                start: str | None = None, end: str | None = None, limit: int = 10) -> dict[str, Any]:
    params: dict[str, str] = {"q": query}
    if cik:
        params["ciks"] = f"{cik:010d}"
    if forms:
        params["forms"] = forms
    if start or end:
        params.update({"dateRange": "custom", "startdt": start or "2001-01-01", "enddt": end or utc_now().date().isoformat()})
    url = "https://efts.sec.gov/LATEST/search-index?" + urllib.parse.urlencode(params)
    data = fetcher.json(url, "efts")
    hits = []
    for h in data["hits"]["hits"][:limit]:
        src = h.get("_source", {})
        acc, _, fname = h.get("_id", "").partition(":")
        ciks = src.get("ciks") or []
        c = int(ciks[0]) if ciks else None
        ftype = src.get("file_type") or ""
        primary = (ftype.upper() in REPORT_FORMS | {"8-K", "8-K/A", "S-1", "S-3", "F-1", "F-3", "424B5"}
                   or (not ftype and not re.match(r"(?i)ex[-_]?\d|exhibit", fname or "")))
        hits.append({"entity": (src.get("display_names") or [None])[0], "form": src.get("form"),
                     "file_type": ftype or None, "primary_document": bool(primary),
                     "filed": src.get("file_date"), "period": src.get("period_ending"),
                     "url": f"https://www.sec.gov/Archives/edgar/data/{c}/{acc.replace('-', '')}/{fname}" if c and fname else None})
    return {"query": query, "total": data["hits"]["total"]["value"], "hits": hits,
            "primary_hits": sum(1 for h in hits if h["primary_document"]), "source_url": url}


# ---------------------------------------------------------------- news
def google_news(fetcher: Fetcher, query: str, limit: int = 12, days: int | None = 120) -> dict[str, Any]:
    q = query + (f" when:{days}d" if days else "")
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    root = ET.fromstring(fetcher.get(url, "news").decode("utf-8", "replace"))
    items = []
    for it in root.findall(".//item"):
        pub = it.findtext("pubDate")
        try:
            pub_iso = iso(parsedate_to_datetime(pub)) if pub else None
        except (TypeError, ValueError):
            pub_iso = None
        src = it.find("source")
        items.append({"title": (it.findtext("title") or "").strip(), "url": it.findtext("link"),
                      "published_at": pub_iso, "publisher": src.text if src is not None else None})
    items.sort(key=lambda x: x["published_at"] or "", reverse=True)
    return {"query": query, "items": items[:limit], "source_url": url,
            "note": "Headlines are leads, not facts; open the primary source before citing a material claim."}


# ---------------------------------------------------------------- issuer / currency
def issuer_profile(subs: dict[str, Any]) -> dict[str, Any]:
    """Domestic (10-K/10-Q) vs foreign private issuer (20-F/40-F/6-K)."""
    forms = {f["form"] for f in subs.get("filings", [])}
    fpi = bool(forms & FPI_FORMS) and not (forms & DOMESTIC_REPORT_FORMS)
    annual = "20-F" if "20-F" in forms else "40-F" if "40-F" in forms else "10-K" if "10-K" in forms else None
    return {"foreign_private_issuer": fpi, "annual_form": annual, "fiscal_year_end": subs.get("fiscal_year_end"),
            "sic": subs.get("sic"), "sic_code": subs.get("sic_code"), "state_of_incorporation": subs.get("state_of_incorporation")}


def major_unit(ccy: str | None) -> tuple[str | None, float]:
    if not ccy:
        return ccy, 1.0
    if ccy in MINOR_UNITS:
        return MINOR_UNITS[ccy]
    return ccy.upper(), 1.0


def fx_rate(fetcher: Fetcher, ccy: str, to: str = "USD") -> dict[str, Any]:
    """Spot FX from the Yahoo chart endpoint (<CCY><TO>=X). 1 unit of ccy = rate units of `to`."""
    ccy = ccy.upper()
    if ccy == to:
        return {"pair": f"{ccy}{to}", "rate": 1.0, "as_of": None, "source_url": None}
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ccy + to + '=X')}?range=5d&interval=1d"
    data = fetcher.json(url, "yahoo")
    result = (data.get("chart") or {}).get("result")
    if not result:
        raise KeyError(f"fx_no_result:{ccy}{to}")
    meta = result[0]["meta"]
    rate = meta.get("regularMarketPrice")
    if not rate or rate <= 0:
        raise ValueError(f"fx_bad_rate:{ccy}{to}:{rate}")
    when = meta.get("regularMarketTime")
    return {"pair": f"{ccy}{to}", "rate": float(rate),
            "as_of": iso(datetime.fromtimestamp(when, timezone.utc)) if when else None, "source_url": url}


# ---------------------------------------------------------------- snapshot
def build_evidence(snap: dict[str, Any]) -> list[dict[str, Any]]:
    """Lens-ready evidence entries (schemas/serenity-lens.schema.json#evidence)."""
    ev: list[dict[str, Any]] = []
    retrieved = snap["retrieved_at"]
    q = snap.get("quote", {})
    if q.get("status") == "ok":
        ev.append({"evidence_id": "E-LIVE-QUOTE", "title": f"{q['symbol']} quote {q['price']} {q['currency']} ({q.get('exchange')})",
                   "locator": q["source_url"], "published_at": q["price_as_of"], "retrieved_at": retrieved, "source_type": "market_data"})
    f = snap.get("fundamentals", {})
    if f.get("status") == "ok":
        s = f.get("summary", {})
        sec = f["provider"] == "sec_companyfacts"
        if s.get("shares_as_of"):
            shares_src = s.get("shares_source_url") or f["source_url"]
            ev.append({"evidence_id": "E-LIVE-SHARES", "title": f"Shares outstanding {s['shares_outstanding']:,.0f} as of {s['shares_as_of']} ({s.get('shares_source') or f['provider']})",
                       "locator": shares_src, "published_at": day_iso(s["shares_as_of"]), "retrieved_at": retrieved,
                       "source_type": "filing" if shares_src == f["source_url"] and sec else "market_data"})
        rq = s.get("revenue_latest_quarter") or ((s.get("revenue_quarterly") or [None])[-1])
        if rq:
            end = rq.get("end") or rq.get("as_of")
            fin_src = s.get("financials_source_url") or f["source_url"]
            gm = (s.get("gross_margin_quarterly") or [{}])[-1].get("pct")
            ev.append({"evidence_id": "E-LIVE-FIN", "title": (f"Latest quarterly revenue {rq['value']:,.0f} {s.get('reporting_currency') or ''} (period end {end}); "
                                                               f"TTM {s.get('revenue_ttm')}; YoY {s.get('revenue_yoy_pct')}%; GM {gm}%"),
                       "locator": fin_src, "published_at": day_iso(end), "retrieved_at": retrieved,
                       "source_type": "filing" if fin_src == f["source_url"] and sec else "market_data"})
    for i, (ccy, r) in enumerate(sorted(((snap.get("usd_view") or {}).get("rates") or {}).items()), 1):
        if r.get("source_url") and r.get("as_of"):
            ev.append({"evidence_id": f"E-LIVE-FX-{ccy}", "title": f"FX {r['pair']} {r['rate']}", "locator": r["source_url"],
                       "published_at": r["as_of"], "retrieved_at": retrieved, "source_type": "market_data"})
    radar = snap.get("filings", {})
    if radar.get("status") == "ok":
        picks = (radar.get("reports", [])[:2] + radar.get("dilution", [])[:3] + radar.get("events_8k", [])[:4]
                 + radar.get("ownership", [])[:2])
        seen = set()
        for i, item in enumerate(picks, 1):
            if item["accession"] in seen:
                continue
            seen.add(item["accession"])
            label = ", ".join(item.get("item_labels", []))
            ev.append({"evidence_id": f"E-LIVE-SEC-{i:02d}", "title": f"{item['form']} filed {item['filed']}" + (f" ({label})" if label else ""),
                       "locator": item["url"], "published_at": day_iso(item["filed"]), "retrieved_at": retrieved, "source_type": "filing"})
    xch = snap.get("exchange") or {}
    disc = xch.get("disclosures") or {}
    if disc.get("status") == "ok":
        flagged = {u for fl in disc.get("flags", []) for u in fl.get("urls", [])}
        items = disc.get("items", [])
        picks = [x for x in items if x.get("url") in flagged][:6]
        picks += [x for x in items if x not in picks][: max(0, 8 - len(picks))]
        for i, item in enumerate(sorted(picks, key=lambda r: r["published_at"], reverse=True), 1):
            if item.get("url") and item.get("published_at"):
                ev.append({"evidence_id": f"E-LIVE-XCH-{i:02d}", "title": f"[{disc.get('system')}] {item['title'][:160]}",
                           "locator": item["url"], "published_at": item["published_at"], "retrieved_at": retrieved,
                           "source_type": "filing"})
    q2 = xch.get("second_quote") or {}
    if q2.get("status") == "ok" and q2.get("price_as_of"):
        ev.append({"evidence_id": "E-LIVE-XQ", "title": f"Second-source quote {q2['price']} {q2['currency']} ({q2['provider']}; "
                   f"check: {(xch.get('quote_check') or {}).get('status')})", "locator": q2["source_url"],
                   "published_at": q2["price_as_of"], "retrieved_at": retrieved, "source_type": "market_data"})
    mrev = xch.get("monthly_revenue") or {}
    if mrev.get("status") == "ok":
        ev.append({"evidence_id": "E-LIVE-MREV", "title": f"{mrev['system']} monthly revenue {mrev['month']}: {mrev['revenue']:,.0f} {mrev['currency']} "
                   f"(YoY {mrev.get('yoy_pct')}%, YTD YoY {mrev.get('ytd_yoy_pct')}%)", "locator": mrev["source_url"],
                   "published_at": mrev["published_at"], "retrieved_at": retrieved, "source_type": "filing"})
    lf = snap.get("local_financials") or {}
    if lf.get("status") == "ok":
        ev += _cnhk().evidence(lf, retrieved)
    ah = xch.get("ah_premium") or {}
    if ah.get("status") == "ok":
        ev.append({"evidence_id": "E-LIVE-AH", "title": f"A/H premium {ah['premium_pct']}% ({ah['a_symbol']} {ah['a_price_cny']} CNY vs {ah['h_symbol']} {ah['h_price_hkd']} HKD, HKDCNY {ah['hkdcny']})",
                   "locator": ah["source_urls"][0], "published_at": ah.get("a_as_of") or retrieved, "retrieved_at": retrieved, "source_type": "market_data"})
    news = snap.get("news", {})
    if news.get("status") == "ok":
        for i, item in enumerate(news.get("items", [])[:6], 1):
            if item.get("published_at"):
                ev.append({"evidence_id": f"E-LIVE-NEWS-{i:02d}", "title": f"[lead] {item['title'][:160]}",
                           "locator": item["url"], "published_at": item["published_at"], "retrieved_at": retrieved, "source_type": "news"})
    return ev


def market_current(snap: dict[str, Any]) -> dict[str, Any] | None:
    """price x latest reported shares, in the quote's MAJOR currency unit.

    Withholds market cap (market_cap=None + notes) when the arithmetic is known
    to be wrong: ADRs without a ratio, or share classes that are not 1:1.
    """
    q, f = snap.get("quote", {}), snap.get("fundamentals", {})
    if q.get("status") != "ok" or f.get("status") != "ok":
        return None
    s = f.get("summary", {})
    shares = s.get("shares_outstanding")
    if not shares or not q.get("price"):
        return None
    major, div = major_unit(q.get("currency"))
    price = q["price"] / div
    notes: list[str] = []
    if div != 1:
        notes.append(f"quote is in {q['currency']} minor units; price converted to {major} (/{div:g})")
    subject = snap.get("subject", {})
    symbol = subject.get("symbol", "")
    withheld = None
    eff_shares = float(shares)
    fpi = (snap.get("sec_profile") or {}).get("foreign_private_issuer")
    if fpi:  # cover-page (and provider) counts are ordinary shares, not ADS
        ratio = subject.get("adr_ratio")
        if ratio:
            eff_shares = shares / float(ratio)
            notes.append(f"SEC cover shares are ordinary shares; divided by ADR ratio {ratio:g} (ordinary shares per ADS)")
        else:
            withheld = ("foreign private issuer: SEC cover shares are ordinary shares but the US quote is per ADS. "
                        "Re-run with --adr-ratio <ordinary shares per ADS> (see the deposit agreement / 20-F Item 12).")
    cls = SHARE_CLASS_NOTES.get(symbol.upper())
    if cls:
        notes.append(cls[1])
        if cls[0] == "unreliable":
            withheld = cls[1]
    if s.get("share_classes_summed") and not cls:
        notes.append(f"{s['share_classes_summed']} share classes summed from the SEC cover page; confirm they convert 1:1")
    out = {"price": round(price, 6), "currency": major, "quote_currency": q.get("currency"), "price_as_of": q["price_as_of"],
           "shares_outstanding": round(eff_shares, 2), "shares_as_of": day_iso(s["shares_as_of"]),
           "market_cap": None if withheld else round(price * eff_shares, 2),
           "evidence_ids": ["E-LIVE-QUOTE", "E-LIVE-SHARES"],
           "basis": "price x latest reported shares (calculated, not provider market cap)"}
    if withheld:
        out["market_cap_withheld"] = withheld
    if notes:
        out["notes"] = notes
    return out


def usd_view(snap: dict[str, Any], fetcher: Fetcher) -> dict[str, Any]:
    """Cross-listing comparables: USD market cap, USD TTM revenue, P/S. Needs FX when not USD."""
    mc = snap.get("market_current") or {}
    f = snap.get("fundamentals", {})
    s = f.get("summary", {}) if f.get("status") == "ok" else {}
    qccy = mc.get("currency") or major_unit((snap.get("quote") or {}).get("currency"))[0]
    rccy = major_unit(s.get("reporting_currency"))[0] if s.get("reporting_currency") else None
    rates: dict[str, Any] = {}
    for c in {c for c in (qccy, rccy) if c}:
        r = section(lambda c=c: fx_rate(fetcher, c))
        rates[c] = r
    out: dict[str, Any] = {"rates": {c: r for c, r in rates.items() if r.get("status") == "ok"}}

    def conv(value: float | None, ccy: str | None) -> float | None:
        if value is None or not ccy:
            return None
        r = rates.get(ccy) or {}
        return round(value * r["rate"], 2) if r.get("status") == "ok" else None

    out["market_cap_usd"] = conv(mc.get("market_cap"), qccy)
    rev, basis = s.get("revenue_ttm"), "ttm"
    lq = s.get("revenue_latest_quarter") or ((s.get("revenue_quarterly") or [None])[-1])
    ann = s.get("revenue_annual_latest") or {}
    lq_end = (lq or {}).get("end") or (lq or {}).get("as_of") or ""
    lf = snap.get("local_financials") or {}
    lttm = ((lf.get("ttm") or {}).get("revenue") or {}) if lf.get("status") == "ok" else {}
    if rev is None and lttm.get("value") and lf.get("reporting_currency") and major_unit(lf["reporting_currency"])[0] == rccy:
        rev, basis = lttm["value"], f"ttm_from_ytd_{lf.get('provider')}"  # YTD + prior FY - prior YTD (cnhk_fin.ttm)
    if rev is None and lq and lq.get("value") and (not ann.get("as_of") or
                                                   (datetime.fromisoformat(lq_end[:10]) - datetime.fromisoformat(ann["as_of"][:10])).days > 90):
        rev, basis = lq["value"] * 4, f"latest_quarter_x4_{lq_end}"  # run-rate beats a stale fiscal year
    elif rev is None and ann.get("value"):
        rev, basis = ann["value"], f"annual_{ann.get('as_of')}"
    out["revenue_ttm_usd"] = conv(rev, rccy)
    out["revenue_basis"] = basis if rev is not None else None
    if out["market_cap_usd"] and out["revenue_ttm_usd"] and out["revenue_ttm_usd"] > 0:
        out["ps_ttm"] = round(out["market_cap_usd"] / out["revenue_ttm_usd"], 2)
    failed = [c for c, r in rates.items() if r.get("status") != "ok"]
    if failed:
        out["fx_unavailable"] = failed
    out["note"] = "USD values use spot FX for comparison only; lens arithmetic stays in the quote currency."
    return out


def quality_warnings(snap: dict[str, Any]) -> list[str]:
    w: list[str] = []
    now = parse_dt(snap["retrieved_at"])
    q, f = snap.get("quote", {}), snap.get("fundamentals", {})
    if q.get("status") == "ok" and q.get("price_as_of") and now and (now - parse_dt(q["price_as_of"])).days > 5:
        w.append("quote_older_than_5_days")
    s = f.get("summary", {}) if f.get("status") == "ok" else {}
    if s.get("shares_as_of") and now and (now - parse_dt(day_iso(s["shares_as_of"]))).days > 200:
        w.append("share_count_older_than_200_days")
    rq = s.get("revenue_latest_quarter") or ((s.get("revenue_quarterly") or [None])[-1]) or {}
    rend = rq.get("end") or rq.get("as_of")
    if rend and now and (now - parse_dt(day_iso(rend))).days > 200:
        w.append(f"latest_quarterly_financials_older_than_200_days:{rend}")
    rc = major_unit(s.get("reporting_currency"))[0] if s.get("reporting_currency") else None
    qc = major_unit(q.get("currency"))[0] if q.get("currency") else None
    if rc and qc and rc != qc:
        w.append(f"reporting_currency_{rc}_differs_from_quote_currency_{qc}: use usd_view or convert before ratios")
    if q.get("currency") in MINOR_UNITS:
        w.append(f"quote_in_minor_units_{q['currency']}: market_current converted to {MINOR_UNITS[q['currency']][0]}")
    for g in s.get("gross_margin_quarterly", [])[-2:]:
        if g["pct"] < 0 or g["pct"] > 95:
            w.append(f"gross_margin_outlier_{g.get('end') or g.get('as_of')}:{g['pct']}% — check impairment/one-offs/data error")
    if s.get("gross_margin_period_lag"):
        lag = s["gross_margin_period_lag"]
        w.append(f"gross_margin_period_lag: latest margin is {lag['gross_margin_end']} but revenue is {lag['revenue_end']}")
    if s.get("share_classes_summed"):
        w.append(f"share_classes_summed:{s['share_classes_summed']} — confirm class conversion ratios")
    mc = snap.get("market_current") or {}
    if mc.get("market_cap_withheld"):
        w.append("market_cap_withheld: " + mc["market_cap_withheld"])
    sym = (snap.get("subject") or {}).get("symbol", "").upper()
    if sym in SHARE_CLASS_NOTES:
        w.append(f"share_class_note_{SHARE_CLASS_NOTES[sym][0]}: {SHARE_CLASS_NOTES[sym][1]}")
    if (snap.get("sec_profile") or {}).get("foreign_private_issuer"):
        w.append("foreign_private_issuer: 20-F/6-K filer; quarterly XBRL may be missing and US quote may be an ADR")
    if s.get("financials_source"):
        w.append("financials_from_fallback: " + s["financials_source"])
    basis = (snap.get("usd_view") or {}).get("revenue_basis")
    if basis and basis != "ttm" and not basis.startswith("ttm_from_ytd"):
        w.append(f"revenue_ttm_unavailable: P/S uses {basis}")
    if (snap.get("usd_view") or {}).get("fx_unavailable"):
        w.append("fx_unavailable:" + ",".join(snap["usd_view"]["fx_unavailable"]))
    if snap.get("subject", {}).get("review_needed"):
        w.append("symbol_resolution_review_needed")
    xch = snap.get("exchange") or {}
    qc2 = xch.get("quote_check") or {}
    if qc2.get("status") == "mismatch":
        w.append(f"quote_cross_check_mismatch: {qc2['second_source']} differs by {qc2['price_diff_pct']}% — {qc2['note']}")
    for fl in ((xch.get("disclosures") or {}).get("flags") or []):
        if fl.get("direction") == "negative":
            w.append(f"exchange_flag_{fl['flag']}: {fl.get('count')} title hit(s) — open the document")
    q2 = xch.get("second_quote") or {}
    if q2.get("status") == "ok" and q2.get("shares_total") and s.get("shares_outstanding") and s.get("shares_source") != "tencent_quote_total_shares":
        gap = (float(q2["shares_total"]) / float(s["shares_outstanding"]) - 1) * 100
        if abs(gap) > 3:
            w.append(f"share_count_vs_exchange_{gap:+.1f}pct: exchange-side total shares {q2['shares_total']:,.0f} vs reported "
                     f"{float(s['shares_outstanding']):,.0f} as of {str(s.get('shares_as_of'))[:10]} — newer issuance/conversion or other share lines")
    lf = snap.get("local_financials")
    if lf:
        w += _cnhk().warnings(lf, now)
    if (xch.get("ah_premium") or {}).get("status") == "ok":
        ah = xch["ah_premium"]
        w.append(f"dual_listed_a_h: {ah['a_symbol']} / {ah['h_symbol']} premium {ah['premium_pct']}% — value each line at its own price; "
                 "per-share ratios use total shares")
    if s.get("shares_source") == "tencent_quote_total_shares":
        w.append("shares_from_exchange_quote: total shares from Tencent quote (all share lines); confirm A/H split before valuing one line")
    for key in ("quote", "fundamentals", "filings", "news"):
        sec = snap.get(key, {})
        if sec.get("status") == "unavailable":
            if key == "filings" and str(sec.get("error", "")).startswith("non_US_issuer"):
                disc = (snap.get("exchange") or {}).get("disclosures") or {}
                if disc.get("status") == "ok" and disc.get("items"):
                    w.append(f"sec_filings_not_applicable_non_us: exchange disclosures attached ({disc.get('system')}, "
                             f"{len(disc.get('items', []))} items) — open flagged documents before concluding")
                elif disc.get("status") == "ok":
                    w.append(f"sec_filings_not_applicable_non_us: {disc.get('system')} returned no items in its window "
                             f"({disc.get('window_days', '?')} days) — check the issuer IR page / statutory filings")
                else:
                    w.append("sec_filings_not_applicable_non_us: read exchange filings (DART/MOPS/TDnet/RNS) for financing and contracts"
                             + (f" [{disc.get('error')}]" if disc.get("error") else ""))
            else:
                w.append(f"{key}_unavailable")
    return w


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _merge_fallback(primary: dict[str, Any], yf: dict[str, Any]) -> None:
    """Fill gaps in SEC companyfacts from the Yahoo series (FPIs, stale tags) and say so."""
    if yf.get("status") != "ok":
        return
    s, y = primary.setdefault("summary", {}), yf.get("summary", {})
    if not s.get("shares_outstanding") and y.get("shares_outstanding"):
        s["shares_outstanding"], s["shares_as_of"] = y["shares_outstanding"], y["shares_as_of"]
        s["shares_source"], s["shares_source_url"] = "yahoo_timeseries", yf["source_url"]
    sec_end = (s.get("revenue_latest_quarter") or {}).get("end") or ""
    y_end = ((y.get("revenue_quarterly") or [{}])[-1]).get("as_of") or ""
    if y_end and (not sec_end or (datetime.fromisoformat(y_end[:10]) - datetime.fromisoformat(sec_end[:10])).days > 80):
        for k in ("revenue_quarterly", "reporting_currency", "revenue_ttm", "revenue_yoy_pct", "revenue_qoq_pct",
                  "gross_margin_quarterly", "gross_margin_change_yoy_pp", "gross_margin_period_lag"):
            if k in y:
                s[k] = y[k]
        s.pop("revenue_latest_quarter", None)
        s["financials_source"] = f"yahoo_timeseries (SEC XBRL latest quarter {sec_end or 'missing'})"
        s["financials_source_url"] = yf["source_url"]


def _venues():
    """Import venues.py sharing THIS module object (also when run as __main__)."""
    sys.modules.setdefault("live_data", sys.modules[__name__])
    import venues  # noqa: PLC0415
    return venues


def _cnhk():
    """Import cnhk_fin.py sharing THIS module object (also when run as __main__)."""
    sys.modules.setdefault("live_data", sys.modules[__name__])
    import cnhk_fin  # noqa: PLC0415
    return cnhk_fin


def _listing_links(symbol: str) -> dict[str, str]:
    try:
        from ticker_normalizer import universe  # type: ignore  # noqa: PLC0415
        return universe().links(symbol)
    except Exception:  # pragma: no cover - universe assets missing
        return {}


def ah_premium(fetcher: Fetcher, subject_quote: dict[str, Any], other_quote: dict[str, Any], symbol: str, other: str) -> dict[str, Any]:
    """A/H premium = A price / (H price x HKDCNY) - 1, both quotes from the same second source (Tencent)."""
    a_sym, h_sym = (symbol, other) if not symbol.endswith(".HK") else (other, symbol)
    quotes = {symbol: subject_quote, other: other_quote}
    a, h = quotes[a_sym], quotes[h_sym]
    if a.get("status") != "ok" or h.get("status") != "ok" or not a.get("price") or not h.get("price"):
        raise KeyError("ah_quote_unavailable")
    hkd, cny = fx_rate(fetcher, "HKD"), fx_rate(fetcher, "CNY")
    hkdcny = hkd["rate"] / cny["rate"]
    prem = (a["price"] / (h["price"] * hkdcny) - 1) * 100
    return {"a_symbol": a_sym, "h_symbol": h_sym, "a_price_cny": a["price"], "h_price_hkd": h["price"],
            "hkdcny": round(hkdcny, 6), "premium_pct": round(prem, 2), "a_as_of": a.get("price_as_of"), "h_as_of": h.get("price_as_of"),
            "source_urls": [a.get("source_url"), h.get("source_url"), hkd.get("source_url"), cny.get("source_url")],
            "basis": "Tencent quotes for both lines; FX = HKDUSD / CNYUSD (Yahoo). Positive = A-share line richer."}


def _shares_from_second_quote(snap: dict[str, Any]) -> None:
    """A/H shares: when the provider has no share count, use the exchange-side total shares and say so."""
    q2 = (snap.get("exchange") or {}).get("second_quote") or {}
    if q2.get("status") != "ok" or not q2.get("shares_total"):
        return
    f = snap.get("fundamentals") or {}
    if f.get("status") != "ok":
        f = snap["fundamentals"] = {"status": "ok", "provider": "tencent_quote", "source_url": q2["source_url"], "summary": {},
                                    "note": "primary fundamentals unavailable; share count only"}
    s = f.setdefault("summary", {})
    if not s.get("shares_outstanding"):
        s["shares_outstanding"], s["shares_as_of"] = q2["shares_total"], q2["price_as_of"][:10]
        s["shares_source"], s["shares_source_url"] = "tencent_quote_total_shares", q2["source_url"]


def snapshot(ticker: str, fetcher: Fetcher, yahoo: str | None = None, news_query: str | None = None,
             fts: bool = True, news: bool = True, now: datetime | None = None,
             adr_ratio: float | None = None, fx: bool = True, exchange: bool = True) -> dict[str, Any]:
    """All sources for one ticker, fetched concurrently (SEC pacing is shared via the Fetcher lock)."""
    now = now or utc_now()
    t0 = time.time()
    subject = resolve_symbol(ticker, yahoo)
    if adr_ratio:
        subject["adr_ratio"] = float(adr_ratio)
    symbol = subject["symbol"]
    if "cross_listings" not in subject:
        links = _listing_links(symbol)
        if links:
            subject["cross_listings"] = links
    snap: dict[str, Any] = {"schema_version": "6.0", "kind": "live_snapshot", "connector_version": CONNECTOR_VERSION,
                            "retrieved_at": iso(now), "subject": subject}
    log_start = len(fetcher.log)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        f_quote = pool.submit(section, lambda: yahoo_quote(fetcher, symbol))
        cik_info: dict[str, Any] = {}
        if subject.get("us_listed"):
            cik_info = section(lambda: sec_cik(fetcher, symbol))
            snap["sec_identity"] = cik_info
        cik = cik_info.get("cik") if cik_info.get("status") == "ok" else None
        if cik and subject.get("review_needed"):
            subject["review_needed"] = False
            subject["reason"] = f"confirmed by SEC ticker map (CIK {cik}, {cik_info.get('exchange')})"
        futs: dict[str, Any] = {}
        if cik:
            futs["subs"] = pool.submit(section, lambda: sec_submissions(fetcher, cik))
            futs["facts"] = pool.submit(section, lambda: sec_facts(fetcher, cik))
            if fts:
                start = (now - timedelta(days=760)).date().isoformat()
                futs["fts"] = {k: pool.submit(section, lambda q=q: efts_search(fetcher, q, cik=cik, start=start, limit=6))
                               for k, q in DOCTRINE_FTS.items()}
        else:
            futs["yf"] = pool.submit(section, lambda: yahoo_fundamentals(fetcher, symbol, now))
        snap["quote"] = f_quote.result()
        cnhk = False
        if exchange and not subject.get("us_listed"):
            V = _venues()
            venue = V.venue_of(symbol)["venue"]
            cnhk = venue in ("CN", "HK")
            if venue != "US":
                futs["xch"] = pool.submit(section, lambda: V.exchange_block(fetcher, symbol, quote=snap["quote"], now=now))
            pair = (subject.get("cross_listings") or {}).get("h_share" if venue == "CN" else "a_share")
            if cnhk and pair:
                futs["pair_quote"] = (pair, pool.submit(section, lambda: V.tencent_quote(fetcher, pair)))
        if news:
            nq = news_query or (snap["quote"].get("name") if snap["quote"].get("status") == "ok" else None) \
                or cik_info.get("name") or ticker
            nq = re.sub(r"\b(Inc|Corp|Corporation|Ltd|Limited|plc|AB|SA|S\.A\.|N\.V\.|Holdings?|Co)\b\.?,?", "", nq).replace("(publ)", "").strip(" ,.")
            futs["news"] = pool.submit(section, lambda: google_news(fetcher, nq))
        if cik:
            subs = futs["subs"].result()
            if subs.get("status") == "ok":
                snap["filings"] = section(lambda: {**filing_radar(subs, now), "source_url": subs["source_url"],
                                                   "issuer": subs.get("name"), "sic": subs.get("sic")})
                snap["sec_profile"] = issuer_profile(subs)
            else:
                snap["filings"] = subs
            facts = futs["facts"].result()
            fsum = facts.get("summary", {}) if facts.get("status") == "ok" else {}
            rend = (fsum.get("revenue_latest_quarter") or {}).get("end")
            stale = not rend or (now.replace(tzinfo=None) - datetime.fromisoformat(rend)).days > 150
            if facts.get("status") != "ok" or not fsum.get("shares_outstanding") or stale:
                yf = section(lambda: yahoo_fundamentals(fetcher, symbol, now))
                snap["fundamentals_fallback"] = {k: v for k, v in yf.items() if k != "series"}
                if facts.get("status") != "ok":
                    facts = yf
                else:
                    _merge_fallback(facts, yf)
            snap["fundamentals"] = facts
            if fts:
                snap["fts"] = {k: fut.result() for k, fut in futs["fts"].items()}
        else:
            snap["fundamentals"] = futs["yf"].result()
            if cnhk:
                ysum = snap["fundamentals"].get("summary") if snap["fundamentals"].get("status") == "ok" else None
                futs["fin"] = pool.submit(section, lambda: _cnhk().financials(fetcher, symbol, ysum, now))
            snap["filings"] = ({"status": "unavailable", "error": f"sec_identity_failed:{cik_info.get('error')}"} if subject.get("us_listed")
                               else {"status": "unavailable", "error": "non_US_issuer: use exchange filings (see references/market-source-playbook.md)"})
        if news:
            snap["news"] = futs["news"].result()
        if "xch" in futs:
            snap["exchange"] = futs["xch"].result()
            _shares_from_second_quote(snap)
        if "fin" in futs:
            snap["local_financials"] = futs["fin"].result()
        if "pair_quote" in futs and "xch" in futs:
            other, fut = futs["pair_quote"]
            q2 = (snap.get("exchange") or {}).get("second_quote") or {}
            snap["exchange"]["ah_premium"] = section(lambda: ah_premium(fetcher, q2, fut.result(), symbol, other))
    snap["market_current"] = market_current(snap)
    if fx:
        snap["usd_view"] = usd_view(snap, fetcher)
    snap["evidence"] = build_evidence(snap)
    snap["warnings"] = quality_warnings(snap)
    snap["fetch_log"] = fetcher.log[log_start:][-80:]
    snap["elapsed_seconds"] = round(time.time() - t0, 2)
    snap["disclaimer"] = "Live data leads for research only; not investment advice. Verify material claims in primary sources."
    return snap


# ---------------------------------------------------------------- primary documents
class _HTMLText(HTMLParser):
    SKIP = {"script", "style", "head", "title", "ix:header", "xbrl"}
    BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "section", "hr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")
        elif tag in ("td", "th"):
            self.parts.append(" ")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)


def html_to_text(raw: bytes) -> str:
    text = raw.decode("utf-8", "replace")
    if "<" in text[:5000]:
        parser = _HTMLText()
        parser.feed(text)
        parser.close()
        text = "".join(parser.parts)
    text = text.replace("\xa0", " ").replace("\u200b", "")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n\s*(\n\s*)+", "\n\n", text)
    return text.strip()


def grep_text(text: str, terms: dict[str, str], window: int = 280, max_per_term: int = 3) -> dict[str, Any]:
    hits: dict[str, Any] = {}
    for name, pat in terms.items():
        matches = list(re.finditer(pat, text, re.I))
        excerpts: list[dict[str, Any]] = []
        last_end = -1
        for m in matches:
            if m.start() < last_end:
                continue
            a, b = max(0, m.start() - window), min(len(text), m.end() + window)
            snippet = re.sub(r"\s+", " ", text[a:b]).strip()
            excerpts.append({"offset": m.start(), "match": m.group(0),
                             "excerpt": ("…" if a else "") + snippet + ("…" if b < len(text) else "")})
            last_end = b
            if len(excerpts) >= max_per_term:
                break
        hits[name] = {"count": len(matches), "excerpts": excerpts}
    return hits


def filing_text(fetcher: Fetcher, url: str, terms: dict[str, str] | None = None, window: int = 280,
                max_per_term: int = 3, full_text: bool = False) -> dict[str, Any]:
    """Fetch one SEC Archives document, strip HTML/inline-XBRL, and pull keyword excerpts."""
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname != "www.sec.gov" or not parsed.path.startswith("/Archives/"):
        raise SourceError("filing_text_requires_www.sec.gov/Archives_url")
    raw = fetcher.get(url, "sec_doc")
    text = html_to_text(raw)
    out: dict[str, Any] = {"url": url, "chars": len(text), "sha256_16": hashlib.sha256(raw).hexdigest()[:16],
                           "terms": grep_text(text, terms or FILING_TERM_PRESETS["all"], window, max_per_term),
                           "source_url": url,
                           "note": "Excerpts are verbatim SEC text (public record); quote sparingly and cite the URL."}
    if full_text:
        out["text"] = text
    return out


def latest_filing(subs: dict[str, Any], form: str) -> dict[str, Any] | None:
    for f in subs.get("filings", []):
        if f["form"] == form:
            return f
    return None


def terms_from_args(preset: str | None, grep: list[str] | None) -> dict[str, str]:
    terms: dict[str, str] = {}
    if preset:
        if preset not in FILING_TERM_PRESETS:
            raise SystemExit(f"unknown preset {preset}; choose from {', '.join(FILING_TERM_PRESETS)}")
        terms.update(FILING_TERM_PRESETS[preset])
    for i, g in enumerate(grep or [], 1):
        terms[f"grep_{i}"] = g
    return terms or FILING_TERM_PRESETS["all"]


# ---------------------------------------------------------------- batch / pack
def batch(tickers: list[str], fetcher: Fetcher, fts: bool = False, news: bool = False,
          now: datetime | None = None) -> dict[str, dict[str, Any]]:
    """Several snapshots concurrently. FTS/news default off for peers (speed)."""
    now = now or utc_now()
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, max(1, len(tickers)))) as pool:
        futs = {t: pool.submit(snapshot, t, fetcher, fts=fts, news=news, now=now) for t in tickers}
        return {t: f.result() for t, f in futs.items()}


def _fmt_big(v: Any) -> str:
    if not isinstance(v, (int, float)):
        return "—"
    a = abs(v)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if a >= div:
            return f"{v / div:.2f}{suf}"
    return f"{v:,.0f}"


def _pct(v: Any, signed: bool = True) -> str:
    return (f"{v:+.1f}%" if signed else f"{v:.1f}%") if isinstance(v, (int, float)) else "—"


def compare_row(snap: dict[str, Any], scan: dict[str, Any] | None = None) -> dict[str, Any]:
    q = snap.get("quote", {}) if snap.get("quote", {}).get("status") == "ok" else {}
    f = snap.get("fundamentals", {})
    s = f.get("summary", {}) if f.get("status") == "ok" else {}
    u = snap.get("usd_view") or {}
    mc = snap.get("market_current") or {}
    gm = (s.get("gross_margin_quarterly") or [{}])[-1]
    return {
        "symbol": snap.get("subject", {}).get("symbol"), "name": q.get("name"),
        "price": q.get("price"), "currency": q.get("currency"), "price_as_of": q.get("price_as_of"),
        "market_cap": mc.get("market_cap"), "market_cap_usd": u.get("market_cap_usd"),
        "drawdown_pct": q.get("drawdown_from_52w_high_pct"), "return_1y_pct": (q.get("return_pct") or {}).get("1y"),
        "revenue_ttm_usd": u.get("revenue_ttm_usd"), "revenue_yoy_pct": s.get("revenue_yoy_pct"),
        "revenue_qoq_pct": s.get("revenue_qoq_pct"), "gross_margin_pct": gm.get("pct"),
        "gross_margin_end": gm.get("end") or gm.get("as_of"), "gross_margin_yoy_pp": s.get("gross_margin_change_yoy_pp"),
        "ps_ttm": u.get("ps_ttm"), "revenue_basis": u.get("revenue_basis"), "share_change_pct": s.get("share_count_change_pct_vs_4_obs_ago"),
        "fit_guess": (scan or {}).get("framework_fit_guess"), "flags": [x["signal"] for x in (scan or {}).get("signals", [])],
        "warnings": snap.get("warnings", []),
    }


def _scan_tools():
    import atlas as atlas_mod  # type: ignore  # scripts/ is on sys.path
    import chokepoint_scan  # type: ignore
    return atlas_mod, chokepoint_scan


def _company_check(snap: dict[str, Any]) -> dict[str, Any] | None:
    """Universal company health check (scripts/company_check.py); never fails the pack."""
    try:
        import company_check  # type: ignore  # scripts/ is on sys.path
        return company_check.check(snap)
    except Exception:  # noqa: BLE001 - a broken check must not block the research pack
        return None


def _memory(ledger_path: Path | None, symbol: str) -> dict[str, Any]:
    if not ledger_path:
        return {"status": "unavailable", "note": "No Serenity stance ledger supplied (--ledger). Silence in this pack is not a view."}
    try:
        from stance_ledger import lens_memory  # type: ignore
        ledger = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    except (OSError, ValueError, ImportError) as exc:
        return {"status": "unavailable", "note": f"ledger_unreadable:{exc}"}
    for key in (symbol, symbol.split(".")[0]):
        if key.upper() in ledger.get("tickers", {}):
            return lens_memory(ledger, key)
    return lens_memory(ledger, symbol)


def pick_primary_docs(snap: dict[str, Any], forms: tuple[str, ...] = ("10-K", "10-Q", "20-F", "40-F")) -> list[dict[str, Any]]:
    reports = (snap.get("filings") or {}).get("reports") or []
    picks: list[dict[str, Any]] = []
    for form in forms:
        hit = next((r for r in reports if r["form"] == form), None)
        if hit:
            picks.append(hit)
    return picks[:2]


def pack(subject: str, fetcher: Fetcher, out_dir: Path, peers: list[str] | None = None, news_query: str | None = None,
         adr_ratio: float | None = None, ledger_path: Path | None = None, docs: bool = True,
         yahoo: str | None = None, now: datetime | None = None) -> dict[str, Any]:
    """Fast path: subject + peers in parallel, FX, latest 10-K/10-Q excerpts, offline scan + atlas,
    optional Serenity memory -> brief.md + lens-draft.json (judgment fields left as TODO)."""
    t0 = time.time()
    now = now or utc_now()
    atlas_mod, scan_mod = _scan_tools()
    atlas = atlas_mod.load_atlas()
    sym = resolve_symbol(subject, yahoo)["symbol"]
    position = atlas_mod.lookup_ticker(atlas, sym)
    if peers is None:  # default: atlas peers on the same node
        peers = list(dict.fromkeys(p for pos in position["positions"] for p in pos["peers"]))[:4]
    peers = [p for p in peers if p and p.upper() != sym.upper()]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "snapshots").mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(peers) + 3)) as pool:
        f_sub = pool.submit(snapshot, subject, fetcher, yahoo, news_query, True, True, now, adr_ratio)
        f_peers = {p: pool.submit(snapshot, p, fetcher, None, None, False, False, now) for p in peers}
        snap = f_sub.result()
        f_docs = []
        if docs:
            for r in pick_primary_docs(snap):
                f_docs.append(pool.submit(section, lambda r=r: {**filing_text(fetcher, r["url"], FILING_TERM_PRESETS["all"], 260, 2),
                                                                "form": r["form"], "filed": r["filed"], "report_date": r.get("report_date")}))
        peer_snaps = {p: f.result() for p, f in f_peers.items()}
        doc_hits = [f.result() for f in f_docs]
    snap_paths = {}
    for s in [snap, *peer_snaps.values()]:
        name = re.sub(r"[^A-Za-z0-9._-]", "_", s["subject"]["symbol"]) + ".json"
        path = out_dir / "snapshots" / name
        path.write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        snap_paths[s["subject"]["symbol"]] = str(path)
    scans = {s["subject"]["symbol"]: scan_mod.scan_snapshot(s, atlas) for s in [snap, *peer_snaps.values()]}
    memory = _memory(ledger_path, sym)
    health = _company_check(snap)
    if health:
        (out_dir / "company-check.json").write_text(json.dumps(health, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for i, d in enumerate(doc_hits, 1):
        d["evidence_id"] = f"E-LIVE-DOC-{i:02d}"
    rows = [compare_row(s, scans.get(s["subject"]["symbol"])) for s in [snap, *peer_snaps.values()]]
    result = {"schema_version": "6.1", "kind": "research_pack", "connector_version": CONNECTOR_VERSION,
              "retrieved_at": snap["retrieved_at"], "subject": sym, "peers": peers, "snapshots": snap_paths,
              "compare": rows, "scan": scans, "atlas": position, "serenity_memory": memory, "filing_excerpts": doc_hits,
              "company_check": ({"path": str(out_dir / "company-check.json"), "type": health["company_type"]["type"],
                                 "counts": health["counts"]} if health else {"status": "unavailable"})}
    (out_dir / "pack.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    draft = draft_lens(snap, scans[snap["subject"]["symbol"]], position, memory, doc_hits, snap_paths[snap["subject"]["symbol"]], now, health)
    (out_dir / "lens-draft.json").write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["elapsed_seconds"] = round(time.time() - t0, 2)
    (out_dir / "brief.md").write_text(brief_markdown(result, snap, health), encoding="utf-8")
    return result


FRAMEWORK_NOTICE = ("框架声明：本 skill 根据 Serenity 公开发布的内容提炼研究框架，用于回测与研究分析；"
                    "报告由框架生成，不代表 Serenity 本人观点，亦非投资建议。")


def brief_markdown(pack_result: dict[str, Any], snap: dict[str, Any], health: dict[str, Any] | None = None) -> str:
    rows = pack_result["compare"]
    sym = pack_result["subject"]
    q = snap.get("quote", {})
    s = (snap.get("fundamentals") or {}).get("summary", {})
    L = [f"# 研究包：{sym}（{q.get('name') or ''}）", "",
         f"> 数据抓取 {pack_result['retrieved_at']} · 连接器 v{CONNECTOR_VERSION} · 用时 {pack_result.get('elapsed_seconds')} 秒。"
         "以下是数据底稿与机械线索，不是结论；判断写进 lens-draft.json 后用 `serenity_lens.py finish` 收尾。", "",
         "## 1. 对比表（USD 用即期汇率，仅作横向比较）", "",
         "| 代码 | 价格 | 市值(USD) | 52周回撤 | 1年涨跌 | TTM收入(USD) | 收入同比 | 收入环比 | 毛利率(期末) | 毛利率同比 | P/S | 股本变化 | 机械旗标 |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        gm = f"{r['gross_margin_pct']:.1f}% ({r['gross_margin_end']})" if isinstance(r["gross_margin_pct"], (int, float)) else "—"
        ps = f"{r['ps_ttm']:.1f}x" if isinstance(r["ps_ttm"], (int, float)) else "—"
        if r.get("revenue_basis") and r["revenue_basis"] != "ttm" and ps != "—":
            ps += f"（{r['revenue_basis']}）"
        gpp = f"{r['gross_margin_yoy_pp']:+.1f}pp" if isinstance(r["gross_margin_yoy_pp"], (int, float)) else "—"
        flags = ", ".join(r["flags"][:5]) or "—"
        price = f"{r['price']} {r['currency']}" if r["price"] is not None else "—"
        L.append(f"| `{r['symbol']}` | {price} | {_fmt_big(r['market_cap_usd'])} | {_pct(r['drawdown_pct'])} | {_pct(r['return_1y_pct'])} | "
                 f"{_fmt_big(r['revenue_ttm_usd'])} | {_pct(r['revenue_yoy_pct'])} | {_pct(r['revenue_qoq_pct'])} | {gm} | {gpp} | {ps} | "
                 f"{_pct(r['share_change_pct'])} | {flags} |")
    L += ["", "## 2. 主体要点", ""]
    rq = s.get("revenue_latest_quarter") or ((s.get("revenue_quarterly") or [None])[-1]) or {}
    om = (s.get("operating_margin_quarterly") or [{}])[-1]
    cash = s.get("cash_and_st_investments") or {}
    L.append(f"- 最新季度收入：{_fmt_big(rq.get('value'))} {s.get('reporting_currency') or ''}（期末 {rq.get('end') or rq.get('as_of')}）；"
             f"营业利润率 {_pct(om.get('pct'), False)}；现金+短投 {_fmt_big(cash.get('value'))}；"
             f"FCF 跑道 {s.get('runway_quarters_at_avg_fcf_burn', '—')} 季。")
    mc = snap.get("market_current") or {}
    if mc.get("market_cap") is not None:
        L.append(f"- 计算市值：{_fmt_big(mc['market_cap'])} {mc['currency']}（{mc['price']} × {mc['shares_outstanding']:,.0f} 股，股本截至 {mc['shares_as_of'][:10]}）。")
    elif mc.get("market_cap_withheld"):
        L.append(f"- ⚠️ 市值未计算：{mc['market_cap_withheld']}")
    for n in mc.get("notes", []):
        L.append(f"- 注：{n}")
    for flag in (snap.get("filings") or {}).get("flags", []):
        L.append(f"- 文件雷达 `{flag['flag']}`（{flag.get('doctrine')}）：{flag.get('check')}")
    fts = snap.get("fts") or {}
    fts_bits = [f"{k} {v.get('total')}（主文档 {v.get('primary_hits')}/{len(v.get('hits', []))}）" for k, v in fts.items() if v.get("status") == "ok" and v.get("total")]
    if fts_bits:
        L.append("- SEC 全文检索命中（近 25 个月）：" + "；".join(fts_bits))
    xch = snap.get("exchange") or {}
    if xch:
        L += ["", "## 2b. 交易所原生数据", ""]
        qc = xch.get("quote_check") or {}
        if qc.get("status") in ("agree", "mismatch"):
            L.append(f"- 第二行情源（{qc.get('second_source')}）核对：**{qc['status']}**，价差 {qc.get('price_diff_pct')}%，时间差 {qc.get('timestamp_gap_hours')} 小时。")
        mrev = xch.get("monthly_revenue") or {}
        if mrev.get("status") == "ok":
            L.append(f"- {mrev['system']} 月营收 {mrev['month']}：{_fmt_big(mrev['revenue'])} {mrev['currency']}，同比 {_pct(mrev.get('yoy_pct'))}，"
                     f"环比 {_pct(mrev.get('mom_pct'))}，累计同比 {_pct(mrev.get('ytd_yoy_pct'))}（`E-LIVE-MREV`）。")
        disc = xch.get("disclosures") or {}
        if disc.get("status") == "ok":
            L.append(f"- {disc.get('system')} 公告 {len(disc.get('items', []))} 条（窗口内）。标题旗标（只是“去打开原文”的提示）：")
            for fl in disc.get("flags", []):
                lt = fl.get("latest") or {}
                L.append(f"  - `{fl['flag']}` ×{fl['count']}（{fl['doctrine']}，{fl['direction']}）最新 {str(lt.get('published_at'))[:10]}：{lt.get('title', '')[:90]} — {lt.get('url')}")
            for it in disc.get("items", [])[:8]:
                L.append(f"  - {it['published_at'][:10]} {it['title'][:100]} — {it.get('url')}")
        elif disc:
            L.append(f"- 交易所公告：{disc.get('error')}")
        if (xch.get("edinet") or {}).get("status") == "needs_key":
            L.append("- EDINET 法定文件需设置 `EDINET_API_KEY`（免费注册）；当前仅含 TDnet 约 31 天的适时披露。")
    L += _brief_company_section(snap, health)
    L += ["", "## 3. 一手文件关键词摘录", ""]
    if not pack_result["filing_excerpts"]:
        L.append("- 无 SEC 文件（非 SEC 申报主体或未抓取）。非美股以 2b 的交易所公告为准，必要时打开原文（references/market-source-playbook.md）。")
    for d in pack_result["filing_excerpts"]:
        if d.get("status") != "ok":
            L.append(f"- {d.get('error')}")
            continue
        L.append(f"### {d['form']}（提交 {d['filed']}，期末 {d.get('report_date')}）`{d['evidence_id']}`")
        L.append(f"来源：{d['url']}")
        L.append("")
        for term, h in d["terms"].items():
            if not h["count"]:
                continue
            L.append(f"- **{term}** ×{h['count']}：{h['excerpts'][0]['excerpt'][:420]}")
        L.append("")
    L += ["## 4. 图谱位置与下一跳候选", ""]
    pos = pack_result["atlas"]
    if not pos.get("found"):
        L.append(f"- 未收录于卡点图谱：{pos.get('note')}")
    for p in pos.get("positions", []):
        L.append(f"- 链 `{p['chain_id']}` / 节点 `{p['node_id']}`（{p['node']}，状态 {p['status']}，类型 {p['kind']}）；同层：{', '.join(p['peers']) or '—'}")
        for c in p["next_hop_candidates"][:5]:
            L.append(f"  - 下一跳 `{c['ticker']}` {c['name']} — {c['node']}（{c['status']}，依据 {c['basis']}）")
    L += ["", "## 5. Serenity 公开言论记忆（时点）", ""]
    mem = pack_result["serenity_memory"]
    L.append(f"- 状态：{mem.get('status')}；{mem.get('note', '')}")
    for item in (mem.get("timeline") or [])[-6:]:
        L.append(f"  - {item.get('date')} `{item.get('post_id')}` {item.get('action')}/{item.get('stance', '')}")
    L += ["", "## 6. 数据质量警告（写进 lens 的 live_data.warnings_addressed）", ""]
    for r in rows:
        for w in r["warnings"]:
            L.append(f"- `{r['symbol']}`：{w}")
    L += ["", "## 7. 下一步（快速路径）", "",
          "1. 只在 brief 不够时再读一手文件：`python connectors/live_data.py filing-text --ticker X --latest 10-Q --preset contracts`（≤2 份）。",
          "2. 填写 `lens-draft.json` 中所有 `TODO:` 字段（判断、情景、证伪条件、红队）。",
          "3. `python scripts/serenity_lens.py finish lens-draft.json --md report.md --html report.html` 一步完成计算、校验、渲染与核验。",
          "", "---", "", FRAMEWORK_NOTICE, ""]
    return "\n".join(L)


def _brief_company_section(snap: dict[str, Any], health: dict[str, Any] | None) -> list[str]:
    L: list[str] = []
    lf = snap.get("local_financials") or {}
    ah = (snap.get("exchange") or {}).get("ah_premium") or {}
    if not health and lf.get("status") != "ok" and ah.get("status") != "ok":
        return L
    L += ["", "## 2c. 本地财务与公司体检", ""]
    if lf.get("status") == "ok":
        p0 = (lf.get("periods") or [{}])[0]
        rev = (lf.get("ttm") or {}).get("revenue") or {}
        L.append(f"- 本地财务：{lf.get('name') or ''} {lf.get('secucode')}，{lf.get('provider')}（聚合源），最新报告期 {p0.get('period_end')}"
                 f"（{p0.get('label') or ''}），币种 {lf.get('reporting_currency')}（{lf.get('currency_basis')}）；TTM 收入 {_fmt_big(rev.get('value'))}"
                 f"（{rev.get('basis') or '—'}）。原文核对：{lf.get('primary_check')}。")
        yc = lf.get("yahoo_cross_check") or {}
        if yc.get("status"):
            L.append(f"- 与 Yahoo 季度收入交叉核对：**{yc['status']}**（差 {yc.get('diff_pct')}%，期末 {yc.get('period_end')}）。")
    elif lf.get("error"):
        L.append(f"- 本地财务不可用：{lf['error']}")
    if ah.get("status") == "ok":
        L.append(f"- A/H 溢价：{ah['a_symbol']} {ah['a_price_cny']} CNY vs {ah['h_symbol']} {ah['h_price_hkd']} HKD（HKD/CNY {ah['hkdcny']}）→ "
                 f"**{ah['premium_pct']:+.1f}%**（正数=A 股更贵，`E-LIVE-AH`）。")
    xl = (snap.get("subject") or {}).get("cross_listings") or {}
    if xl:
        L.append("- 其他上市线：" + "，".join(f"{k} `{v}`" for k, v in xl.items() if v) + "。")
    if health:
        import company_check  # type: ignore
        L += ["", company_check.to_markdown(health, heading="###").rstrip()]
    return L


def draft_lens(snap: dict[str, Any], scan: dict[str, Any], position: dict[str, Any], memory: dict[str, Any],
               docs: list[dict[str, Any]], snapshot_path: str, now: datetime,
               health: dict[str, Any] | None = None) -> dict[str, Any]:
    """Pre-filled SerenityLens v6 with every judgment field marked TODO (finish refuses TODO)."""
    T = "TODO: "
    q = snap.get("quote", {})
    sym = snap["subject"]["symbol"]
    mc = snap.get("market_current") or {}
    s = (snap.get("fundamentals") or {}).get("summary", {})
    evidence = list(snap.get("evidence", []))
    for d in docs:
        if d.get("status") == "ok":
            evidence.append({"evidence_id": d["evidence_id"], "title": f"{d['form']} filed {d['filed']} (primary document)",
                             "locator": d["url"], "published_at": day_iso(d["filed"]), "retrieved_at": snap["retrieved_at"],
                             "source_type": "filing"})
    pos = (position.get("positions") or [None])[0]
    fit = scan.get("framework_fit_guess", {})
    role = fit.get("role") if fit.get("role") in {"chokepoint", "price_setter_anchor", "downstream_platform",
                                                    "integrator_or_commodity", "diluter_or_story", "non_ai_compounder"} else "integrator_or_commodity"
    fitv = fit.get("fit") if fit.get("fit") in {"strong", "partial", "weak", "not_applicable"} else "partial"
    layers = [{"layer": "upstream_material", "taxonomy_code": pos["taxonomy"] if pos else "",
               "nodes": [{"name": q.get("name") or sym, "ticker": sym, "role": T + "该公司在链条中的位置", "is_subject": True,
                          "listing_status": "listed"}]}]
    if pos:
        if pos["peers"]:
            layers[0]["nodes"] += [{"name": p, "ticker": p, "role": "同层（图谱）", "listing_status": "listed"} for p in pos["peers"][:4]]
        ups = [u for u in pos["upstream_path"] if u["depth"] == 1][:3]
        if ups:
            layers.append({"layer": "cross_theme_root", "nodes": [{"name": u["name"], "ticker": (u["holders"] or [""])[0],
                                                                    "role": f"上游节点（图谱状态 {u['status']}）", "listing_status": "listed"} for u in ups]})
    picks = []
    for c in scan.get("next_hop_candidates", [])[:3]:
        basis = c.get("basis") if c.get("basis") in {"serenity_lead", "author_lead", "industry_knowledge", "live_data", "inference"} else "inference"
        picks.append({"ticker": c["ticker"], "name": c["name"], "relation": "upstream", "node": c["node"],
                      "why": T + "为什么它是更好的下一跳", "basis": basis,
                      "verify_first": f"python connectors/live_data.py snapshot {c['ticker']}"})
    cur = {"price": mc.get("price") or 0, "shares_outstanding": mc.get("shares_outstanding") or 0,
           "market_cap": mc.get("market_cap") or 0, "currency": mc.get("currency") or major_unit(q.get("currency"))[0] or "USD",
           "price_as_of": mc.get("price_as_of") or snap["retrieved_at"], "shares_as_of": mc.get("shares_as_of") or snap["retrieved_at"],
           "evidence_ids": [e for e in ("E-LIVE-QUOTE", "E-LIVE-SHARES") if any(x["evidence_id"] == e for x in evidence)]}
    cash = (s.get("cash_and_st_investments") or {}).get("value")
    debt = (s.get("total_debt_latest") or {}).get("value")
    if cash is not None:
        cur["net_debt"] = float((debt or 0) - cash)
    if mc.get("market_cap") is None:
        cur["market_cap"] = T + (mc.get("market_cap_withheld") or "market cap unavailable")
    scen = [{"name": n, "label": "hypothesis", "horizon_years": 2,
             "assumptions": {"revenue": T + "收入假设", "multiple": T + "倍数", "multiple_basis": "ps", "dilution_pct": 0.0},
             "implied_market_cap": 0, "implied_per_share": 0, "vs_current_pct": 0,
             "assumption_sources": ["E-LIVE-FIN"] if any(x["evidence_id"] == "E-LIVE-FIN" for x in evidence) else [],
             "narrative": T + "情景叙述（≥20 字）"} for n in ("bear", "base", "bull")]
    red_flags = []
    for c in (health or {}).get("checks", []):
        if c["status"] in ("flag", "watch"):
            unit = c.get("unit") or ""
            red_flags.append({"flag": f"company_check_{c['id']}", "severity": "watch", "triggered": "yes",
                              "detail": T + f"体检 {c['id']} {c['label']} = {c['value']}{unit}（{c['status']}；{c['formula']}）：核实原因并判断是否影响结论",
                              "evidence_ids": list(health.get("evidence_ids") or [])})
    for sig in scan.get("signals", []):
        if sig["direction"] in {"negative", "check"}:
            red_flags.append({"flag": sig["signal"], "severity": "watch", "triggered": "unknown",
                              "detail": T + f"核实：{sig['detail']}（{sig['rule']}）", "evidence_ids": []})
    if not red_flags:
        red_flags.append({"flag": "dilution_and_financing", "severity": "watch", "triggered": "unknown",
                          "detail": T + "核实股本、货架注册与融资", "evidence_ids": []})
    warnings_addressed = [{"warning": w, "handling": T + "说明如何处理"} for w in snap.get("warnings", [])]
    mem = dict(memory)
    mem.setdefault("note", "")
    return {
        "schema_version": "6.0", "lens_id": f"lens:{sym.lower()}-{now.date().isoformat()}", "mode": "single_ticker",
        "subject": {"ticker": snap["subject"].get("input") or sym, "resolved_symbol": sym, "exchange": q.get("exchange"),
                    "company_name": q.get("name") or (snap.get("sec_identity") or {}).get("name") or sym,
                    "currency": cur["currency"], "company_type": "other",
                    "taxonomy_codes": [p["taxonomy"] for p in position.get("positions", [])][:3]},
        "research_cutoff": snap["retrieved_at"], "as_of": snap["retrieved_at"],
        "one_liner": T + "一句话结论（≤200 字）", "thirty_second_summary": T + "30 秒摘要（≤700 字，带数字）",
        "capex_certainty": {"demand_source": "unknown", "statement": T + "需求来自谁、多确定", "evidence_ids": []},
        "chain_map": {"theme": pos["chain"] if pos else T + "产业链主题", "layers": layers},
        "chokepoint_of_chokepoint": {"statement": T + "瓶颈的瓶颈", "node": T + "节点", "status": "unknown", "evidence_ids": []},
        "archetype_hits": [{"archetype": a, "applies": "unknown", "why": T + "是否成立"} for a in (pos or {}).get("archetypes", [])[:3]],
        "gates": {g: {"status": "unknown", "why": T + "理由", "evidence_ids": []} for g in ("real_bottleneck", "pre_institutional", "cheap_derisked")},
        "red_flags": red_flags,
        "valuation": {"current": cur, "ruler": "chokepoint_comparable", "scenarios": scen},
        "leading_signals": [{"signal": T + "领先指标", "type": "filing", "confirms_if": T + "确认条件", "refutes_if": T + "否定条件"}],
        "osint_leads": [],
        "red_team": {"not_real_bottleneck": T, "not_monetized": T, "already_priced": T,
                     "better_alternative": {"ticker": (picks[0]["ticker"] if picks else T), "why": T}, "biggest_kill_shot": T},
        "falsification": [{"condition": T + "可证伪条件", "machine_checkable": False}],
        "serenity_memory": mem,
        "serenity_view": {"would_he_care": "maybe", "why": T + "按 Serenity 框架会怎么看", "playbook_rules": []},
        "research_tier": "amber", "tier_reason": T + "分级理由", "rerate_triggers": [T + "重估触发器"],
        "evidence": evidence,
        "live_data": {"snapshot_path": snapshot_path, "retrieved_at": snap["retrieved_at"],
                      "source_hosts": sorted({urllib.parse.urlparse(e["locator"]).hostname for e in evidence if e.get("locator")}),
                      "warnings_addressed": warnings_addressed},
        "framework_fit": {"role": role, "fit": fitv, "rationale": T + f"机械猜测 {role}/{fitv}，需确认", "rule_ids": [fit.get("rule") or "PB-FIT-01"]},
        "bottleneck_status": {"status": (pos or {}).get("status", "unknown") if (pos or {}).get("status") in {"now", "filling", "coming", "monopoly_not_bottleneck", "diluted_exposure", "resolving", "not_bottleneck"} else "unknown",
                              "kind": (pos or {}).get("kind", "none") if (pos or {}).get("kind") in {"material", "demand", "none"} else "none",
                              "rationale": T + "用实时数据确认图谱状态", "evidence_ids": []},
        "phase": {"stage": {"volume_ramp": "volume_ramp", "rnd_or_sampling": "sampling", "decline_or_cyclical_trough": "decline"}.get(scan.get("phase_guess"), "steady_state"),
                  "evidence": T + f"机械猜测 {scan.get('phase_guess')}", "evidence_ids": []},
        "purity": {"exposure_pct_estimate": None, "basis": "unknown", "rationale": T + "相关业务占比"},
        "risk_tier": "rerating",
        "variant_perception": {"consensus": T + "市场共识", "consensus_sources": [], "our_view": T + "差异化观点（需带数字）",
                               "reason_codes": ["PB-VP-01"], "when_market_sees": T + "市场何时看到",
                               "first_number_to_prove_wrong": {"metric": T, "operator": "<", "threshold": 0, "check_by": T + "YYYY-MM-DD"},
                               "what_changed_since_archive": T + "档案截止后的变化"},
        "next_hop_picks": picks,
        "audit_link": {"research_output_id": f"research:{sym.lower()}-{now.date().isoformat()}", "bundle_validated": False},
        "disclaimer": FRAMEWORK_NOTICE,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache-dir", type=Path, default=Path(os.environ.get("SERENITY_LIVE_CACHE", ".cache/live")))
    ap.add_argument("--offline", action="store_true", help="use cache only; never touch the network")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot"); s.add_argument("ticker"); s.add_argument("--yahoo"); s.add_argument("--news-query")
    s.add_argument("--adr-ratio", type=float, help="ordinary shares per ADS (foreign private issuers)")
    s.add_argument("--no-fts", action="store_true"); s.add_argument("--no-news", action="store_true"); s.add_argument("--out", type=Path)
    s = sub.add_parser("batch", help="several snapshots in parallel (FTS/news off unless asked)")
    s.add_argument("tickers", nargs="+"); s.add_argument("--out-dir", type=Path, required=True)
    s.add_argument("--fts", action="store_true"); s.add_argument("--news", action="store_true")
    s = sub.add_parser("pack", help="fast path: subject + peers + filings excerpts + scan -> brief.md + lens-draft.json")
    s.add_argument("ticker"); s.add_argument("--peers", help="comma list; default = atlas peers on the same node; 'none' to skip")
    s.add_argument("--out-dir", type=Path, required=True); s.add_argument("--news-query"); s.add_argument("--yahoo")
    s.add_argument("--adr-ratio", type=float); s.add_argument("--ledger", type=Path, help="stance_ledger fold output (private)")
    s.add_argument("--no-docs", action="store_true", help="skip 10-K/10-Q keyword excerpts")
    s = sub.add_parser("filing-text", help="SEC document -> text + keyword excerpts")
    s.add_argument("url", nargs="?"); s.add_argument("--ticker"); s.add_argument("--latest", help="form, e.g. 10-K, 10-Q, 20-F, 8-K")
    s.add_argument("--preset", choices=sorted(FILING_TERM_PRESETS)); s.add_argument("--grep", action="append", help="extra regex (repeatable)")
    s.add_argument("--window", type=int, default=280); s.add_argument("--max", type=int, default=3)
    s.add_argument("--text-out", type=Path, help="also write the full plain text here"); s.add_argument("--out", type=Path)
    s = sub.add_parser("quote"); s.add_argument("symbol")
    s = sub.add_parser("fx"); s.add_argument("currency"); s.add_argument("--to", default="USD")
    s = sub.add_parser("fundamentals"); s.add_argument("ticker"); s.add_argument("--yahoo")
    s = sub.add_parser("filings"); s.add_argument("ticker"); s.add_argument("--forms", default=""); s.add_argument("--days", type=int, default=400)
    s = sub.add_parser("fts"); s.add_argument("query"); s.add_argument("--ticker"); s.add_argument("--forms"); s.add_argument("--start"); s.add_argument("--end"); s.add_argument("--limit", type=int, default=10)
    s = sub.add_parser("news"); s.add_argument("query"); s.add_argument("--days", type=int, default=120); s.add_argument("--limit", type=int, default=12)
    s = sub.add_parser("exchange", help="exchange-native block for a non-US symbol (announcements, flags, 2nd quote, TW monthly revenue)")
    s.add_argument("symbol"); s.add_argument("--days", type=int, default=180); s.add_argument("--out", type=Path)
    s = sub.add_parser("etf-holdings", help="latest SEC N-PORT holdings of a US-registered ETF (SMH, SOXX, XSD, PSI, QQQ ...)")
    s.add_argument("etf"); s.add_argument("--top", type=int, default=0, help="keep only the top N holdings (0 = all)"); s.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    fx = Fetcher(cache_dir=args.cache_dir, offline=args.offline)
    if args.cmd == "snapshot":
        out = snapshot(args.ticker, fx, yahoo=args.yahoo, news_query=args.news_query, fts=not args.no_fts,
                       news=not args.no_news, adr_ratio=args.adr_ratio)
    elif args.cmd == "batch":
        snaps = batch(args.tickers, fx, fts=args.fts, news=args.news)
        args.out_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        for t, snap in snaps.items():
            path = args.out_dir / (re.sub(r"[^A-Za-z0-9._-]", "_", snap["subject"]["symbol"]) + ".json")
            path.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            rows.append({**compare_row(snap), "path": str(path)})
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    elif args.cmd == "pack":
        peers = None if args.peers is None else ([] if args.peers.lower() == "none" else [p.strip() for p in args.peers.split(",") if p.strip()])
        res = pack(args.ticker, fx, args.out_dir, peers=peers, news_query=args.news_query, adr_ratio=args.adr_ratio,
                   ledger_path=args.ledger, docs=not args.no_docs, yahoo=args.yahoo)
        print(json.dumps({"brief": str(args.out_dir / "brief.md"), "lens_draft": str(args.out_dir / "lens-draft.json"),
                          "pack": str(args.out_dir / "pack.json"), "peers": res["peers"], "elapsed_seconds": res["elapsed_seconds"],
                          "warnings": {r["symbol"]: r["warnings"] for r in res["compare"]}}, ensure_ascii=False, indent=2))
        return 0
    elif args.cmd == "filing-text":
        terms = terms_from_args(args.preset, args.grep)

        def _ft() -> dict[str, Any]:
            url, meta = args.url, {}
            if not url:
                if not (args.ticker and args.latest):
                    raise ValueError("give a URL or --ticker X --latest FORM")
                cik = sec_cik(fx, resolve_symbol(args.ticker)["symbol"])["cik"]
                hit = latest_filing(sec_submissions(fx, cik), args.latest)
                if not hit:
                    raise KeyError(f"no_{args.latest}_in_recent_filings")
                url, meta = hit["url"], {"form": hit["form"], "filed": hit["filed"], "report_date": hit.get("report_date")}
            res = filing_text(fx, url, terms, args.window, args.max, full_text=bool(args.text_out))
            if args.text_out:
                args.text_out.parent.mkdir(parents=True, exist_ok=True)
                args.text_out.write_text(res.pop("text"), encoding="utf-8")
                res["text_written"] = str(args.text_out)
            return {**meta, **res}
        out = section(_ft)
    elif args.cmd == "quote":
        out = section(lambda: yahoo_quote(fx, resolve_symbol(args.symbol)["symbol"]))
    elif args.cmd == "fx":
        out = section(lambda: fx_rate(fx, args.currency, args.to.upper()))
    elif args.cmd == "fundamentals":
        sym = resolve_symbol(args.ticker, args.yahoo)
        if sym["us_listed"]:
            out = section(lambda: sec_facts(fx, sec_cik(fx, sym["symbol"])["cik"]))
        else:
            out = section(lambda: yahoo_fundamentals(fx, sym["symbol"]))
    elif args.cmd == "filings":
        def _f() -> dict[str, Any]:
            cik = sec_cik(fx, resolve_symbol(args.ticker)["symbol"])["cik"]
            subs = sec_submissions(fx, cik)
            radar = filing_radar(subs, days=args.days)
            radar["issuer_profile"] = issuer_profile(subs)
            if args.forms:
                wanted = {x.strip() for x in args.forms.split(",") if x.strip()}
                radar["matching"] = [f for f in subs["filings"] if f["form"] in wanted][:40]
            return radar
        out = section(_f)
    elif args.cmd == "fts":
        def _fts() -> dict[str, Any]:
            cik = sec_cik(fx, resolve_symbol(args.ticker)["symbol"])["cik"] if args.ticker else None
            return efts_search(fx, args.query, cik=cik, forms=args.forms, start=args.start, end=args.end, limit=args.limit)
        out = section(_fts)
    elif args.cmd == "exchange":
        V = _venues()
        sym = resolve_symbol(args.symbol)["symbol"]
        out = section(lambda: V.exchange_block(fx, sym, quote=section(lambda: yahoo_quote(fx, sym)), days=args.days))
    elif args.cmd == "etf-holdings":
        V = _venues()

        def _etf() -> dict[str, Any]:
            res = V.etf_holdings(fx, args.etf)
            if args.top:
                res["holdings_total"] = len(res["holdings"])
                res["holdings"] = res["holdings"][: args.top]
            return res
        out = section(_etf)
    else:
        out = section(lambda: google_news(fx, args.query, limit=args.limit, days=args.days))
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if getattr(args, "out", None):
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(json.dumps({"written": str(args.out), "status": out.get("status"), "warnings": out.get("warnings"),
                          "evidence": len(out.get("evidence", [])), "elapsed_seconds": out.get("elapsed_seconds")}, ensure_ascii=False))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

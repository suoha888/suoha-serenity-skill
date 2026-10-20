"""v7: exchange-native connectors,
ETF audit, ticker truth and the suoha.py entry point.
All tests are network-free (synthetic bytes / committed fixtures)."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT / "scripts"))
sys.path.insert(0, str(SOURCE_ROOT / "connectors"))

import live_data  # noqa: E402
sys.modules.setdefault("live_data", live_data)
import venues  # noqa: E402
import etf_audit  # noqa: E402
import ticker_truth as tt  # noqa: E402

UTC = timezone.utc
ATLAS = json.loads((SOURCE_ROOT / "assets" / "chokepoint-atlas.json").read_text(encoding="utf-8"))


def tencent_bytes(fields: dict[int, str], n: int = 90) -> bytes:
    f = [""] * n
    for i, v in fields.items():
        f[i] = v
    return ('v_x="' + "~".join(f) + '";').encode("gbk")


class FakeFetcher:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = []

    def get(self, url, kind, **_):
        self.calls.append(url)
        for key, body in self.payloads.items():
            if key in url:
                return body
        raise live_data.SourceError("not_in_fixture")


class VenueParsingTests(unittest.TestCase):
    def test_venue_routing(self):
        self.assertEqual(venues.venue_of("600519.SS")["venue"], "CN")
        self.assertEqual(venues.venue_of("0700.HK")["venue"], "HK")
        self.assertEqual(venues.venue_of("3105.TWO")["venue"], "TW")
        self.assertEqual(venues.venue_of("8035.T")["venue"], "JP")
        self.assertEqual(venues.venue_of("000660.KS")["venue"], "KR")
        self.assertEqual(venues.tencent_code("300308.SZ"), "sz300308")
        self.assertEqual(venues.tencent_code("0700.HK"), "hk00700")
        with self.assertRaises(KeyError):
            venues.tencent_code("MU")

    def test_parse_tencent_cn_gbk_and_units(self):
        raw = tencent_bytes({1: "贵州茅台", 3: "1500.00", 4: "1490.00", 30: "20261016150000", 39: "22.1",
                             45: "18843.6", 46: "7.9", 73: "1256197800", 82: "CNY"})
        q = venues.parse_tencent(raw, "600519.SS", "https://qt.gtimg.cn/q=sh600519")
        self.assertEqual(q["name"], "贵州茅台")
        self.assertEqual(q["price"], 1500.0)
        self.assertEqual(q["market_cap"], 18843.6e8)
        self.assertEqual(q["shares_total"], 1256197800)
        self.assertEqual(q["price_as_of"], "2026-10-16T07:00:00Z")  # Asia/Shanghai -> UTC

    def test_parse_tencent_hk_format(self):
        raw = tencent_bytes({1: "腾讯控股", 3: "600.5", 4: "598", 30: "2026/10/16 16:08:00", 45: "55000", 70: "9100000000", 75: "HKD"})
        q = venues.parse_tencent(raw, "0700.HK", "u")
        self.assertEqual((q["currency"], q["shares_total"], q["pb"]), ("HKD", 9.1e9, None))
        # A+H / dual-class: field 69 = all issued shares, field 70 = the HK-listed line only (BYD 2026-10)
        raw = tencent_bytes({1: "比亚迪股份", 3: "73.85", 30: "2026/10/20 16:08:00", 69: "9117197565", 70: "3683400000", 75: "HKD"})
        q = venues.parse_tencent(raw, "1211.HK", "u")
        self.assertEqual((q["shares_total"], q["line_shares"]), (9117197565, 3683400000))
        with self.assertRaises(KeyError):
            venues.parse_tencent(b'v_pv_none_match="1";', "0700.HK", "u")

    def test_cross_check_flags_disagreement_never_averages(self):
        a = {"status": "ok", "price": 100.0, "price_as_of": "2026-10-16T07:00:00Z"}
        b = {"status": "ok", "price": 100.8, "price_as_of": "2026-10-16T07:00:00Z", "provider": "tencent"}
        self.assertEqual(venues.cross_check(a, b)["status"], "agree")
        bad = venues.cross_check(a, {**b, "price": 110.0})
        self.assertEqual(bad["status"], "mismatch")
        self.assertEqual(bad["price_diff_pct"], 10.0)
        self.assertEqual(venues.cross_check(a, {"status": "unavailable"})["status"], "not_compared")

    def test_title_flags_multilingual(self):
        items = [{"title": "关于向特定对象发行股票的公告", "url": "u1", "published_at": "2026-10-01T00:00:00Z"},
                 {"title": "業績予想の修正に関するお知らせ", "url": "u2", "published_at": "2026-10-02T00:00:00Z"},
                 {"title": "PROFIT WARNING", "url": "u3", "published_at": "2026-10-03T00:00:00Z"},
                 {"title": "关于公司股票可能被实施退市风险警示的公告", "url": "u4", "published_at": "2026-10-04T00:00:00Z"},
                 {"title": "Issue of Debt Securities - 5.25% Notes due 2031", "url": "u5", "published_at": "2026-10-05T00:00:00Z"}]
        flags = {f["flag"]: f for f in venues.title_flags(items)}
        self.assertIn("dilution", flags)
        self.assertEqual(flags["guidance_change"]["count"], 2)
        self.assertEqual(flags["listing_or_going_concern_risk"]["direction"], "negative")
        self.assertEqual(flags["debt_issuance"]["urls"], ["u5"])

    def test_parse_tdnet_page(self):
        html = ('<div>全1件</div><table><tr><td class="kjTime" noWrap>15:30</td><td class="kjCode">80350</td>'
                '<td class="kjName">東京エレクトロン</td><td class="kjTitle" align="left">'
                '<a href="140120261016512345.pdf" target="_blank">2027年3月期 第2四半期決算短信〔日本基準〕(連結)</a></td></tr></table>')
        rows, total = venues.parse_tdnet_page(html, date(2026, 10, 16))
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["code"], "80350")
        self.assertEqual(rows[0]["published_at"], "2026-10-16T06:30:00Z")  # JST -> UTC
        self.assertTrue(rows[0]["url"].startswith("https://www.release.tdnet.info/inbs/"))

    def test_taiwan_monthly_revenue_roc_calendar_and_units(self):
        self.assertEqual(venues._roc_month("11509"), "2026-09")
        row = {"公司代號": "3105", "公司名稱": "穩懋", "產業別": "半導體業", "資料年月": "11509", "出表日期": "1151010",
               "營業收入-當月營收": "2000000", "營業收入-上月比較增減(%)": "5.123", "營業收入-去年同月增減(%)": "30.456",
               "累計營業收入-前期比較增減(%)": "22.2"}
        fx = FakeFetcher({"tpex.org.tw": json.dumps([row]).encode("utf-8")})
        m = venues.taiwan_monthly_revenue(fx, "3105.TWO")
        self.assertEqual((m["system"], m["month"], m["revenue"], m["yoy_pct"]), ("TPEx", "2026-09", 2e9, 30.46))
        self.assertTrue(m["published_at"].startswith("2026-10-10"))
        with self.assertRaises(KeyError):
            venues.taiwan_monthly_revenue(fx, "9999.TWO")

    def test_parse_nport(self):
        xml = b"""<?xml version="1.0"?><edgarSubmission xmlns="http://www.sec.gov/edgar/nport"><formData>
        <genInfo><regName>Example Trust</regName><seriesName>Example Semiconductor ETF</seriesName><seriesId>S000099999</seriesId>
        <repPdDate>2026-06-30</repPdDate></genInfo><fundInfo><netAssets>1000000</netAssets></fundInfo><invstOrSecs>
        <invstOrSec><name>Small Co</name><cusip>111111111</cusip><identifiers><isin value="US1111111111"/></identifiers>
        <valUSD>10000</valUSD><pctVal>1.0</pctVal><assetCat>EC</assetCat><invCountry>US</invCountry></invstOrSec>
        <invstOrSec><name>Big Co</name><cusip>222222222</cusip><identifiers><isin value="US2222222222"/></identifiers>
        <valUSD>200000</valUSD><pctVal>20.0</pctVal><assetCat>EC</assetCat><invCountry>TW</invCountry></invstOrSec>
        </invstOrSecs></formData></edgarSubmission>"""
        n = venues.parse_nport(xml)
        self.assertEqual((n["fund"], n["period_end"], n["net_assets_usd"]), ("Example Semiconductor ETF", "2026-06-30", 1e6))
        self.assertEqual([h["name"] for h in n["holdings"]], ["Big Co", "Small Co"])
        self.assertEqual(n["holdings"][0]["isin"], "US2222222222")


def xch_snap():
    return {"retrieved_at": "2026-10-18T00:00:00Z", "subject": {"symbol": "600000.SS"},
            "quote": {"status": "ok", "symbol": "600000.SS", "price": 10.0, "currency": "CNY",
                      "price_as_of": "2026-10-16T07:00:00Z", "source_url": "https://query1.finance.yahoo.com/x"},
            "fundamentals": {"status": "ok", "provider": "yahoo", "source_url": "https://query1.finance.yahoo.com/y", "summary": {"shares_outstanding": 1_000_000_000, "shares_as_of": "2026-06-30"}},
            "filings": {"status": "unavailable", "error": "non_US_issuer"},
            "exchange": {"venue": "CN", "system": "CNINFO",
                         "second_quote": {"status": "ok", "provider": "tencent", "price": 11.0, "currency": "CNY",
                                          "price_as_of": "2026-10-16T07:00:00Z", "shares_total": 1_100_000_000,
                                          "source_url": "https://qt.gtimg.cn/q=sh600000"},
                         "quote_check": {"status": "mismatch", "second_source": "tencent", "price_diff_pct": 10.0, "note": "n"},
                         "disclosures": {"status": "ok", "system": "CNINFO",
                                         "items": [{"title": "关于公司股票可能被实施退市风险警示的公告", "url": "https://x/1",
                                                    "published_at": "2026-10-10T00:00:00Z"},
                                                   {"title": "2026年半年度报告", "url": "https://x/2",
                                                    "published_at": "2026-08-30T00:00:00Z"}]}}}


class ConnectorPostBoundaryTests(unittest.TestCase):
    def test_form_post_only_to_allowlisted_search_hosts(self):
        f = live_data.Fetcher(offline=True)
        with self.assertRaises(live_data.SourceError) as ctx:
            f.get("https://www1.hkexnews.hk/search", "venue_list", form={"q": "1"})
        self.assertIn("form_post_not_allowlisted", str(ctx.exception))
        self.assertLessEqual(set(live_data.FORM_POST_HOSTS), set(live_data.ALLOWED_HOSTS))

    def test_eval_rejects_post_host_outside_ceiling(self):
        sys.path.insert(0, str(SOURCE_ROOT / "scripts"))
        import run_evals
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "connectors").mkdir()
            (root / "connectors" / "c.py").write_text(
                "import urllib.request\nALLOWED_HOSTS = frozenset({'www.sec.gov'})\n"
                "FORM_POST_HOSTS = frozenset({'www.sec.gov'})\n"
                "def g(h, d):\n    if h not in FORM_POST_HOSTS: raise ValueError\n"
                "    return urllib.request.Request('https://www.sec.gov', data=d, method='POST' if d else 'GET')\n",
                encoding="utf-8")
            errors: list[str] = []
            run_evals.check_connectors(root, errors)
        self.assertIn("connector_post_host_outside_ceiling", " ".join(errors))
        self.assertNotIn("connector_non_get_method", " ".join(errors))


class LiveDataExchangeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.snap = xch_snap()
        disc = self.snap["exchange"]["disclosures"]
        disc["flags"] = venues.title_flags(disc["items"])

    def test_evidence_includes_exchange_items_flagged_first(self):
        ids = {e["evidence_id"]: e for e in live_data.build_evidence(self.snap)}
        self.assertIn("E-LIVE-XCH-01", ids)
        self.assertEqual(ids["E-LIVE-XCH-01"]["locator"], "https://x/1")
        self.assertIn("E-LIVE-XQ", ids)

    def test_quality_warnings_surface_exchange_problems(self):
        w = " | ".join(live_data.quality_warnings(self.snap))
        self.assertIn("quote_cross_check_mismatch", w)
        self.assertIn("exchange_flag_listing_or_going_concern_risk", w)
        self.assertIn("share_count_vs_exchange_+10.0pct", w)

    def test_missing_shares_filled_from_exchange_quote_and_labelled(self):
        s = copy.deepcopy(self.snap)
        s["fundamentals"] = {"status": "unavailable", "error": "x"}
        live_data._shares_from_second_quote(s)
        summ = s["fundamentals"]["summary"]
        self.assertEqual(summ["shares_outstanding"], 1_100_000_000)
        self.assertIn("shares_from_exchange_quote", " ".join(live_data.quality_warnings(s)))


def entry(i, **kw):
    base = {"lens_id": f"t:{i}", "ticker": "AAA", "symbol": "AAA", "tier": "green", "currency": "USD", "entry_price": 10.0,
            "entry_date": "2026-10-16", "researched_at": "2026-10-17T00:00:00Z", "benchmark": "SMH", "method": "lens"}
    return {**base, **kw}


class NameMatchingTests(unittest.TestCase):
    def test_similarity_rules(self):
        self.assertEqual(tt.similarity("TSMC", "Taiwan Semiconductor Manufacturing Company Limited"), 1.0)
        self.assertEqual(tt.similarity("Leaderdrive", "Jiangsu Leader Harmonious Drive Systems"), 1.0)
        self.assertLess(tt.similarity("WIN Semiconductors Corp.", "NXP Semiconductors N.V."), etf_audit.MATCH)
        self.assertLess(tt.similarity("LandMark Optoelectronics", "GCS Holdings, Inc."), tt.NAME_MIN_SIMILARITY)
        self.assertGreaterEqual(tt.similarity("AXT Inc", "AXT, Inc."), 0.99)

    def test_wrong_ticker_in_atlas_is_caught(self):
        truth = {"entries": {"4991.TWO": {"official_name": "GCS Holdings, Inc.", "names": ["GCS Holdings, Inc."], "currency": "TWD"}}}
        atlas = {"chains": [{"chain_id": "c", "nodes": [{"node_id": "n", "status": "now",
                                                         "holders": [{"ticker": "4991.TWO", "name": "LandMark Optoelectronics"}]}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "atlas.json"
            p.write_text(json.dumps(atlas), encoding="utf-8")
            res = tt.check(truth, atlas_path=p)
        self.assertFalse(res["ok"])
        self.assertIn("GCS Holdings", res["errors"][0])

    def test_committed_truth_table_passes(self):
        res = tt.check(tt.load(), lens_paths=sorted((SOURCE_ROOT / "examples").glob("*-serenity-lens.json")))
        self.assertTrue(res["ok"], res["errors"])
        self.assertEqual(tt.load()["entries"]["3081.TWO"]["currency"], "TWD")

    def test_etf_audit_matches_and_reports_gaps(self):
        etf = {"etf": "TEST", "period_end": "2026-06-30",
               "holdings": [{"name": "AXT Inc", "pct": 1.2}, {"name": "NXP Semiconductors NV", "pct": 4.0},
                            {"name": "WIN Semiconductors Corp", "pct": 0.5}]}
        res = etf_audit.audit([etf], ATLAS, tt.load())
        in_etf = {r["ticker"] for r in res["in_etf"]}
        self.assertIn("AXTI", in_etf)
        self.assertIn("3105.TWO", in_etf)
        self.assertIn("NXP Semiconductors NV", [g["name"] for g in res["etf_heavy_not_in_atlas"]])


class EntryPointTests(unittest.TestCase):
    def test_suoha_doctor_offline(self):
        for args in (["doctor"],):
            p = subprocess.run([sys.executable, str(SOURCE_ROOT / "suoha.py"), *args], cwd=SOURCE_ROOT,
                               capture_output=True, text=True, encoding="utf-8", timeout=120)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()

"""v7.1: A-share / Hong Kong statements (aggregator), listing universe and
name resolution, universal company health check, A/H premium, SEC quality
fields and pack integration.  Network-free: synthetic provider payloads."""
import json
import subprocess
import sys
import unittest
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT / "scripts"))
sys.path.insert(0, str(SOURCE_ROOT / "connectors"))

import live_data  # noqa: E402
sys.modules.setdefault("live_data", live_data)
import cnhk_fin  # noqa: E402
import company_check  # noqa: E402
import run_evals  # noqa: E402
import ticker_normalizer as tn  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 10, 18, tzinfo=UTC)


def em(rows):
    return json.dumps({"success": True, "result": {"data": rows}}).encode("utf-8")


class FakeEM:
    """Answers datacenter URLs by reportName (and REPORT_DATE filter for the HK long table)."""

    def __init__(self, tables):
        self.tables, self.urls = tables, []

    def get(self, url, kind="", **_):
        self.urls.append(url)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        rows = self.tables.get(q["reportName"][0], [])
        if callable(rows):
            rows = rows(q["filter"][0])
        return em(rows)


def cn_tables(pledge=35.0, org="通用"):
    base = {"SECURITY_NAME_ABBR": "样例股份", "ORG_TYPE": org, "CURRENCY": "CNY"}
    main = [
        {**base, "REPORT_DATE": "2026-06-30 00:00:00", "REPORT_DATE_NAME": "2026中报", "NOTICE_DATE": "2026-08-20 00:00:00",
         "TOTALOPERATEREVE": 6.0e9, "MLR": 3.0e9, "PARENTNETPROFIT": 1.2e9, "KCFJCXSYJLR": 0.5e9, "NETCASH_OPERATE_PK": 0.3e9,
         "TOTALOPERATEREVETZ": 20.0, "PARENTNETPROFITTZ": -25.0, "DJD_TOI_YOY": 12.0, "XSMLL": 50.0, "TOTAL_SHARE": 1.0e9,
         "TOTAL_EQUITY_PK": 20.0e9, "ZCFZL": 50.0},
        {**base, "REPORT_DATE": "2025-12-31 00:00:00", "REPORT_DATE_NAME": "2025年报",
         "TOTALOPERATEREVE": 11.0e9, "MLR": 5.4e9, "PARENTNETPROFIT": 2.2e9, "KCFJCXSYJLR": 1.0e9, "NETCASH_OPERATE_PK": 0.6e9,
         "TOTAL_SHARE": 1.0e9},
        {**base, "REPORT_DATE": "2025-06-30 00:00:00", "REPORT_DATE_NAME": "2025中报",
         "TOTALOPERATEREVE": 5.0e9, "MLR": 2.5e9, "PARENTNETPROFIT": 1.6e9, "KCFJCXSYJLR": 0.6e9, "NETCASH_OPERATE_PK": 0.1e9,
         "TOTAL_SHARE": 1.0e9},
    ]
    bal = [
        {"REPORT_DATE": "2026-06-30 00:00:00", "ACCOUNTS_RECE": 4.0e9, "INVENTORY": 1.0e9, "CONTRACT_LIAB": 0.3e9, "GOODWILL": 8.0e9,
         "MONETARYFUNDS": 2.0e9, "SHORT_LOAN": 1.0e9, "LONG_LOAN": 3.0e9, "TOTAL_ASSETS": 40.0e9, "TOTAL_LIABILITIES": 20.0e9,
         "TOTAL_PARENT_EQUITY": 20.0e9},
        {"REPORT_DATE": "2025-12-31 00:00:00", "ACCOUNTS_RECE": 3.0e9},
        {"REPORT_DATE": "2025-06-30 00:00:00", "ACCOUNTS_RECE": 2.0e9, "INVENTORY": 0.9e9, "CONTRACT_LIAB": 0.6e9},
    ]
    return {"RPT_F10_FINANCE_MAINFINADATA": main, "RPT_F10_FINANCE_GBALANCE": bal,
            "RPT_CSDC_LIST": [{"TRADE_DATE": "2026-10-16 00:00:00", "PLEDGE_RATIO": pledge, "PLEDGE_DEAL_NUM": 12, "INDUSTRY": "电子元件"}],
            "RPT_SHAREBONUS_DET": [{"REPORT_DATE": "2025-12-31 00:00:00", "EX_DIVIDEND_DATE": "2026-06-10 00:00:00",
                                    "PRETAX_BONUS_RMB": 5.0, "ASSIGN_PROGRESS": "实施分配", "IMPL_PLAN_PROFILE": "10派5元"}]}


YAHOO_CN = {"revenue_quarterly": [{"as_of": "2026-03-31", "value": 2.9e9, "currency": "CNY"},
                                  {"as_of": "2026-06-30", "value": 3.1e9, "currency": "CNY"}]}


def cn_snapshot(**kw):
    fin = live_data.section(lambda: cnhk_fin.financials(FakeEM(cn_tables(**kw)), "600999.SS", YAHOO_CN, NOW))
    snap = {"subject": {"symbol": "600999.SS"}, "retrieved_at": "2026-10-18T00:00:00Z",
            "quote": {"status": "ok", "price": 30.0, "currency": "CNY", "name": "样例股份"},
            "local_financials": fin, "fundamentals": {"status": "ok", "summary": {}},
            "exchange": {"second_quote": {"status": "ok", "provider": "tencent", "pe_ttm": 15.0}}}
    snap["evidence"] = cnhk_fin.evidence(fin, snap["retrieved_at"])
    return snap


class AggregatorParsing(unittest.TestCase):
    def test_secucode(self):
        self.assertEqual(cnhk_fin.secucode("600519.SS"), ("CN", "600519.SH"))
        self.assertEqual(cnhk_fin.secucode("000858.SZ"), ("CN", "000858.SZ"))
        self.assertEqual(cnhk_fin.secucode("0700.HK"), ("HK", "00700.HK"))
        with self.assertRaises(ValueError):
            cnhk_fin.secucode("MU")

    def test_cn_periods_ttm_balance_pledge_dividends(self):
        fin = cn_snapshot()["local_financials"]
        self.assertEqual(fin["status"], "ok")
        self.assertEqual(fin["reporting_currency"], "CNY")
        self.assertEqual(fin["periods"][0]["period_months"], 6)
        self.assertEqual(fin["ttm"]["revenue"]["value"], 12.0e9)  # 6 + 11 - 5
        self.assertIn("YTD 2026-06-30 + FY 2025-12-31 - YTD 2025-06-30", fin["ttm"]["revenue"]["basis"])
        self.assertEqual(fin["ttm"]["net_profit_parent"]["value"], 1.8e9)
        self.assertEqual(fin["yahoo_cross_check"]["status"], "match")
        self.assertEqual(fin["balance"]["year_ago"]["period_end"], "2025-06-30")
        self.assertEqual(fin["pledge"]["pledge_ratio_pct"], 35.0)
        self.assertAlmostEqual(fin["dividends"]["dps_ttm"], 0.5)
        ids = [e["evidence_id"] for e in cnhk_fin.evidence(fin, "2026-10-18T00:00:00Z")]
        self.assertEqual(ids, ["E-LIVE-FIN-CN", "E-LIVE-BAL-CN", "E-LIVE-PLEDGE", "E-LIVE-DIV"])
        self.assertTrue(all(e["source_type"] == "market_data" for e in cnhk_fin.evidence(fin, "x")))
        w = cnhk_fin.warnings(fin, NOW)
        self.assertTrue(any(x.startswith("financials_from_aggregator") for x in w))
        self.assertFalse(any("mismatch" in x for x in w))

    def test_ttm_needs_matching_prior_period(self):
        periods = [{"period_end": "2026-06-30", "period_months": 6, "revenue": 10},
                   {"period_end": "2025-12-31", "period_months": 12, "revenue": 18}]
        self.assertIsNone(cnhk_fin.ttm(periods, "revenue"))
        self.assertEqual(cnhk_fin.ttm(periods[1:], "revenue"), {"value": 18, "basis": "FY 2025-12-31"})

    def test_financial_template_skips_balance_and_flags_definition(self):
        tables = cn_tables(org="银行")
        fin = live_data.section(lambda: cnhk_fin.financials(
            FakeEM(tables), "600036.SS", {"revenue_quarterly": [{"as_of": "2026-03-31", "value": 2.0e9, "currency": "CNY"},
                                                               {"as_of": "2026-06-30", "value": 2.0e9, "currency": "CNY"}]}, NOW))
        self.assertEqual(fin["balance"]["status"], "unavailable")
        w = cnhk_fin.warnings(fin, NOW)
        self.assertTrue(any("definition_differs" in x for x in w), w)

    def test_hk_reporting_currency_confirmed_by_yahoo(self):
        main = [{"REPORT_DATE": "2026-06-30 00:00:00", "START_DATE": "2026-01-01 00:00:00", "SECURITY_NAME_ABBR": "样例控股",
                 "ORG_TYPE": None, "CURRENCY": "HKD", "OPERATE_INCOME": 100.0e9, "HOLDER_PROFIT": 20.0e9, "DPS_HKD": 1.2,
                 "ISSUED_COMMON_SHARES": 9.0e9},
                {"REPORT_DATE": "2025-12-31 00:00:00", "START_DATE": "2025-01-01 00:00:00", "OPERATE_INCOME": 190.0e9, "HOLDER_PROFIT": 38.0e9},
                {"REPORT_DATE": "2025-06-30 00:00:00", "START_DATE": "2025-01-01 00:00:00", "OPERATE_INCOME": 90.0e9, "HOLDER_PROFIT": 18.0e9}]

        def balance(filt):
            if "2026-06-30" in filt:
                return [{"STD_ITEM_NAME": "总资产", "AMOUNT": 500.0e9}, {"STD_ITEM_NAME": "股东权益", "AMOUNT": 300.0e9},
                        {"STD_ITEM_NAME": "总负债", "AMOUNT": 200.0e9}]
            return [{"STD_ITEM_NAME": "总资产", "AMOUNT": 450.0e9}]
        yahoo = {"revenue_quarterly": [{"as_of": "2026-03-31", "value": 49.0e9, "currency": "CNY"},
                                       {"as_of": "2026-06-30", "value": 51.0e9, "currency": "CNY"}]}
        fin = live_data.section(lambda: cnhk_fin.financials(
            FakeEM({"RPT_HKF10_FN_MAININDICATOR": main, "RPT_HKF10_FN_BALANCE_PC": balance}), "9999.HK", yahoo, NOW))
        self.assertEqual(fin["reporting_currency"], "CNY")
        self.assertEqual(fin["listing_currency_field"], "HKD")
        self.assertEqual(fin["ttm"]["revenue"]["value"], 200.0e9)
        self.assertEqual(fin["balance"]["latest"]["equity_parent"], 300.0e9)
        self.assertEqual(fin["balance"]["year_ago"]["period_end"], "2025-06-30")
        unconfirmed = live_data.section(lambda: cnhk_fin.financials(
            FakeEM({"RPT_HKF10_FN_MAININDICATOR": main, "RPT_HKF10_FN_BALANCE_PC": balance}), "9999.HK", None, NOW))
        self.assertIsNone(unconfirmed["reporting_currency"])
        self.assertTrue(any(x.startswith("hk_reporting_currency_unconfirmed") for x in cnhk_fin.warnings(unconfirmed, NOW)))

    def test_empty_provider_is_a_section_error(self):
        out = live_data.section(lambda: cnhk_fin.financials(FakeEM({}), "600999.SS", None, NOW))
        self.assertEqual(out["status"], "unavailable")
        self.assertIn("eastmoney_no_rows", out["error"])

    def test_host_is_allow_listed_and_within_eval_ceiling(self):
        self.assertIn("datacenter.eastmoney.com", live_data.ALLOWED_HOSTS)
        self.assertIn("datacenter.eastmoney.com", run_evals.CONNECTOR_HOST_CEILING)
        self.assertTrue(cnhk_fin.EM.startswith("https://datacenter.eastmoney.com/"))


class CompanyCheck(unittest.TestCase):
    def test_general_company_checks_and_valuation(self):
        r = company_check.check(cn_snapshot())
        self.assertEqual(r["company_type"]["type"], "general")
        by = {c["id"]: c for c in r["checks"]}
        self.assertEqual(by["G2"]["status"], "flag")          # -25% < -20%
        self.assertEqual(by["G3"]["status"], "flag")          # (1.2-0.5)/1.2 = 58%
        self.assertEqual(by["C1"]["status"], "watch")         # OCF TTM 0.8 / profit TTM 1.8 = 0.44
        self.assertAlmostEqual(by["C1"]["value"], 0.44, places=2)
        self.assertEqual(by["B2"]["status"], "watch")         # goodwill 8 / equity 20 = 40%
        self.assertEqual(by["D2"]["status"], "flag")          # pledge 35%
        self.assertEqual(by["W1"]["status"], "flag")          # receivables +100% vs revenue +20%
        self.assertEqual(by["W3"]["status"], "flag")          # contract liabilities -50%
        v = r["valuation"]
        self.assertEqual(v["status"], "ok")
        self.assertEqual(v["market_cap_reporting_ccy"], 30.0e9)
        self.assertAlmostEqual(v["pe_ttm"], 30.0e9 / 1.8e9, places=1)
        self.assertAlmostEqual(v["dividend_yield_pct"], 0.5 / 30 * 100, places=2)
        self.assertEqual(v["pe_cross_check"]["status"], "differs")
        self.assertIn("E-LIVE-PLEDGE", r["evidence_ids"])
        md = company_check.to_markdown(r)
        self.assertIn("公司体检", md)
        self.assertIn("不是买卖结论", md)

    def test_bank_routing_skips_operating_checks(self):
        snap = cn_snapshot(org="银行")
        snap["local_financials"]["periods"][0].update(bank_npl_ratio_pct=3.2, bank_provision_coverage_pct=170.0, bank_cet1_ratio_pct=10.0)
        r = company_check.check(snap)
        self.assertEqual(r["company_type"]["type"], "bank")
        by = {c["id"]: c for c in r["checks"]}
        for skipped in ("P1", "C1", "B1", "W1", "W2", "W3"):
            self.assertNotIn(skipped, by)
        self.assertEqual((by["S1"]["status"], by["S2"]["status"], by["S3"]["status"]), ("flag", "watch", "ok"))

    def test_sec_routing_and_profit_yoy(self):
        snap = {"subject": {"symbol": "XBNK"}, "sec_profile": {"sic_code": "6022", "sic": "State commercial banks"},
                "quote": {"status": "ok", "price": 10.0, "currency": "USD"},
                "fundamentals": {"status": "ok", "provider": "sec_companyfacts",
                                 "summary": {"reporting_currency": "USD", "net_income_ttm": 81.0, "net_income_ttm_year_ago": 100.0,
                                             "revenue_ttm": 400.0, "revenue_ttm_year_ago": 380.0}}}
        r = company_check.check(snap)
        self.assertEqual(r["company_type"]["type"], "bank")
        g2 = next(c for c in r["checks"] if c["id"] == "G2")
        self.assertEqual((g2["value"], g2["status"]), (-19.0, "watch"))
        snap["fundamentals"]["summary"]["net_income_ttm_year_ago"] = -5.0
        g2 = next(c for c in company_check.check(snap)["checks"] if c["id"] == "G2")
        self.assertIsNone(g2["value"])

    def test_small_contract_liabilities_are_info_only(self):
        m = {"revenue_ttm": 1000.0, "contract_liabilities": 5.0, "contract_liabilities_ya": 0.1}
        w3 = next(c for c in company_check.checks(m, "general") if c["id"] == "W3")
        self.assertEqual(w3["status"], "info")

    def test_rules_are_ordered(self):
        for rule, (watch, flag) in company_check.RULES.items():
            self.assertNotEqual(watch, flag, rule)

    def test_cli_on_snapshot_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "snap.json"
            p.write_text(json.dumps(cn_snapshot(), ensure_ascii=False), encoding="utf-8")
            out = subprocess.run([sys.executable, str(SOURCE_ROOT / "scripts" / "company_check.py"), str(p), "--json", str(Path(tmp) / "c.json")],
                                 capture_output=True, text=True, check=True)
            self.assertEqual(out.stdout, "")
            self.assertEqual(json.loads((Path(tmp) / "c.json").read_text(encoding="utf-8"))["check_version"], company_check.CHECK_VERSION)


class PackIntegration(unittest.TestCase):
    def test_draft_lens_turns_flags_into_todo_red_flags(self):
        snap = cn_snapshot()
        snap.update(warnings=[], market_current={})
        health = company_check.check(snap)
        draft = live_data.draft_lens(snap, {}, {}, {"status": "unavailable"}, [], "snap.json", NOW, health)
        cc = [f for f in draft["red_flags"] if f["flag"].startswith("company_check_")]
        self.assertTrue(cc)
        self.assertTrue(all(f["detail"].startswith("TODO: ") and f["triggered"] == "yes" and f["severity"] == "watch" for f in cc))
        self.assertIn("E-LIVE-FIN-CN", cc[0]["evidence_ids"])

    def test_brief_section_2c(self):
        snap = cn_snapshot()
        snap["exchange"]["ah_premium"] = {"status": "ok", "a_symbol": "600999.SS", "h_symbol": "9999.HK", "a_price_cny": 30.0,
                                          "h_price_hkd": 25.0, "hkdcny": 0.9, "premium_pct": 33.33}
        lines = live_data._brief_company_section(snap, company_check.check(snap))
        text = "\n".join(lines)
        self.assertIn("## 2c.", text)
        self.assertIn("+33.3%", text)
        self.assertIn("### 公司体检", text)
        self.assertEqual(live_data._brief_company_section({"subject": {}}, None), [])

    def test_ah_premium(self):
        orig = live_data.fx_rate
        live_data.fx_rate = lambda f, c, to="USD": {"rate": {"HKD": 0.128, "CNY": 0.14}[c], "source_url": f"fx:{c}"}
        try:
            out = live_data.ah_premium(None, {"status": "ok", "price": 50.0}, {"status": "ok", "price": 45.0}, "601318.SS", "2318.HK")
        finally:
            live_data.fx_rate = orig
        hkdcny = 0.128 / 0.14
        self.assertAlmostEqual(out["premium_pct"], round((50 / (45 * hkdcny) - 1) * 100, 2))
        self.assertEqual((out["a_symbol"], out["h_symbol"]), ("601318.SS", "2318.HK"))
        with self.assertRaises(KeyError):
            live_data.ah_premium(None, {"status": "ok", "price": 50.0}, {"status": "unavailable"}, "601318.SS", "2318.HK")

    def test_sec_summary_year_ago_ttm(self):
        def q(end, v):
            return {"end": end, "value": v, "unit": "USD"}
        ends = ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30", "2026-09-30", "2026-12-31"]
        s = live_data.summarize_sec({"revenue": [q(e, 100 + i) for i, e in enumerate(ends)],
                                     "net_income": [q(e, 10 + i) for i, e in enumerate(ends)]})
        self.assertEqual(s["net_income_ttm"], 13 + 14 + 15 + 16 + 4)
        self.assertEqual(s["net_income_ttm_year_ago"], 10 + 11 + 12 + 13)
        self.assertEqual(s["revenue_ttm_year_ago"], 100 + 101 + 102 + 103)


class ListingUniverse(unittest.TestCase):
    def test_universe_files_are_dated_and_well_formed(self):
        for name, minimum in (("cn", 4000), ("hk", 2000), ("us", 5000), ("ah", 100)):
            d = json.loads((SOURCE_ROOT / "assets" / "universe" / f"{name}.json").read_text(encoding="utf-8"))
            self.assertEqual(d["count"], len(d["rows"]))
            self.assertGreaterEqual(d["count"], minimum, name)
            date.fromisoformat(d["as_of"])
            self.assertTrue(all(len(r) == len(d["fields"]) for r in d["rows"][:50]), name)
            self.assertTrue(d["source_urls"])

    def test_names_codes_and_hints(self):
        aliases = tn.load_aliases([tn.SEED_PATH])
        cases = {"贵州茅台": "600519.SS", "騰訊控股": "0700.HK", "腾讯": "0700.HK", "000858": "000858.SZ", "00700": "0700.HK",
                 "苹果": "AAPL", "Apple Inc": "AAPL", "比亚迪": "002594.SZ"}
        for text, want in cases.items():
            self.assertEqual(tn.normalize(text, aliases)["symbol"], want, text)
        self.assertEqual(tn.normalize("中国平安", aliases, hint="港股")["symbol"], "2318.HK")
        self.assertEqual(tn.normalize("阿里巴巴", aliases, hint="美股")["symbol"], "BABA")
        self.assertEqual(tn.normalize("000660", aliases, hint="Korea")["symbol"], "000660.KS")
        res = tn.normalize("601318", aliases)
        self.assertEqual(res["cross_listings"].get("h_share"), "2318.HK")

    def test_ambiguous_name_is_never_guessed(self):
        res = tn.normalize("中国", tn.load_aliases([tn.SEED_PATH]))
        self.assertTrue(res["review_needed"] or res["confidence"] < 0.8)

    def test_suoha_entry_points(self):
        out = subprocess.run([sys.executable, str(SOURCE_ROOT / "suoha.py"), "resolve", "贵州茅台"], capture_output=True, text=True,
                             cwd=SOURCE_ROOT, check=True, encoding="utf-8")
        self.assertIn("600519.SS", out.stdout)
        helptext = subprocess.run([sys.executable, str(SOURCE_ROOT / "suoha.py"), "--help"], capture_output=True, text=True, encoding="utf-8", check=True).stdout
        self.assertIn("check", helptext)


if __name__ == "__main__":
    unittest.main()

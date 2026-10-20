"""v8.2.0: fixes from an external review of v8.1.0.

1. claim <-> evidence-type matrix in the lens validator
2. evidence dated by when it became public (SEC filing date), not period end
3. net debt never assumes zero debt; A+H market cap prices each line; forward
   returns use one price basis and a real peak-to-trough drawdown
4. atlas statuses carry a check date and a 180-day review flag
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "connectors"))

import atlas as atlas_mod  # noqa: E402
import live_data  # noqa: E402
import serenity_lens  # noqa: E402

AXTI = ROOT / "examples" / "axti-serenity-lens.json"


class ClaimEvidenceMatrixTest(unittest.TestCase):
    def lens(self):
        return json.loads(AXTI.read_text(encoding="utf-8"))

    def test_example_passes(self):
        self.assertEqual(serenity_lens.validate(self.lens()), [])

    def test_price_quote_cannot_prove_a_bottleneck(self):
        lens = self.lens()
        md = next(e["evidence_id"] for e in lens["evidence"] if e["source_type"] == "market_data")
        lens["gates"]["real_bottleneck"]["evidence_ids"] = [md]
        errors = serenity_lens.validate(lens)
        self.assertTrue(any(e.startswith("lens:claim_evidence_type_mismatch:gates.real_bottleneck") for e in errors), errors)

    def test_cheap_needs_price_and_fundamentals(self):
        lens = self.lens()
        filing = [e["evidence_id"] for e in lens["evidence"] if e["source_type"] == "filing"][:2]
        gate = lens["gates"]["cheap_derisked"]
        gate["status"], gate["evidence_ids"] = "pass", filing
        errors = serenity_lens.validate(lens)
        self.assertTrue(any("claim_evidence_type_mismatch:gates.cheap_derisked:needs:market_data" in e for e in errors), errors)

    def test_established_chokepoint_needs_fundamental_source(self):
        lens = self.lens()
        lens["chokepoint_of_chokepoint"]["status"] = "established"  # cited ids are social leads
        errors = serenity_lens.validate(lens)
        self.assertTrue(any("claim_evidence_type_mismatch:chokepoint_of_chokepoint" in e for e in errors), errors)


def sec_snap(**summary):
    s = {"shares_outstanding": 1_000_000, "shares_as_of": "2026-07-25", "shares_filed": "2026-08-05",
         "revenue_latest_quarter": {"end": "2026-06-30", "value": 5_000_000, "unit": "USD", "filed": "2026-08-05"},
         "reporting_currency": "USD", **summary}
    return {"retrieved_at": "2026-10-20T00:00:00Z", "subject": {"symbol": "TEST"},
            "quote": {"status": "ok", "symbol": "TEST", "price": 10.0, "currency": "USD", "exchange": "NMS",
                      "price_as_of": "2026-10-19T20:00:00Z", "source_url": "https://q"},
            "fundamentals": {"status": "ok", "provider": "sec_companyfacts", "source_url": "https://sec", "summary": s}}


class EvidenceDateTest(unittest.TestCase):
    def test_sec_figures_dated_by_filing_not_period_end(self):
        ev = {e["evidence_id"]: e for e in live_data.build_evidence(sec_snap())}
        fin, sh = ev["E-LIVE-FIN"], ev["E-LIVE-SHARES"]
        self.assertEqual((fin["published_at"], fin["period_end"], fin["available_basis"]),
                         ("2026-08-05T00:00:00Z", "2026-06-30T00:00:00Z", "sec_filing_date"))
        self.assertEqual((sh["published_at"], sh["period_end"]), ("2026-08-05T00:00:00Z", "2026-07-25T00:00:00Z"))

    def test_unknown_filing_date_falls_back_to_retrieval(self):
        snap = sec_snap()
        del snap["fundamentals"]["summary"]["revenue_latest_quarter"]["filed"]
        fin = {e["evidence_id"]: e for e in live_data.build_evidence(snap)}["E-LIVE-FIN"]
        self.assertEqual(fin["published_at"], "2026-10-20T00:00:00Z")
        self.assertTrue(fin["available_basis"].startswith("retrieved_at"))

    def test_quarterly_rows_keep_filing_date(self):
        rows = [{"start": "2026-04-01", "end": "2026-06-30", "days": 90, "value": 7.0, "unit": "USD", "filed": "2026-08-05"}]
        self.assertEqual(live_data._quarterly(rows)[0]["filed"], "2026-08-05")


class NetDebtTest(unittest.TestCase):
    def draft(self, **summary):
        snap = {"subject": {"symbol": "ZZZZ", "input": "ZZZZ"}, "retrieved_at": "2026-10-20T00:00:00Z",
                "quote": {"name": "ZZZZ", "currency": "USD"}, "evidence": [], "warnings": [],
                "fundamentals": {"status": "ok", "summary": summary}}
        return live_data.draft_lens(snap, {"signals": [], "next_hop_candidates": []}, {"found": False, "positions": []},
                                    {"status": "no_mentions"}, [], "snap.json",
                                    live_data.datetime(2026, 10, 20, tzinfo=live_data.timezone.utc))

    def test_missing_debt_is_not_zero_debt(self):
        d = self.draft(cash_and_st_investments={"end": "2026-06-30", "value": 100.0})
        self.assertNotIn("net_debt", d["valuation"]["current"])
        self.assertTrue(any(w["warning"].startswith("net_debt_unknown: total debt") for w in d["live_data"]["warnings_addressed"]))

    def test_both_known(self):
        d = self.draft(cash_and_st_investments={"end": "2026-06-30", "value": 100.0},
                       total_debt_latest={"end": "2026-06-30", "value": 40.0})
        self.assertEqual(d["valuation"]["current"]["net_debt"], -60.0)


class AHMarketCapTest(unittest.TestCase):
    """BYD 2026-10-20: 9,117,197,565 shares, 3,683,400,000 of them H shares."""

    def snap(self, symbol, price, ccy):
        s = {"retrieved_at": "2026-10-20T00:00:00Z", "subject": {"symbol": symbol},
             "quote": {"status": "ok", "price": price, "currency": ccy, "price_as_of": "2026-10-20T07:00:00Z"},
             "fundamentals": {"status": "ok", "summary": {"shares_outstanding": 9_117_197_565, "shares_as_of": "2026-06-30"}},
             "exchange": {"ah_premium": {"status": "ok", "a_symbol": "002594.SZ", "h_symbol": "1211.HK",
                                         "a_price_cny": 82.6, "h_price_hkd": 73.85, "hkdcny": 0.851035,
                                         "h_shares_exchange": 3_683_400_000}}}
        return live_data.market_current(s)

    def test_each_line_at_its_own_price(self):
        h, a = self.snap("1211.HK", 73.85, "HKD"), self.snap("002594.SZ", 82.6, "CNY")
        expected_cny = 5_433_797_565 * 82.6 + 3_683_400_000 * 73.85 * 0.851035
        self.assertAlmostEqual(a["market_cap"], expected_cny, delta=1e3)
        self.assertAlmostEqual(h["market_cap"] * 0.851035, expected_cny, delta=1e4)
        self.assertAlmostEqual(h["price"] * h["shares_outstanding"], h["market_cap"], delta=1)  # lens arithmetic holds
        self.assertLess(h["ah_lines"]["market_cap_if_all_shares_at_this_price"], h["market_cap"])  # H line was understated

    def test_non_ah_unchanged(self):
        s = {"retrieved_at": "x", "subject": {"symbol": "0700.HK"},
             "quote": {"status": "ok", "price": 400.0, "currency": "HKD", "price_as_of": "2026-10-20T07:00:00Z"},
             "fundamentals": {"status": "ok", "summary": {"shares_outstanding": 9e9, "shares_as_of": "2026-06-30"}}}
        mc = live_data.market_current(s)
        self.assertEqual(mc["market_cap"], 3.6e12)
        self.assertNotIn("ah_lines", mc)


class AtlasFreshnessTest(unittest.TestCase):
    def test_review_flag_after_180_days(self):
        atlas = atlas_mod.load_atlas()
        fresh = atlas_mod.lookup_ticker(atlas, "AXTI", today=date.fromisoformat(atlas["as_of"]))["positions"][0]
        self.assertEqual((fresh["status_checked"], fresh["status_review_due"]), (atlas["as_of"], False))
        late = atlas_mod.lookup_ticker(atlas, "AXTI", today=date(2030, 1, 1))["positions"][0]
        self.assertTrue(late["status_review_due"])

    def test_validator_checks_dates(self):
        atlas = copy.deepcopy(atlas_mod.load_atlas())
        atlas["chains"][0]["nodes"][0]["status_checked"] = "2099-01-01"
        self.assertTrue(any(e.startswith("atlas:status_checked_after_as_of") for e in atlas_mod.validate(atlas)))


if __name__ == "__main__":
    unittest.main()

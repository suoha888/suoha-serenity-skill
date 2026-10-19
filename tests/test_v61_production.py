"""v6.1 production-hardening tests: currency/ADR/share-class arithmetic, stale
SEC tags, exhibit-only going-concern hits, the TODO/evidence-strength lens
gates, the Serenity framework notice, multi-ticker stance regression and the
private-archive update workflow. Network-free; posts are synthetic."""
import copy
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT / "scripts"))
sys.path.insert(0, str(SOURCE_ROOT / "connectors"))

import atlas as atlas_mod  # noqa: E402
import chokepoint_scan  # noqa: E402
import live_data  # noqa: E402
import render_report  # noqa: E402
import serenity_lens  # noqa: E402
import serenity_update  # noqa: E402
import stance_ledger  # noqa: E402
import ticker_normalizer  # noqa: E402
import verify_report  # noqa: E402

UTC = timezone.utc
AXTI_LENS = SOURCE_ROOT / "examples" / "axti-serenity-lens.json"
AXTI_SNAP = SOURCE_ROOT / "examples" / "live" / "axti-snapshot-2026-10-18.json"


def snap(symbol="TEST", currency="USD", price=10.0, shares=1_000_000, fpi=False, adr_ratio=None, **summary):
    s = {"shares_outstanding": shares, "shares_as_of": "2026-09-30", **summary}
    out = {"retrieved_at": "2026-10-18T00:00:00Z",
           "subject": {"symbol": symbol, **({"adr_ratio": adr_ratio} if adr_ratio else {})},
           "quote": {"status": "ok", "price": price, "currency": currency, "price_as_of": "2026-10-17T20:00:00Z"},
           "fundamentals": {"status": "ok", "summary": s}}
    if fpi:
        out["sec_profile"] = {"foreign_private_issuer": True}
    return out


class FakeFX(live_data.Fetcher):
    RATES = {"TWD": 0.031, "GBP": 1.25}

    def __init__(self):
        super().__init__(offline=True)

    def json(self, url, kind):
        for ccy, rate in self.RATES.items():
            if f"{ccy}USD" in url:
                return {"chart": {"result": [{"meta": {"regularMarketPrice": rate, "regularMarketTime": 1792281600,
                                                        "currency": "USD"}}]}}
        raise live_data.SourceError("no_fx")


class MarketArithmeticTest(unittest.TestCase):
    def test_minor_units_are_converted_to_major(self):
        mc = live_data.market_current(snap("IQE.L", currency="GBp", price=2000, shares=100))
        self.assertEqual(mc["currency"], "GBP")
        self.assertAlmostEqual(mc["price"], 20.0)
        self.assertAlmostEqual(mc["market_cap"], 2000.0)
        self.assertTrue(any("minor units" in n for n in mc["notes"]))

    def test_fpi_without_adr_ratio_withholds_market_cap(self):
        mc = live_data.market_current(snap("TSM", price=200, shares=25_000_000_000, fpi=True))
        self.assertIsNone(mc["market_cap"])
        self.assertIn("adr-ratio", mc["market_cap_withheld"])
        mc = live_data.market_current(snap("TSM", price=200, shares=25_000_000_000, fpi=True, adr_ratio=5))
        self.assertAlmostEqual(mc["market_cap"], 200 * 5_000_000_000)

    def test_unreliable_share_classes_withhold(self):
        mc = live_data.market_current(snap("BRK-B", price=500, shares=2_000_000))
        self.assertIsNone(mc["market_cap"])
        w = live_data.quality_warnings({**snap("BRK-B"), "market_current": mc})
        self.assertTrue(any(x.startswith("market_cap_withheld") for x in w))

    def test_usd_view_converts_and_flags_revenue_basis(self):
        s = snap("2408.TW", currency="TWD", price=100, shares=1_000, reporting_currency="TWD", revenue_ttm=None,
                 revenue_latest_quarter={"value": 50.0, "end": "2026-09-30"},
                 revenue_annual_latest={"value": 120.0, "as_of": "2025-12-31"})
        s["market_current"] = live_data.market_current(s)
        uv = live_data.usd_view(s, FakeFX())
        self.assertAlmostEqual(uv["market_cap_usd"], 100_000 * 0.031, places=2)
        self.assertTrue(uv["revenue_basis"].startswith("latest_quarter_x4"))
        self.assertAlmostEqual(uv["revenue_ttm_usd"], 200 * 0.031, places=2)
        self.assertIn("ps_ttm", uv)
        s["usd_view"] = uv
        self.assertTrue(any(w.startswith("revenue_ttm_unavailable") for w in live_data.quality_warnings(s)))

    def test_usd_view_reports_missing_fx(self):
        s = snap("X.KS", currency="KRW", price=1000, shares=10, reporting_currency="KRW", revenue_ttm=5000.0)
        s["market_current"] = live_data.market_current(s)
        uv = live_data.usd_view(s, FakeFX())
        self.assertIsNone(uv["market_cap_usd"])
        self.assertEqual(uv["fx_unavailable"], ["KRW"])

    def test_currency_mismatch_warning(self):
        w = live_data.quality_warnings(snap("TSM", reporting_currency="TWD"))
        self.assertTrue(any(x.startswith("reporting_currency_TWD_differs") for x in w))


class SecSeriesTest(unittest.TestCase):
    @staticmethod
    def facts(**tags):
        return {"facts": {"us-gaap": {t: {"units": {"USD": rows}} for t, rows in tags.items()}}}

    def test_stale_priority_tag_is_skipped(self):
        old = [{"start": "2019-01-01", "end": "2019-03-31", "val": 1, "form": "10-Q", "fp": "Q1", "fy": 2019, "filed": "2019-05-01"}]
        new = [{"start": "2026-04-01", "end": "2026-06-30", "val": 2, "form": "10-Q", "fp": "Q2", "fy": 2026, "filed": "2026-08-01"}]
        name, rows = live_data._sec_series(self.facts(Revenues=old, RevenueFromContractWithCustomerExcludingAssessedTax=new),
                                           ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"), False)
        self.assertTrue(name.endswith("RevenueFromContractWithCustomerExcludingAssessedTax"), name)
        self.assertEqual(rows[-1]["end"], "2026-06-30")


class FetcherMemoTest(unittest.TestCase):
    def test_parallel_callers_share_one_request(self):
        calls = []

        class Counting(live_data.Fetcher):
            def _get(self, url, kind, parsed):
                calls.append(url)
                return b"{}"

        f = Counting(offline=True)
        url = "https://data.sec.gov/submissions/CIK0000000001.json"
        threads = [threading.Thread(target=f.get, args=(url, "sec")) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(calls), 1)
        self.assertEqual(sum(1 for e in f.log if e.get("cache") == "memo"), 7)


class FilingTextTest(unittest.TestCase):
    def test_html_to_text_and_grep(self):
        raw = (b"<html><body><div style='display:none'><ix:header>x</ix:header></div>"
               b"<p>Customers made&nbsp;prepayments under take-or-pay agreements.</p><p>Other</p></body></html>")
        text = live_data.html_to_text(raw)
        self.assertIn("take-or-pay", text)
        hits = live_data.grep_text(text, live_data.terms_from_args("contracts", None))
        self.assertTrue(any(h["count"] for h in hits.values()))
        custom = live_data.grep_text(text, live_data.terms_from_args(None, ["prepayment"]))
        self.assertEqual(next(iter(custom.values()))["count"], 1)

    def test_exhibit_only_going_concern_is_downgraded(self):
        self.assertFalse(chokepoint_scan._is_primary_report({"url": "https://www.sec.gov/Archives/x/ex10-1.htm"}))
        self.assertTrue(chokepoint_scan._is_primary_report({"file_type": "10-K"}))
        self.assertFalse(chokepoint_scan._is_primary_report({"file_type": "EX-10.1"}))
        self.assertTrue(chokepoint_scan._is_primary_report({"primary_document": True, "file_type": "EX-99"}))


class LensGateTest(unittest.TestCase):
    def setUp(self):
        self.lens = json.loads(AXTI_LENS.read_text(encoding="utf-8"))
        self.assertEqual(serenity_lens.validate(self.lens), [])

    def test_todo_fields_are_rejected(self):
        bad = copy.deepcopy(self.lens)
        bad["one_liner"] = "TODO: write the one-liner"
        self.assertIn("lens:unfilled_todo:document.one_liner", serenity_lens.find_todos(bad))
        self.assertTrue(any(e.startswith("lens:unfilled_todo") for e in serenity_lens.validate(bad)))
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x-lens.json"
            p.write_text(json.dumps(bad), encoding="utf-8")
            self.assertEqual(serenity_lens.finish(p, bad), 1)
            self.assertFalse((Path(tmp) / "x-report.md").exists())

    def test_finish_renders_and_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "axti-lens.json"
            p.write_text(json.dumps(self.lens), encoding="utf-8")
            self.assertEqual(serenity_lens.finish(p, self.lens), 0)
            md = (Path(tmp) / "axti-report.md").read_text(encoding="utf-8")
            self.assertIn(render_report.FRAMEWORK_NOTICE, md)

    def test_gate_pass_on_news_only_is_rejected(self):
        bad = copy.deepcopy(self.lens)
        news = [e["evidence_id"] for e in bad["evidence"] if e["source_type"] == "news"][:1]
        self.assertTrue(news)
        bad["gates"]["real_bottleneck"]["evidence_ids"] = news
        self.assertIn("lens:gate_pass_requires_non_lead_evidence:real_bottleneck", serenity_lens.validate(bad))

    def test_current_price_needs_market_data(self):
        bad = copy.deepcopy(self.lens)
        filing = [e["evidence_id"] for e in bad["evidence"] if e["source_type"] == "filing"][:1]
        bad["valuation"]["current"]["evidence_ids"] = filing
        self.assertIn("lens:current_price_requires_market_data_evidence", serenity_lens.validate(bad))

    def test_disclaimer_must_disown_serenity_view(self):
        bad = copy.deepcopy(self.lens)
        bad["disclaimer"] = "本报告仅供研究与教学讨论使用，所有数字均来自公开资料并可能有误，非投资建议。"
        self.assertIn("lens:disclaimer_must_state_not_serenity_view", serenity_lens.validate(bad))

    def test_report_without_framework_notice_fails_verify(self):
        md = render_report.to_markdown(self.lens).replace(render_report.FRAMEWORK_NOTICE, "")
        htm = render_report.to_html(self.lens).replace(render_report.FRAMEWORK_NOTICE, "")
        self.assertTrue(verify_report.verify_markdown(md, None))
        self.assertTrue(verify_report.verify(htm))

    def test_draft_lens_from_snapshot_is_all_todo(self):
        s = json.loads(AXTI_SNAP.read_text(encoding="utf-8"))
        atlas = atlas_mod.load_atlas()
        scan = chokepoint_scan.scan_snapshot(s, atlas)
        draft = live_data.draft_lens(s, scan, atlas_mod.lookup_ticker(atlas, "AXTI"),
                                     {"status": "no_mentions", "source": "stance_ledger", "note": "n/a"},
                                     [], str(AXTI_SNAP), datetime(2026, 10, 18, tzinfo=UTC))
        self.assertTrue(serenity_lens.find_todos(draft))
        self.assertRegex(draft["disclaimer"], serenity_lens.SERENITY_NOTICE_RE)
        self.assertEqual(draft["valuation"]["current"]["evidence_ids"][:1], ["E-LIVE-QUOTE"])


class StanceRegressionTest(unittest.TestCase):
    def setUp(self):
        self.aliases = ticker_normalizer.load_aliases([SOURCE_ROOT / "assets" / "ticker-aliases.seed.json"])

    def test_multi_ticker_commentary_is_not_bearish(self):
        post = {"id": "1000000000000000001", "created_at": "2026-05-01T00:00:00Z",
                "text": "Funny how people copy shorts from $AAA to $BBB and dump both."}
        events = stance_ledger.extract_post(post, self.aliases)
        self.assertTrue(events)
        for e in events:
            self.assertNotEqual(e["stance"], "bearish", e)

    def test_single_ticker_buy_still_bullish(self):
        post = {"id": "1000000000000000002", "created_at": "2026-05-01T00:00:00Z", "text": "I bought more $AAA today."}
        events = stance_ledger.extract_post(post, self.aliases)
        self.assertEqual([e["stance"] for e in events], ["bullish"])

    def test_lens_memory_reports_archive_through(self):
        events = [{"schema_version": "5.0", "post_id": "1000000000000000003", "created_at": "2026-05-01T00:00:00Z",
                   "ticker": "AAA", "action": "ADD", "stance": "bullish", "conviction": 0.8, "cue": "bought",
                   "is_reply": False, "extractor": "test", "review_status": "machine", "access_level": "public",
                   "source_partition": "public"}]
        led = stance_ledger.fold(events, datetime(2026, 10, 1, tzinfo=UTC))
        self.assertTrue(led["archive_through"].startswith("2026-05-01"))
        mem = stance_ledger.lens_memory(led, "AAA")
        self.assertIn("archive_through", mem)
        self.assertIn("not a sell", mem["note"])
        self.assertIn("archive_through", stance_ledger.lens_memory(led, "ZZZ"))


class SerenityUpdateTest(unittest.TestCase):
    def test_normalise_x_export_and_plain_rows(self):
        x = serenity_update.normalise({"tweet": {"id_str": "1000000000000000010", "full_text": "hello $AAA",
                                                 "created_at": "Wed Oct 10 20:19:24 +0000 2018"}})
        self.assertEqual(x["created_at"], "2018-10-10T20:19:24Z")
        self.assertEqual(x["access_level"], "public")
        self.assertIsNone(serenity_update.normalise({"id": "abc", "text": "x", "created_at": "2026-01-01"}))
        ms = serenity_update.normalise({"id": 1000000000000000011, "text": "t", "created_at": 1767225600000})
        self.assertTrue(ms["created_at"].startswith("2026-01-01"))

    def test_ingest_dedupes_and_manifest_has_no_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            priv, inc = Path(tmp) / "priv", Path(tmp) / "new.jsonl"
            rows = [{"id": "1000000000000000020", "text": "Bought more $AAA, the bottleneck is substrates.",
                     "created_at": "2026-06-01T00:00:00Z"},
                    {"id": "1000000000000000020", "text": "Bought more $AAA, the bottleneck is substrates.",
                     "created_at": "2026-06-01T00:00:00Z"},
                    {"id": "1000000000000000021", "text": "Watching $BBB lasers.", "created_at": "2026-05-01T00:00:00Z"}]
            inc.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
            self.assertEqual(serenity_update.main(["ingest", str(inc), "--private-dir", str(priv)]), 0)
            stored = [json.loads(l) for l in (priv / "posts.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([p["id"] for p in stored], ["1000000000000000021", "1000000000000000020"])
            manifest = serenity_update.build_manifest(stored, [], set())
            blob = json.dumps(manifest)
            self.assertNotIn("substrates", blob)
            self.assertEqual(manifest["post_count"], 2)

    def test_leak_scan(self):
        post = {"id": "1000000000000000030",
                "text": "one two three four five six seven eight nine ten eleven twelve thirteen"}
        with tempfile.TemporaryDirectory() as tmp:
            leak, clean = Path(tmp) / "leak.md", Path(tmp) / "clean.md"
            leak.write_text("Quote: one two three four five six seven eight nine ten eleven twelve.", encoding="utf-8")
            clean.write_text("Paraphrase: the post lists numbers one to five.", encoding="utf-8")
            hits = serenity_update.leak_scan([post], [leak, clean])
            self.assertEqual([Path(h["file"]).name for h in hits], ["leak.md"])

    def test_guard_refuses_unignored_path_inside_repo(self):
        with self.assertRaises(SystemExit):
            serenity_update.guard_private_path(SOURCE_ROOT / "references" / "posts.jsonl")
        serenity_update.guard_private_path(Path(tempfile.gettempdir()) / "posts.jsonl")

    def test_public_manifest_carries_no_post_text(self):
        manifest = json.loads((SOURCE_ROOT / "assets" / "serenity-archive-manifest.json").read_text(encoding="utf-8"))
        def walk(v):
            if isinstance(v, dict):
                for k, x in v.items():
                    self.assertNotIn(k, {"text", "full_text", "post_text"})
                    walk(x)
            elif isinstance(v, list):
                for x in v:
                    walk(x)
        walk(manifest)


if __name__ == "__main__":
    unittest.main()

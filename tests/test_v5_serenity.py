"""v5 Serenity Lens, memory layer, backtest, eval, and report pipeline tests."""
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT / "scripts"))

import eval_alignment  # noqa: E402
import forward_returns  # noqa: E402
import render_report  # noqa: E402
import serenity_lens  # noqa: E402
import stance_ledger  # noqa: E402
import ticker_normalizer  # noqa: E402
import verify_report  # noqa: E402

EXAMPLE = SOURCE_ROOT / "tests" / "fixtures" / "amd-v5-contract-lens.json"
SHIPPED_AMD = SOURCE_ROOT / "examples" / "amd-serenity-lens.json"
UTC = timezone.utc


def load_example():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def ev(post_id, day, ticker, action, stance="neutral", conviction=None, partition="public"):
    out = {"schema_version": "5.0", "post_id": str(post_id), "created_at": f"{day}T12:00:00Z",
           "ticker": ticker, "action": action, "stance": stance, "extractor": "test",
           "access_level": partition, "source_partition": partition}
    if conviction is not None:
        out["conviction"] = conviction
    else:
        out["conviction"] = stance_ledger.ACTION_WEIGHT[action]
    return out


class SerenityLensContractTest(unittest.TestCase):
    def test_example_passes_and_compute_is_idempotent(self):
        lens = load_example()
        self.assertEqual(serenity_lens.validate(lens), [])
        self.assertEqual(serenity_lens.compute(lens)["valuation"], lens["valuation"])

    def test_compute_fills_derived_numbers(self):
        lens = load_example()
        lens["valuation"]["current"]["market_cap"] = 1
        for sc in lens["valuation"]["scenarios"]:
            sc["implied_market_cap"] = sc["implied_per_share"] = sc["vs_current_pct"] = 0
        fixed = serenity_lens.compute(lens)
        self.assertEqual(serenity_lens.validate(fixed), [])
        base = fixed["valuation"]["scenarios"][1]
        a = base["assumptions"]
        self.assertAlmostEqual(base["implied_market_cap"], a["revenue"] * a["net_margin"] * a["multiple"], places=0)

    def assertError(self, lens, fragment):
        errors = serenity_lens.validate(lens)
        self.assertTrue(any(fragment in e for e in errors), f"{fragment!r} not in {errors}")

    def test_arithmetic_tampering_is_caught(self):
        lens = load_example()
        lens["valuation"]["scenarios"][2]["implied_per_share"] *= 1.5
        self.assertError(lens, "implied_per_share_mismatch:bull")
        lens = load_example()
        lens["valuation"]["current"]["market_cap"] *= 1.2
        self.assertError(lens, "market_cap_mismatch")

    def test_scenarios_must_increase(self):
        lens = load_example()
        lens["valuation"]["scenarios"][0]["assumptions"]["revenue"] = 5e11
        lens = serenity_lens.compute(lens)
        self.assertError(lens, "scenario_values_must_increase")

    def test_freshness_and_cutoff(self):
        lens = load_example()
        lens["valuation"]["current"]["price_as_of"] = "2026-09-01T00:00:00Z"
        self.assertError(lens, "stale_price")
        lens = load_example()
        lens["evidence"][0]["published_at"] = "2026-12-01T00:00:00Z"
        self.assertError(lens, "evidence_after_cutoff")
        lens = load_example()
        lens["serenity_memory"]["timeline"][0]["date"] = "2027-01-01"
        self.assertError(lens, "memory_event_after_cutoff")

    def test_unknown_evidence_and_vague_assumption(self):
        lens = load_example()
        lens["capex_certainty"]["evidence_ids"].append("ev:does-not-exist")
        self.assertError(lens, "unknown_evidence_id")
        lens = load_example()
        lens["valuation"]["scenarios"][1]["assumption_sources"] = ["assumption:x"]
        self.assertError(lens, "assumption_source_too_vague")

    def test_veto_forces_red_and_green_gating(self):
        lens = load_example()
        lens["red_flags"][-1]["triggered"] = "yes"
        self.assertError(lens, "triggered_veto_requires_red_tier")
        lens = load_example()
        lens["research_tier"] = "green"
        self.assertError(lens, "green_cannot_have_failed_gate")
        lens = load_example()
        lens["rerate_triggers"] = []
        self.assertError(lens, "amber_requires_rerate_triggers")

    def test_advice_boundary(self):
        lens = load_example()
        lens["one_liner"] = "AMD strong buy now"
        self.assertError(lens, "advice_language")
        lens = load_example()
        lens["valuation"]["target_price"] = 900
        self.assertError(lens, "forbidden_execution_key")
        lens = load_example()
        lens["serenity_memory"]["timeline"][0]["text"] = "verbatim"
        errors = serenity_lens.validate(lens)
        self.assertTrue(errors)
        lens = load_example()
        lens["disclaimer"] = "This report is provided for research and educational discussion only."
        self.assertError(lens, "disclaimer_must_state_not_investment_advice")

    def test_red_team_must_be_specific(self):
        lens = load_example()
        lens["red_team"]["biggest_kill_shot"] = "估值过高。"
        self.assertError(lens, "red_team_too_thin")
        lens = load_example()
        lens["red_team"]["biggest_kill_shot"] = "competition is the main risk to this thesis"
        self.assertEqual(serenity_lens.validate(lens), [])

    def test_playbook_ids_are_enforced(self):
        lens = load_example()
        lens["serenity_view"]["playbook_rules"].append("PB-MADE-UP-99")
        self.assertError(lens, "unknown_playbook_rule:PB-MADE-UP-99")
        lens = load_example()
        lens["archetype_hits"][0]["archetype"] = "ARC-NOT-REAL"
        self.assertError(lens, "unknown_archetype:ARC-NOT-REAL")

    def test_chain_map_needs_upstream_and_subject(self):
        lens = load_example()
        lens["chain_map"]["layers"] = [l for l in lens["chain_map"]["layers"] if not l["layer"].startswith("upstream")]
        self.assertError(lens, "chain_map_requires_upstream_layer")

    def test_memory_unavailable_cannot_carry_timeline(self):
        lens = load_example()
        lens["serenity_memory"]["status"] = "unavailable"
        self.assertError(lens, "memory_timeline_requires_available_status")


class TickerNormalizerTest(unittest.TestCase):
    def setUp(self):
        self.aliases = ticker_normalizer.load_aliases([SOURCE_ROOT / "assets" / "ticker-aliases.seed.json"])

    def test_suffix_alias_and_ambiguity(self):
        r = ticker_normalizer.normalize("6669.TW", self.aliases)
        self.assertEqual((r["symbol"], r["currency"], r["review_needed"]), ("6669.TW", "TWD", False))
        r = ticker_normalizer.normalize("$SIVE", self.aliases)
        self.assertEqual(r["symbol"], "SIVE.ST")
        r = ticker_normalizer.normalize("3110", self.aliases)
        self.assertTrue(r["review_needed"])
        self.assertIsNone(r["symbol"])
        r = ticker_normalizer.normalize("3110", self.aliases, hint="Japan")
        self.assertEqual(r["symbol"], "3110.T")


class StanceLedgerTest(unittest.TestCase):
    AS_OF = datetime(2026, 6, 30, tzinfo=UTC)

    def test_point_in_time_has_no_leakage(self):
        events = [ev(100001, "2026-01-10", "SIVE", "MENTION", "bullish"),
                  ev(100002, "2026-05-01", "SIVE", "OPEN", "bullish", 0.8)]
        early = stance_ledger.fold(events, datetime(2026, 3, 1, tzinfo=UTC))
        self.assertEqual(early["tickers"]["SIVE"]["holding_status"], "unknown")
        self.assertEqual(early["skipped_future_events"], 1)
        before = stance_ledger.fold(events, datetime(2026, 1, 1, tzinfo=UTC))
        self.assertEqual(stance_ledger.lens_memory(before, "SIVE")["status"], "no_mentions")

    def test_deny_close_and_silence_are_distinct(self):
        events = [ev(200001, "2026-06-01", "AAA", "DENY"),
                  ev(200002, "2026-01-05", "BBB", "OPEN", "bullish", 0.8),
                  ev(200003, "2026-06-01", "BBB", "CLOSE"),
                  ev(200004, "2026-01-05", "CCC", "OPEN", "bullish", 0.8)]
        led = stance_ledger.fold(events, self.AS_OF)["tickers"]
        self.assertEqual((led["AAA"]["state"], led["AAA"]["holding_status"]), ("DENIED", "denied"))
        self.assertEqual((led["BBB"]["state"], led["BBB"]["holding_status"]), ("CLOSED", "cleared"))
        self.assertEqual((led["CCC"]["state"], led["CCC"]["holding_status"]), ("DORMANT", "held"))

    def test_decay_respects_grace_and_half_life(self):
        self.assertEqual(stance_ledger._decayed(0.8, 10, 21, 45), 0.8)
        self.assertAlmostEqual(stance_ledger._decayed(0.8, 66, 21, 45), 0.4, places=6)

    def test_private_partition_and_verbatim_refused(self):
        events = [ev(300001, "2026-06-01", "DDD", "OPEN", "bullish", 0.8, partition="subscription")]
        led = stance_ledger.fold(events, self.AS_OF)
        self.assertEqual((led["ticker_count"], led["skipped_private_events"]), (0, 1))
        bad = [{**ev(300002, "2026-06-01", "DDD", "MENTION"), "text": "copy"}]
        with self.assertRaises(ValueError):
            stance_ledger.fold(bad, self.AS_OF)

    def test_rule_extractor_basics(self):
        aliases = ticker_normalizer.load_aliases([SOURCE_ROOT / "assets" / "ticker-aliases.seed.json"])
        out = stance_ledger.extract_post({"id": "400001", "created_at": "2026-05-01T00:00:00Z",
                                          "text": "I don't own any $XYZQ shares."}, aliases)
        self.assertEqual([(e["ticker"], e["action"]) for e in out], [("XYZQ", "DENY")])
        self.assertNotIn("text", out[0])

    def test_lens_memory_validates_inside_lens(self):
        events = [ev(500001, "2026-04-01", "AMD", "MENTION", "bullish"),
                  ev(500002, "2026-05-01", "AMD", "REAFFIRM", "bullish")]
        mem = stance_ledger.lens_memory(stance_ledger.fold(events, datetime(2026, 10, 17, tzinfo=UTC)), "AMD")
        lens = load_example()
        lens["serenity_memory"] = mem
        self.assertEqual(serenity_lens.validate(lens), [])


class ForwardReturnsTest(unittest.TestCase):
    def prices(self):
        start = date(2026, 1, 1)
        return [(start + timedelta(days=i), 100 + i + 1, 100 + i - 1, 100.0 + i) for i in range(40)]

    def test_next_close_prevents_lookahead(self):
        p = self.prices()
        sig = {"signal_id": "s1", "ticker": "T", "created_at": "2026-01-05T15:00:00Z"}
        nxt = forward_returns.evaluate(sig, p)
        same = forward_returns.evaluate(sig, p, entry="same_close")
        self.assertEqual(nxt["entry_date"], "2026-01-06")
        self.assertEqual(same["entry_date"], "2026-01-05")
        self.assertAlmostEqual(nxt["d1_return_pct"], (106 / 105 - 1) * 100, places=2)
        self.assertEqual(nxt["d30_return_pct"] is not None, True)
        summary = forward_returns.summarize([nxt, {"status": "no_price_data"}])
        self.assertEqual((summary["signals"], summary["evaluated"]), (2, 1))

    def test_adverse_move_vs_peak_to_trough_drawdown(self):
        # v8.2: +50% then -40% from the peak: only -10% vs entry (adverse) but a -40% drawdown
        d = date(2026, 1, 1)
        closes = [100, 100, 150, 90, 120]
        p = [(d + timedelta(days=i), c, c, float(c)) for i, c in enumerate(closes)]
        out = forward_returns.evaluate({"signal_id": "s", "ticker": "T", "created_at": "2026-01-01"}, p)
        self.assertEqual(out["entry_close"], 100.0)
        self.assertAlmostEqual(out["max_runup_pct"], 50.0)
        self.assertAlmostEqual(out["max_adverse_pct"], -10.0)
        self.assertAlmostEqual(out["max_drawdown_pct"], -40.0)

    def test_high_low_scaled_to_adjusted_close(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "T.csv"
            f.write_text("date,open,high,low,close,adj_close\n2026-01-02,10,11,9,10,5\n", encoding="utf-8")
            (_d, high, low, close), = forward_returns.load_prices(f)
        self.assertEqual((high, low, close), (5.5, 4.5, 5.0))

    def test_missing_entry_bar(self):
        sig = {"signal_id": "s2", "ticker": "T", "created_at": "2027-01-01T00:00:00Z"}
        self.assertEqual(forward_returns.evaluate(sig, self.prices())["status"], "no_entry_bar")


class EvalAlignmentTest(unittest.TestCase):
    def test_make_cases_is_blind_and_scores(self):
        events = [ev(600001, "2026-01-01", "AAA", "MENTION"),
                  ev(600002, "2026-02-01", "AAA", "OPEN", "bullish", 0.8),
                  ev(600003, "2026-02-10", "AAA", "ADD", "bullish", 0.9),
                  ev(600004, "2026-03-01", "BBB", "BEARISH", "bearish", 0.6),
                  ev(600005, "2026-03-05", "BBB", "BEARISH", "bearish", 0.6)]
        cases, answers = eval_alignment.make_cases(events, lead_days=14, horizon_days=60,
                                                   min_events=2, seed=1, negatives=0)
        self.assertEqual(len(cases), 2)
        for c in cases:
            self.assertNotIn("label", c)
            self.assertNotIn("first_call_post_id", c)
        a_map = {a["case_id"]: a for a in answers}
        aaa = next(c for c in cases if c["ticker"] == "AAA")
        self.assertLess(aaa["as_of"], "2026-02-01")
        self.assertEqual(a_map[aaa["case_id"]]["label"], "bullish")
        perfect = {cid: {"stance": a["label"], "confidence": 0.9} for cid, a in a_map.items()}
        s = eval_alignment.score(a_map, perfect)
        self.assertEqual((s["accuracy"], s["coverage"]), (1.0, 1.0))
        half = {aaa["case_id"]: {"stance": "bearish", "confidence": 0.9}}
        s = eval_alignment.score(a_map, half)
        self.assertEqual((s["accuracy"], s["coverage"]), (0.0, 0.5))


class ReportPipelineTest(unittest.TestCase):
    def test_render_verify_and_tamper_detection(self):
        lens = load_example()
        html_text = render_report.to_html(lens)
        md_text = render_report.to_markdown(lens)
        self.assertEqual(verify_report.verify(html_text), [])
        with tempfile.TemporaryDirectory() as tmp:
            lp = Path(tmp) / "lens.json"
            lp.write_text(json.dumps(lens, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(verify_report.verify_markdown(md_text, lp), [])
            changed = copy.deepcopy(lens)
            changed["one_liner"] = changed["one_liner"] + "（改）"
            lp.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
            self.assertIn("report:lens_hash_mismatch_render_again", verify_report.verify_markdown(md_text, lp))
        bear = f"{lens['valuation']['scenarios'][0]['implied_per_share']:.2f}"
        tampered = html_text.replace(f"<td>{bear}</td>", "<td>999.99</td>", 1)
        self.assertTrue(any("visible_scenario_differs" in e for e in verify_report.verify(tampered)))
        tampered = html_text.replace('"research_tier":"amber"', '"research_tier":"green"', 1)
        self.assertIn("report:embedded_lens_hash_mismatch", verify_report.verify(tampered))
        stripped = html_text.replace("id='red-team'", "id='x'")
        self.assertIn("report:missing_section:red-team", verify_report.verify(stripped))

    def test_renderer_refuses_invalid_lens(self):
        lens = load_example()
        lens["research_tier"] = "green"
        with tempfile.TemporaryDirectory() as tmp:
            lp = Path(tmp) / "bad.json"
            lp.write_text(json.dumps(lens, ensure_ascii=False), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = render_report.main([str(lp), "--out-dir", tmp])
            self.assertNotEqual(code, 0)
            self.assertFalse((Path(tmp) / "bad.html").exists())

    def test_html_escapes_untrusted_text(self):
        lens = load_example()
        lens["chain_map"]["layers"][0]["nodes"][0]["role"] = "<script>alert(1)</script>"
        self.assertNotIn("<script>alert(1)", render_report.to_html(lens).split("id='lens-data'")[0])

    def test_shipped_example_reports_are_current(self):
        lens = json.loads(SHIPPED_AMD.read_text(encoding="utf-8"))
        html_path = SOURCE_ROOT / "examples" / "amd-serenity-report.html"
        md_path = SOURCE_ROOT / "examples" / "amd-serenity-report.md"
        self.assertEqual(verify_report.verify(html_path.read_text(encoding="utf-8")), [])
        self.assertEqual(verify_report.verify_markdown(md_path.read_text(encoding="utf-8"), SHIPPED_AMD), [])
        self.assertEqual(lens["lens_id"], "lens:amd-2026-10-19")


if __name__ == "__main__":
    unittest.main()

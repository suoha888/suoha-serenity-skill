import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import company_check as cc  # noqa: E402


def row(cid, status, value=None):
    return {"id": cid, "area": "x", "label": cid, "value": value, "unit": "%", "status": status, "formula": "f"}


class StageTest(unittest.TestCase):
    def test_ramp_stage_moves_profit_flags_to_info_and_keeps_trace(self):
        m = {"revenue_yoy_pct": 60.0, "profit_ttm": -5.0}
        st = cc.stage(m, {}, "general")
        self.assertEqual(st["stage"], "ramp")
        rows = [row("P3", "flag", -40), row("G2", "watch", -10), row("B2", "flag", 1)]
        cc.apply_stage(rows, m, {}, st, "general")
        by = {r["id"]: r for r in rows}
        self.assertEqual(by["P3"]["status"], "info")
        self.assertEqual(by["P3"]["stage_adjusted_from"], "flag")
        self.assertEqual(by["G2"]["status"], "info")
        self.assertEqual(by["B2"]["status"], "flag")  # balance-sheet risk is never waived

    def test_loss_without_growth_is_not_ramp(self):
        st = cc.stage({"revenue_yoy_pct": 2.0, "profit_ttm": -1.0}, {}, "general")
        self.assertEqual(st["stage"], "loss_no_growth")

    def test_cyclical_high_and_financial(self):
        st = cc.stage({"revenue_yoy_pct": 80.0, "profit_ttm": 10.0, "profit_yoy_pct": 300.0}, {"pe_ttm": 6.0}, "general")
        self.assertEqual(st["stage"], "cyclical_high")
        self.assertIn("周期压力测试", "".join(cc.verify_list([], st)).replace("单期年化利润做压力测试", "周期压力测试"))
        self.assertEqual(cc.stage({"profit_ttm": -1, "revenue_yoy_pct": 90}, {}, "bank")["stage"], "operating")

    def test_cash_runway_and_dilution_exception(self):
        m = {"revenue_yoy_pct": 100.0, "profit_ttm": -5.0, "ocf_ttm": -50.0, "capex_ttm": 10.0, "cash": 300.0}
        st = cc.stage(m, {}, "general")
        rows = [row("D1", "flag", 20.0)]
        cc.apply_stage(rows, m, {}, st, "general")
        by = {r["id"]: r for r in rows}
        self.assertEqual(by["R1"]["value"], 60.0)          # 300 / (60/12)
        self.assertEqual(by["R1"]["status"], "ok")
        self.assertEqual(by["D1"]["status"], "watch")       # revenue/share +66.7% beats dilution
        self.assertIn("ATM", by["D1"]["why"])

    def test_dilution_flag_stays_when_growth_does_not_cover_it(self):
        m = {"revenue_yoy_pct": 5.0, "profit_ttm": 1.0}
        rows = [row("D1", "flag", 30.0)]
        cc.apply_stage(rows, m, {}, cc.stage(m, {}, "general"), "general")
        self.assertEqual(rows[0]["status"], "flag")

    def test_ps_scored_by_stage(self):
        slow = {"revenue_yoy_pct": 10.0, "profit_ttm": 1.0}
        rows = []
        cc.apply_stage(rows, slow, {"ps_ttm": 35.0}, cc.stage(slow, {}, "general"), "general")
        self.assertEqual(rows[-1]["status"], "flag")
        ramp = {"revenue_yoy_pct": 60.0, "profit_ttm": -1.0}
        rows = []
        cc.apply_stage(rows, ramp, {"ps_ttm": 35.0}, cc.stage(ramp, {}, "general"), "general")
        self.assertEqual(rows[-1]["status"], "watch")
        fast = {"revenue_yoy_pct": 80.0, "profit_ttm": 1.0}
        rows = []
        cc.apply_stage(rows, fast, {"ps_ttm": 35.0}, cc.stage(fast, {}, "general"), "general")
        self.assertEqual(rows, [])

    def test_empty_snapshot_is_insufficient_not_clean(self):
        r = cc.check({"subject": {"symbol": "XYZ"}})
        self.assertEqual(r["data_status"], "insufficient")
        self.assertEqual(r["counts"]["flag"], 0)
        self.assertIn("数据不足", r["notes"][0])
        md = cc.to_markdown(r)
        self.assertIn("需核实清单", md)


if __name__ == "__main__":
    unittest.main()


import json  # noqa: E402

import render_report  # noqa: E402
import serenity_lens  # noqa: E402

AXTI = Path(__file__).resolve().parents[1] / "examples" / "axti-serenity-lens.json"


class LensV9FieldsTest(unittest.TestCase):
    def lens(self):
        L = json.loads(AXTI.read_text(encoding="utf-8"))
        L["phase"]["kpis"] = [{"kpi": "认证/客户导入进度", "status": "on_track", "note": "以公司电话会原话为准"}]
        L["dilution"] = {"class": "private_placement", "share_count_yoy_pct": 8.0, "use_of_funds": "扩产",
                         "per_share_growth_covers": "yes", "detail": "融资用于扩产，每股收入增速高于股本增速"}
        L["verify_checklist"] = [{"item": "主题业务收入占比", "status": "pending"}]
        return L

    def test_old_lenses_still_valid_and_new_fields_render(self):
        self.assertEqual(serenity_lens.validate(json.loads(AXTI.read_text(encoding="utf-8"))), [])
        L = self.lens()
        self.assertEqual(serenity_lens.validate(L), [])
        md, html = render_report.to_markdown(L), render_report.to_html(L)
        for text in ("阶段 KPI", "稀释分类", "定增", "财务需核实清单", "主题业务收入占比"):
            self.assertIn(text, md)
            self.assertIn(text, html)
        self.assertLess(md.index("## 8. 红旗筛查"), md.index("稀释分类"))
        self.assertLess(md.index("稀释分类"), md.index("## 9. 红队"))

    def test_uncovered_atm_blocks_green(self):
        L = self.lens()
        L["research_tier"] = "green"
        L["dilution"].update({"class": "atm", "per_share_growth_covers": "no"})
        self.assertIn("lens:uncovered_atm_dilution_blocks_green", serenity_lens.validate(L))

    def test_problem_item_needs_note(self):
        L = self.lens()
        L["verify_checklist"][0]["status"] = "problem"
        self.assertIn("lens:verify_problem_requires_note", serenity_lens.validate(L))


import re  # noqa: E402

import serenity_timeline as stl  # noqa: E402


class PublicTimelineTest(unittest.TestCase):
    def test_asset_shape_ids_only(self):
        d = stl.load()
        self.assertGreater(d["entry_count"], 1000)
        for t, rows in d["tickers"].items():
            for e in rows:
                self.assertTrue(e["p"] and all(re.fullmatch(r"[0-9]{5,25}", p) for p in e["p"]), t)
                self.assertIn(e["s"], stl.STANCE_ZH)
                self.assertNotIn("http", e["c"])
        self.assertNotIn("SIVE", d["tickers"])  # cashtag aliases merged into SIVE.ST

    def test_memory_is_point_in_time_and_lens_valid(self):
        m = stl.memory("SIVEF", "2026-04-01")
        self.assertEqual(m["status"], "available")
        self.assertLessEqual(len(m["timeline"]), 12)
        self.assertTrue(all(x["date"] <= "2026-04-01" and len(x["summary"]) <= 200 for x in m["timeline"]))
        L = json.loads(AXTI.read_text(encoding="utf-8"))
        L["serenity_memory"] = stl.memory("AXTI", L["research_cutoff"][:10])
        self.assertEqual(serenity_lens.validate(L), [])

    def test_unknown_ticker_is_not_a_view(self):
        m = stl.memory("ZZZZQ")
        self.assertEqual(m["status"], "no_mentions")
        self.assertIn("不代表看空", m["note"])
        self.assertIn("公开时间线无记录", stl.dossier("ZZZZQ"))

    def test_neutral_context_is_not_a_stance_change(self):
        rows = [{"d": "2026-01-01", "s": "bull"}, {"d": "2026-01-02", "s": "neutral"}, {"d": "2026-01-03", "s": "bull"}]
        self.assertEqual(len(stl.changes(rows)), 1)

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

"""v9.1 integrity fixes: EV multiples need net debt; snapshot warnings cannot be silently dropped."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import serenity_lens as sl  # noqa: E402

AMD = json.loads((ROOT / "examples" / "amd-serenity-lens.json").read_text(encoding="utf-8"))


def ev_lens(with_net_debt: bool) -> dict:
    lens = copy.deepcopy(AMD)
    for sc in lens["valuation"]["scenarios"]:
        sc["assumptions"]["multiple_basis"] = "ev_sales"
    if not with_net_debt:
        lens["valuation"]["current"].pop("net_debt", None)
    return sl.compute(lens)


class EvSalesNetDebtTest(unittest.TestCase):
    def test_ev_sales_without_net_debt_is_rejected(self):
        self.assertIn("lens:ev_sales_requires_net_debt", sl.validate(ev_lens(False)))

    def test_ev_sales_with_net_debt_passes_this_check(self):
        self.assertNotIn("lens:ev_sales_requires_net_debt", sl.validate(ev_lens(True)))

    def test_ps_without_net_debt_is_unaffected(self):
        lens = copy.deepcopy(AMD)
        for sc in lens["valuation"]["scenarios"]:
            sc["assumptions"]["multiple_basis"] = "ps"
        lens["valuation"]["current"].pop("net_debt", None)
        self.assertNotIn("lens:ev_sales_requires_net_debt", sl.validate(sl.compute(lens)))


class SnapshotWarningsTest(unittest.TestCase):
    WARN = ["share_count_older_than_200_days",
            "sec_filings_not_applicable_non_us: read exchange filings (DART/MOPS/TDnet/RNS)"]

    def lens_with(self, tmp: Path, addressed: list[str], snapshot: bool = True) -> dict:
        snap = tmp / "snapshots" / "X.json"
        snap.parent.mkdir(parents=True, exist_ok=True)
        if snapshot:
            snap.write_text(json.dumps({"warnings": self.WARN}), encoding="utf-8")
        lens = copy.deepcopy(AMD)
        lens["live_data"]["snapshot_path"] = str(snap)
        lens["live_data"]["warnings_addressed"] = [
            {"warning": w, "handling": "已在第 6 节说明处理方式并改用交易所公告核实"} for w in addressed]
        return lens

    def test_emptied_list_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            errs = sl.validate(self.lens_with(Path(d), []))
            self.assertIn("lens:snapshot_warning_not_addressed:share_count_older_than_200_days", errs)
            self.assertIn("lens:snapshot_warning_not_addressed:sec_filings_not_applicable_non_us", errs)

    def test_partial_list_names_the_missing_one(self):
        with tempfile.TemporaryDirectory() as d:
            errs = [e for e in sl.validate(self.lens_with(Path(d), [self.WARN[0]])) if "snapshot_warning" in e]
            self.assertEqual(errs, ["lens:snapshot_warning_not_addressed:sec_filings_not_applicable_non_us"])

    def test_code_only_entry_counts_as_addressed(self):
        with tempfile.TemporaryDirectory() as d:
            lens = self.lens_with(Path(d), ["share_count_older_than_200_days", "sec_filings_not_applicable_non_us"])
            self.assertFalse([e for e in sl.validate(lens) if "snapshot_warning" in e])

    def test_missing_snapshot_skips_check(self):
        with tempfile.TemporaryDirectory() as d:
            lens = self.lens_with(Path(d), [], snapshot=False)
            self.assertFalse([e for e in sl.validate(lens) if "snapshot_warning" in e])

    def test_relative_snapshot_path_resolved_next_to_lens(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            lens = self.lens_with(tmp, [])
            lens["live_data"]["snapshot_path"] = "work/x-2026/snapshots/X.json"
            self.assertFalse([e for e in sl.validate(lens) if "snapshot_warning" in e])  # not found from cwd/root
            errs = sl.validate(lens, base=tmp)  # finish passes the lens folder; snapshots/X.json sits there
            self.assertIn("lens:snapshot_warning_not_addressed:share_count_older_than_200_days", errs)


if __name__ == "__main__":
    unittest.main()

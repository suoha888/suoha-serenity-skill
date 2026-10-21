"""v9 compliance checks: subscription posts never cited, timeline has no look-ahead, public wording."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import serenity_timeline as tl  # noqa: E402
import serenity_update as su  # noqa: E402

PUB = "1900000000000000001"
SUB = "1900000000000000002"


def archive(tmp: Path) -> Path:
    p = tmp / "posts.jsonl"
    rows = [
        {"id": PUB, "text": "alpha beta gamma delta", "created_at": "2026-01-01T00:00:00Z", "access_level": "public"},
        {"id": SUB, "text": "zeta eta theta iota", "created_at": "2026-01-02T00:00:00Z", "access_level": "subscription"},
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return p


def run_check(arc: Path, root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "serenity_update.py"), "check",
                           "--archive", str(arc), "--root", str(root), "--ngram", "8"],
                          capture_output=True, text=True)


class RestrictedIdScanTest(unittest.TestCase):
    def test_subscription_id_is_caught_public_id_is_fine(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            posts = list(su.load_archive(archive(tmp)).values())
            ok = tmp / "ok.md"
            ok.write_text(f"公开帖 {PUB}；更长的数字 9{SUB}9 不算。", encoding="utf-8")
            bad = tmp / "bad.md"
            bad.write_text(f"见 `{SUB}`", encoding="utf-8")
            hits = su.restricted_id_scan(posts, [ok, bad])
            self.assertEqual([h["file"] for h in hits], [str(bad)])
            self.assertEqual(hits[0]["posts"], [SUB])

    def test_check_command_fails_on_subscription_id(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            arc = archive(tmp)
            root = tmp / "repo"
            root.mkdir()
            (root / "README.md").write_text(f"来源 {SUB}", encoding="utf-8")
            res = run_check(arc, root)
            self.assertEqual(res.returncode, 1, res.stdout)
            self.assertIn("subscription-only", res.stdout)
            (root / "README.md").write_text(f"来源 {PUB}", encoding="utf-8")
            res = run_check(arc, root)
            self.assertEqual(res.returncode, 0, res.stdout)


class TimelineNoLookAheadTest(unittest.TestCase):
    def test_as_of_never_returns_later_entries(self):
        data = tl.load()
        for key in list(data["tickers"])[:60]:
            rows = data["tickers"][key]
            cut = rows[len(rows) // 2]["d"]
            mem = tl.memory(key, as_of=cut, data=data)
            self.assertLessEqual(mem["archive_through"], cut)
            for e in mem.get("timeline", []):
                self.assertLessEqual(e["date"], cut, key)
            if mem["status"] == "available":
                self.assertLessEqual(mem["last_mention"], cut)

    def test_before_first_mention_is_no_mentions(self):
        data = tl.load()
        key = next(iter(data["tickers"]))
        mem = tl.memory(key, as_of="2000-01-01", data=data)
        self.assertEqual(mem["status"], "no_mentions")


PUBLIC_DOCS = ["README.md", "README.en.md", "SKILL.md", "references/serenity-exceptions.md",
               "references/serenity-case-library.md", "docs/CHANGELOG.md"]
BANNED = re.compile(r"(最完整|稳赚|保证收益|必涨|建议买入|建议卖出|立即买入|强烈推荐|推荐买入)")


class PublicWordingTest(unittest.TestCase):
    def test_no_promotional_or_advice_wording(self):
        for name in PUBLIC_DOCS:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertEqual([m.group(0) for m in BANNED.finditer(text)], [], name)

    def test_paraphrase_and_disclaimer_notes_present(self):
        case = (ROOT / "references/serenity-case-library.md").read_text(encoding="utf-8")
        self.assertIn("他自己承认错了", case)
        self.assertIn("不构成投资建议", case)
        self.assertIn("转述", (ROOT / "references/serenity-exceptions.md").read_text(encoding="utf-8"))
        note = json.loads((ROOT / "assets/serenity-public-timeline.json").read_text(encoding="utf-8"))["note"]
        self.assertIn("no subscription content", note)
        self.assertIn("not investment advice", note)

    def test_timeline_entries_only_cite_post_ids(self):
        timeline = json.loads((ROOT / "assets/serenity-public-timeline.json").read_text(encoding="utf-8"))
        for rows in timeline["tickers"].values():
            for e in rows:
                self.assertTrue(e["p"] and all(re.fullmatch(r"\d{15,20}", p) for p in e["p"]))
                self.assertNotIn("http", e["c"])


if __name__ == "__main__":
    unittest.main()

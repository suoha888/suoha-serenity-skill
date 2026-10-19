"""Offline release and entry-point regressions; no third-party dependencies."""
import contextlib
import argparse
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "connectors"))
import suoha
import venues
import validate_skill

class EntryPoint(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "suoha.py"), *args],
                              capture_output=True, text=True, encoding="utf-8")

    def test_unknown_ticker_is_friendly(self):
        p = self.cli("check", "XXXXXX")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("resolve", p.stderr)
        self.assertIn("无法识别", p.stderr)
        self.assertNotIn("Traceback", p.stderr)

    def test_missing_argument_is_friendly(self):
        p = self.cli("check")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("Missing files/arguments", p.stderr)
        self.assertNotIn("Traceback", p.stderr)

    def test_debug_anywhere_keeps_traceback(self):
        p = self.cli("check", "XXXXXX", "--debug")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("Traceback", p.stderr)

    def test_old_python(self):
        err = io.StringIO()
        with patch.object(sys, "version_info", (3, 9)), contextlib.redirect_stderr(err):
            self.assertEqual(suoha.main(["doctor"]), 1)
        self.assertIn("Python 3.10+", err.getvalue())

    def test_missing_file(self):
        err = io.StringIO()
        with patch.object(suoha, "dispatch", side_effect=FileNotFoundError()), contextlib.redirect_stderr(err):
            self.assertEqual(suoha.main(["doctor"]), 1)
        self.assertIn("Missing files", err.getvalue())

    def test_timeout(self):
        err = io.StringIO()
        with patch.object(suoha, "dispatch", side_effect=TimeoutError()), contextlib.redirect_stderr(err):
            self.assertEqual(suoha.main(["check", "AAPL"]), 1)
        self.assertIn("Network/data source", err.getvalue())

    def test_child_traceback_hidden(self):
        failed = subprocess.CompletedProcess([], 1, "", "Traceback: secret-path\nTimeoutError")
        err = io.StringIO()
        with patch.object(subprocess, "run", return_value=failed), contextlib.redirect_stderr(err):
            suoha.DEBUG = False
            self.assertEqual(suoha.run([sys.executable, "missing.py"], "network"), 1)
        self.assertNotIn("Traceback", err.getvalue())
        self.assertIn("Network/data source", err.getvalue())

    def test_unavailable_json_nonzero(self):
        result = subprocess.CompletedProcess([], 0, json.dumps({"status": "unavailable"}), "")
        with patch.object(subprocess, "run", return_value=result):
            self.assertEqual(suoha.run([sys.executable, "x.py"], check=False), 1)

    def test_doctor_ticker(self):
        p = self.cli("doctor", "--ticker", "XXXXXX")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("Ticker unresolved", p.stderr)

    def test_resolve_three_markets(self):
        self.assertEqual([suoha.normalized_ticker(x) for x in ("600519", "00700", "AAPL")],
                         ["600519.SS", "0700.HK", "AAPL"])

    def test_empty_snapshot_is_not_successful_health_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap = Path(tmp) / "snapshot.json"
            snap.write_text(json.dumps({"quote": {"status": "unavailable"}}), encoding="utf-8")
            args = argparse.Namespace(ticker="AAPL", out=str(snap), yahoo=None)
            err = io.StringIO()
            with patch.object(suoha, "run", return_value=0) as run, contextlib.redirect_stderr(err):
                self.assertEqual(suoha.cmd_check(args), 1)
            self.assertEqual(run.call_count, 1)
            self.assertIn("Network/data source", err.getvalue())

    def test_doctor_missing_installation(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()) as err:
            with patch.object(suoha, "ROOT", Path(tmp)):
                self.assertEqual(suoha.cmd_doctor(argparse.Namespace(online=False, ticker=None)), 1)
            self.assertIn("Missing files", err.getvalue())

class ReleaseChecks(unittest.TestCase):
    def test_plain_yaml_colon_rejected(self):
        with self.assertRaises(ValueError):
            validate_skill.parse_frontmatter('---\nname: test\ndescription: Also: broken\n---')
        parsed = validate_skill.parse_frontmatter('---\nname: test\ndescription: "Also: valid"\n---')
        self.assertEqual(parsed["description"], "Also: valid")

    def test_windows_timezone_fallback(self):
        with patch.object(venues, "ZoneInfo", side_effect=venues.ZoneInfoNotFoundError()):
            tz = venues.venue_timezone("TEST", "Asia/Shanghai", 8)
        self.assertEqual(datetime(2026, 1, 1, tzinfo=tz).utcoffset(), timedelta(hours=8))
        with patch.dict(venues.TZ, {"TEST": tz}):
            self.assertEqual(venues._utc(datetime(2026, 1, 1, 8), "TEST"), "2026-01-01T00:00:00Z")
            with self.assertRaises(ValueError):
                venues._utc(datetime(1980, 1, 1), "TEST")
        venues.FALLBACK_VENUES.discard("TEST")

if __name__ == "__main__":
    unittest.main()

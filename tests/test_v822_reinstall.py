import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT / "scripts"))

from build_runtime import build_runtime  # noqa: E402
from runtime_common import is_user_artifact  # noqa: E402
from verify_runtime import verify_runtime  # noqa: E402


def _simulate_user_run(runtime_root: Path) -> None:
    (runtime_root / ".cache" / "live").mkdir(parents=True)
    (runtime_root / ".cache" / "live" / "abc.cache").write_text("cached", encoding="utf-8")
    (runtime_root / "work" / "NBIS").mkdir(parents=True)
    (runtime_root / "work" / "NBIS" / "report.md").write_text("my report", encoding="utf-8")
    for folder in (runtime_root / "__pycache__", runtime_root / "scripts" / "__pycache__"):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "x.cpython-313.pyc").write_bytes(b"\0")


class ReinstallAfterUseTest(unittest.TestCase):
    def test_user_artifact_classification(self):
        for relative in ("work/a/report.md", ".cache/live/x.cache", "__pycache__/a.pyc",
                         "scripts/__pycache__/b.pyc", "connectors/c.pyc"):
            self.assertTrue(is_user_artifact(relative), relative)
        for relative in ("SKILL.md", "scripts/build_runtime.py", "workbench/x.md", "docs/work.md"):
            self.assertFalse(is_user_artifact(relative), relative)

    def test_reinstall_after_running_keeps_reports_and_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "suoha-serenity-skill"
            build_runtime(SOURCE_ROOT, runtime_root)
            _simulate_user_run(runtime_root)
            self.assertEqual(verify_runtime(SOURCE_ROOT, runtime_root)["status"], "pass")

            second = build_runtime(SOURCE_ROOT, runtime_root, replace=True)

            self.assertEqual(
                (runtime_root / "work" / "NBIS" / "report.md").read_text(encoding="utf-8"), "my report"
            )
            self.assertTrue((runtime_root / ".cache" / "live" / "abc.cache").is_file())
            self.assertFalse((runtime_root / "__pycache__").exists())
            self.assertEqual(sorted(second["preserved_user_data"]), [".cache", "work"])
            self.assertTrue(Path(second["replacement_backup"]).is_dir())
            self.assertEqual(verify_runtime(SOURCE_ROOT, runtime_root)["status"], "pass")
            # A third install (update again) still works.
            build_runtime(SOURCE_ROOT, runtime_root, replace=True)
            self.assertTrue((runtime_root / "work" / "NBIS" / "report.md").is_file())

    def test_modified_skill_file_still_refuses_with_chinese_hint(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "suoha-serenity-skill"
            build_runtime(SOURCE_ROOT, runtime_root)
            (runtime_root / "SKILL.md").write_text("edited", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "改名备份"):
                build_runtime(SOURCE_ROOT, runtime_root, replace=True)
            self.assertEqual((runtime_root / "SKILL.md").read_text(encoding="utf-8"), "edited")

    @unittest.skipUnless(sys.platform != "win32", "bash installer")
    def test_install_sh_twice_with_user_data(self):
        with tempfile.TemporaryDirectory() as home:
            env = {"SUOHA_INSTALL_ROOT": home, "PATH": "/usr/bin:/bin:/usr/local/bin", "PYTHON": sys.executable}
            first = subprocess.run(["bash", str(SOURCE_ROOT / "install.sh"), "claude"], env=env,
                                   capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            runtime_root = Path(home) / ".claude" / "skills" / "suoha-serenity-skill"
            _simulate_user_run(runtime_root)
            second = subprocess.run(["bash", str(SOURCE_ROOT / "install.sh"), "claude"], env=env,
                                    capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertTrue((runtime_root / "work" / "NBIS" / "report.md").is_file())


if __name__ == "__main__":
    unittest.main()

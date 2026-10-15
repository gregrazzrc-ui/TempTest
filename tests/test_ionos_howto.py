"""Offline consistency check for the IONOS MariaDB lab how-to.

Ensures the guide points to the actual TempTest source and recorded live evidence.
Does not connect to IONOS or access GitHub Secrets.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class IonosHowToContract(unittest.TestCase):
    def test_documented_target_matches_bridge(self):
        howto = (ROOT / "docs/IONOS-MARIADB-DATABASE-HOWTO.md").read_text(encoding="utf-8")
        bridge = (ROOT / "deploy/temp513-bridge.php").read_text(encoding="utf-8")
        uploader = (ROOT / "scripts/deploy_temp513_sftp.py").read_text(encoding="utf-8")
        for value in ("dbs16231513", "db5021656421.hosting-data.io", "dbu5597618",
                      "temptest_chat_probe_513_v1"):
            with self.subTest(value=value):
                self.assertIn(value, howto)
                self.assertIn(value, bridge)
        self.assertIn("access-5021528741.webspace-host.com", uploader)
        self.assertIn("su78426", uploader)
        self.assertIn("public-temptest", howto)
        self.assertIn("CURRENT_USER()", howto)
        self.assertIn("USER()", howto)

    def test_evidence_and_limits_are_explicit(self):
        guide = (ROOT / "docs/IONOS-MARIADB-DATABASE-HOWTO.md").read_text(encoding="utf-8")
        for run in ("38772988725", "38773221229", "38773458699", "38773537809", "38773804071"):
            with self.subTest(run=run):
                self.assertIn(run, guide)
        self.assertIn("not yet been exercised", guide)
        self.assertIn("unmerged", guide)
        self.assertIn("remove", guide.lower())
        self.assertIn("secrets", guide.lower())

    def test_navigation_is_present(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        short = (ROOT / "docs/CHAT-BRIDGE.md").read_text(encoding="utf-8")
        self.assertIn("docs/IONOS-MARIADB-DATABASE-HOWTO.md", readme)
        self.assertIn("IONOS-MARIADB-DATABASE-HOWTO.md", short)


if __name__ == "__main__":
    unittest.main()

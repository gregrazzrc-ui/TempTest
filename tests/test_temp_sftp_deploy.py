"""Offline deployment safety checks. No network or GitHub secrets."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import deploy_temp513_sftp as deploy


class DeployGuardsTests(unittest.TestCase):
    def test_refuse_other_repositories_and_triggers(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(deploy.Refuse, "WRONG_REPOSITORY_OR_BRANCH"):
                deploy.verify_local({}, Path(tmp))

    def test_missing_host_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "deploy").mkdir()
            (base / "deploy/temp513-bridge.php").write_text(
                "<?php // TempTest dbs16231513 db5021656421.hosting-data.io", encoding="utf-8")
            env = {
                "GITHUB_REPOSITORY": deploy.REPO,
                "GITHUB_REF": deploy.BRANCH,
                "GITHUB_EVENT_NAME": "push",
                "GITHUB_ACTOR": "gregrazzrc-ui",
                "TEMPTEST_SFTP_UPLOAD_APPROVED": "YES_ONLY_PUBLIC_TEMPTEST",
                "FHQ_TEMP_SFTP_USERNAME": "su78426",
                "FHQ_TEMP_SFTP_PASSWORD": "fake-not-a-real-secret"
            }
            with self.assertRaisesRegex(deploy.Refuse, "SOURCE_OR_PINNED_HOST_KEY_MISSING"):
                deploy.verify_local(env, base)
            (base / "deploy/ionos_sftp_known_hosts").write_text("wrong.example.test ssh-ed25519 AAAATESTKEY\n")
            with self.assertRaisesRegex(deploy.Refuse, "HOST_KEY_NOT_VERIFIED"):
                deploy.verify_local(env, base)


class HomeChecksTests(unittest.TestCase):
    def test_refuses_wrong_webspace_page(self):
        class BadSftp:
            class FakeFile:
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def read(self, _): return b"unrelated PHP application"
            def open(self, *args): return self.FakeFile()
        with self.assertRaisesRegex(deploy.Refuse, "WRONG_SFTP_HOME"):
            deploy.verify_sftp_home(BadSftp())

    def test_refuses_existing_target(self):
        class Sftp:
            class FakeFile:
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def read(self, _): return b"TempTest Database lab dbs16231513"
            def open(self, *args): return self.FakeFile()
            def listdir(self, *_): return ["index.php", "temp513-bridge.php"]
        with self.assertRaisesRegex(deploy.Refuse, "REMOTE_TARGET_ALREADY_PRESENT"):
            deploy.verify_sftp_home(Sftp())


if __name__ == "__main__":
    unittest.main()

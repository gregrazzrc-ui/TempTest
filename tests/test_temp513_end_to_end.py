"""Offline acceptance regression tests: mocked endpoint, never contacts MariaDB."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import temp_db_513_bridge as gate
import accept_temp513_database as smoke


class EndToEndGuardTests(unittest.TestCase):
    def environment(self, folder):
        return {
            "GITHUB_REPOSITORY": gate.REPO,
            "GITHUB_ACTOR": gate.OWNER,
            "GITHUB_REF": smoke.BRANCH,
            "GITHUB_EVENT_NAME": "push",
            "FHQ_TEMP_DB_513_HOST": gate.HOST,
            "FHQ_TEMP_DB_513_USERNAME": gate.USERNAME,
            "FHQ_TEMP_DB_513_PASSWORD": "test-not-real",
            "RUNNER_TEMP": str(folder)
        }

    def run_with_trigger(self, folder, operation, responses, env=None):
        trigger = Path(folder) / "mode.txt"
        trigger.write_text(operation + "\n")
        values = self.environment(folder) if env is None else env
        with patch.object(smoke, "TRIGGER", trigger), patch.dict(os.environ, values, clear=True):
            with patch.object(smoke.endpoint, "request_endpoint", side_effect=responses) as remote:
                outcome = smoke.main()
        return outcome, remote.call_args_list, json.loads((Path(folder) / smoke.REPORT).read_text())

    def test_no_write_when_actor_is_not_owner(self):
        with tempfile.TemporaryDirectory() as folder:
            env = self.environment(folder)
            env["GITHUB_ACTOR"] = "other"
            result, calls, report = self.run_with_trigger(folder, "FULL", [], env)
            self.assertEqual(result, 1)
            self.assertEqual(calls, [])
            self.assertEqual(report["reason"], "UNAUTHORIZED_ACCEPTANCE_CONTEXT")

    def test_full_sequence_and_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            responses = [{"table_exists": False}]
            responses += [{"row_count": 3} for _ in range(4)]
            responses += [{"row_count": 2} for _ in range(2)]
            responses += [{"cleaned": True}]
            responses += [{"table_exists": False}]
            self.assertEqual(len(responses), 9)
            result, calls, report = self.run_with_trigger(folder, "FULL", responses)
            self.assertEqual(result, 0)
            self.assertEqual([x.args[1] for x in calls],
                ["status", "create", "read", "update", "read", "delete", "read", "cleanup", "status"])
            self.assertEqual(report["status"], "PASS")
            self.assertNotIn("test-not-real", json.dumps(report))

    def test_existing_fixture_refuses_write(self):
        with tempfile.TemporaryDirectory() as folder:
            result, calls, report = self.run_with_trigger(folder, "FULL", [{"table_exists": True}])
            self.assertEqual(result, 1)
            self.assertEqual([x.args[1] for x in calls], ["status"])
            self.assertEqual(report["reason"], "EXISTING_FIXTURE_REFUSED")

    def test_status_mode_never_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            result, calls, report = self.run_with_trigger(folder, "STATUS", [{"table_exists": False}])
            self.assertEqual(result, 0)
            self.assertEqual([x.args[1] for x in calls], ["status"])
            self.assertEqual(report["mode"], "STATUS")

    def test_cleanup_after_failed_create_attempt(self):
        with tempfile.TemporaryDirectory() as folder:
            responses = [{"table_exists": False}, gate.ProbeBlocked("CREATE_FAILED"), {"cleaned": True}]
            result, calls, report = self.run_with_trigger(folder, "FULL", responses)
            self.assertEqual(result, 1)
            self.assertEqual([x.args[1] for x in calls], ["status", "create", "cleanup"])
            self.assertEqual(report["recovery_cleanup"], "PASS")


if __name__ == "__main__":
    unittest.main()

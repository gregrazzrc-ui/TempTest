"""No-database test of the one-shot live CRUD acceptance order and refusal gates."""
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import temp_db_513_bridge as gate
import test_temp513_end_to_end as smoke


class EndToEndGuardTests(unittest.TestCase):
    def environment(self, folder):
        return {"GITHUB_REPOSITORY": gate.REPO, "GITHUB_ACTOR": gate.OWNER,
                "GITHUB_REF": smoke.BRANCH, "GITHUB_EVENT_NAME": "push",
                "TEMPTEST_513_LIVE_WRITE_APPROVED": "YES_DB_513_ONLY",
                "FHQ_TEMP_DB_513_HOST": gate.HOST, "FHQ_TEMP_DB_513_USERNAME": gate.USERNAME,
                "FHQ_TEMP_DB_513_PASSWORD": "test-not-real",
                "RUNNER_TEMP": folder}

    def test_no_write_without_owner_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            env = self.environment(folder)
            env.pop("TEMPTEST_513_LIVE_WRITE_APPROVED")
            with patch.object(smoke.endpoint, "request_endpoint") as remote:
                result = smoke.main(env)
                self.assertEqual(result, 1)
                remote.assert_not_called()

    def test_full_sequence_and_successful_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            env = self.environment(folder)
            responses = [
                {"table_exists": False, "read_only": True},
                {"row_count": 3},
                {"row_count": 3},
                {"row_count": 3, "rows": [{"id": 2, "state": "UPDATED"}]},
                {"row_count": 3, "rows": [{"id": 2, "state": "UPDATED"}]},
                {"row_count": 2},
                {"row_count": 2, "rows": [{"id": 1}, {"id": 2}]},
                {"cleaned": True},
                {"table_exists": False},
            ]
            with patch.object(smoke.endpoint, "request_endpoint", side_effect=responses) as remote:
                result = smoke.main(env)
                self.assertEqual(result, 0)
                self.assertEqual([x.args[1] for x in remote.call_args_list],
                                 ["status","create","read","update","read",
                                  "delete","read","cleanup","status"])

    def test_existing_fixture_refuses_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            env = self.environment(folder)
            with patch.object(smoke.endpoint, "request_endpoint",
                              return_value={"table_exists": True, "read_only": True}) as remote:
                self.assertEqual(smoke.main(env), 1)
                remote.assert_called_once_with("test-not-real", "status")


if __name__ == "__main__":
    unittest.main()

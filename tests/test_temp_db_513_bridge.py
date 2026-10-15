"""Offline security boundary tests: no IONOS access, no secrets required."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import tempfile
import json
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bridge", ROOT / "scripts" / "temp_db_513_bridge.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def event(operation="status", user="gregrazzrc-ui", database="dbs16231513"):
    return {"action": "opened", "repository": {"full_name": "gregrazzrc-ui/TempTest"},
            "issue": {"number": 42, "state": "open", "user": {"login": user},
                      "title": "TEMPTEST-513: " + operation,
                      "body": f"TEMPTEST_513_V1\noperation={operation}\ndatabase={database}"}}


class BridgeBoundaryTests(unittest.TestCase):
    def test_all_exact_issue_commands(self):
        for op in mod.OPERATIONS:
            with self.subTest(operation=op):
                self.assertEqual(mod.issue_operation(event(op)), (42, op))

    def test_reject_non_owner(self):
        with self.assertRaisesRegex(mod.ProbeBlocked, "UNAUTHORIZED_AUTHOR"):
            mod.issue_operation(event(user="not-owner"))

    def test_reject_wrong_repo(self):
        e = event()
        e["repository"]["full_name"] = "another/other"
        with self.assertRaisesRegex(mod.ProbeBlocked, "WRONG_REPOSITORY"):
            mod.issue_operation(e)

    def test_reject_arbitrary_sql_and_extra_body(self):
        with self.assertRaisesRegex(mod.ProbeBlocked, "INVALID_COMMAND"):
            mod.issue_operation(event("DROP DATABASE"))
        e = event()
        e["issue"]["body"] += "\nother=payload"
        with self.assertRaisesRegex(mod.ProbeBlocked, "INVALID_COMMAND_BODY"):
            mod.issue_operation(e)

    def test_reject_wrong_database_name(self):
        with self.assertRaisesRegex(mod.ProbeBlocked, "INVALID_COMMAND_BODY"):
            mod.issue_operation(event(database="wrong"))

    def test_config_requires_exact_host_user_and_password(self):
        config = {"FHQ_TEMP_DB_513_HOST": mod.HOST,
                  "FHQ_TEMP_DB_513_USERNAME": mod.USERNAME,
                  "FHQ_TEMP_DB_513_PASSWORD": "fake-secret"}
        self.assertEqual(mod.read_credentials(config)["host"], mod.HOST)
        for key, bad in [("FHQ_TEMP_DB_513_HOST", "other.example.com"),
                         ("FHQ_TEMP_DB_513_USERNAME", "dbu-other"),
                         ("FHQ_TEMP_DB_513_PASSWORD", "")]:
            with self.subTest(secret=key):
                c = config.copy()
                c[key] = bad
                with self.assertRaises(mod.ProbeBlocked):
                    mod.read_credentials(c)

    def test_read_only_preflight_and_sanitized_output(self):
        with tempfile.TemporaryDirectory() as dest:
            env = {"GITHUB_REPOSITORY": mod.REPO,
                   "GITHUB_REF": "refs/heads/work/temptest-db513-chat-bridge-20261015",
                   "GITHUB_EVENT_NAME": "push", "GITHUB_ACTOR": mod.OWNER,
                   "FHQ_TEMP_DB_513_HOST": mod.HOST,
                   "FHQ_TEMP_DB_513_USERNAME": mod.USERNAME,
                   "FHQ_TEMP_DB_513_PASSWORD": "super-secret-dummy", "RUNNER_TEMP": dest}
            with patch.object(mod, "connect") as connect, patch.object(mod, "execute", return_value={"read_only": True}) as execute:
                result = mod.main(["--probe"], env)
            self.assertEqual(result, 0)
            execute.assert_called_once_with(connect.return_value, "status")
            report = (Path(dest) / "temptest-db513-result.json").read_text()
            self.assertNotIn("super-secret-dummy", report)
            self.assertEqual(json.loads(report)["status"], "PASS")

    def test_wrong_preflight_actor_rejected_without_connecting(self):
        with tempfile.TemporaryDirectory() as dest:
            env = {"GITHUB_REPOSITORY": mod.REPO, "GITHUB_REF": "refs/heads/main",
                   "GITHUB_EVENT_NAME": "push", "GITHUB_ACTOR": mod.OWNER,
                   "RUNNER_TEMP": dest}
            with patch.object(mod, "connect") as connect:
                self.assertEqual(mod.main(["--probe"], env), 1)
                connect.assert_not_called()

    def test_issue_parse_requires_main_and_opened_event(self):
        with tempfile.TemporaryDirectory() as dest:
            event_path = Path(dest) / "event.json"
            event_path.write_text(json.dumps(event("read")))
            env = {"GITHUB_REPOSITORY": mod.REPO, "GITHUB_REF": "refs/heads/main",
                   "GITHUB_EVENT_NAME": "issues", "GITHUB_EVENT_PATH": str(event_path),
                   "FHQ_TEMP_DB_513_HOST": mod.HOST,
                   "FHQ_TEMP_DB_513_USERNAME": mod.USERNAME,
                   "FHQ_TEMP_DB_513_PASSWORD": "dummy", "RUNNER_TEMP": dest}
            with patch.object(mod, "connect"), patch.object(mod, "execute", return_value={"rows": []}) as execute:
                self.assertEqual(mod.main(["--issue"], env), 0)
                self.assertEqual(execute.call_args.args[1], "read")


if __name__ == "__main__":
    unittest.main()

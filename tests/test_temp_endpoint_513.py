"""TempTest only: no-secrets offline tests for dedicated PHP CRUD bridge."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import temp_db_513_bridge as gate
import temp_endpoint_513 as endpoint


def sample(op):
    result = {"status": "PASS", "database": gate.DATABASE, "operation": op,
              "login_verified": True, "grant_account_differs": True}
    if op == "status":
        result.update({"read_only": True, "table_exists": False})
    elif op == "cleanup":
        result.update({"cleaned": True, "table_exists": False, "row_count": 0})
    else:
        rows = [
            {"id": 1, "label": "Alpha", "state": "CREATED"},
            {"id": 2, "label": "Beta", "state": "UPDATED" if op in ("update", "delete") else "CREATED"},
        ]
        if op != "delete":
            rows.append({"id": 3, "label": "Gamma", "state": "CREATED"})
        result.update({"table_exists": True, "row_count": len(rows), "rows": rows})
    return result


class EndpointBoundaryTests(unittest.TestCase):
    def test_each_fixed_operation_has_valid_sanitized_response(self):
        for op in gate.OPERATIONS:
            with self.subTest(op=op):
                r = endpoint.verify_response(sample(op), op)
                self.assertEqual(r["database"], gate.DATABASE)
                self.assertNotIn("password", r)

    def test_refuses_wrong_target_or_operation(self):
        result = sample("status")
        result["database"] = "different_database"
        with self.assertRaises(gate.ProbeBlocked):
            endpoint.verify_response(result, "status")
        result = sample("status")
        with self.assertRaises(gate.ProbeBlocked):
            endpoint.verify_response(result, "create")

    def test_refuses_wrong_row_data_and_unverified_cleanup(self):
        result = sample("create")
        result["rows"][0]["label"] = "not-Alpha"
        with self.assertRaises(gate.ProbeBlocked):
            endpoint.verify_response(result, "create")
        result = sample("cleanup")
        result["cleaned"] = False
        with self.assertRaises(gate.ProbeBlocked):
            endpoint.verify_response(result, "cleanup")

    def test_issue_owner_gate_precedes_network_request(self):
        with tempfile.TemporaryDirectory() as folder:
            event_path = Path(folder) / "event.json"
            event_path.write_text(json.dumps({
                "action": "opened", "repository": {"full_name": gate.REPO},
                "issue": {"number": 9, "state": "open",
                          "user": {"login": gate.OWNER},
                          "title": gate.PREFIX + "update",
                          "body": "TEMPTEST_513_V1\noperation=update\ndatabase="+gate.DATABASE}
            }), encoding="utf-8")
            env = {"GITHUB_REPOSITORY": gate.REPO, "GITHUB_REF": "refs/heads/main",
                   "GITHUB_EVENT_NAME": "issues", "GITHUB_EVENT_PATH": str(event_path),
                   "FHQ_TEMP_DB_513_HOST": gate.HOST,
                   "FHQ_TEMP_DB_513_USERNAME": gate.USERNAME,
                   "FHQ_TEMP_DB_513_PASSWORD": "fake-test-secret", "RUNNER_TEMP": folder}
            with patch.object(endpoint, "request_endpoint", return_value=endpoint.verify_response(sample("update"),"update")) as request:
                self.assertEqual(endpoint.main(["--issue"], env), 0)
                request.assert_called_once_with("fake-test-secret", "update")
            self.assertNotIn("fake-test-secret", (Path(folder) / "temptest-db513-result.json").read_text())
            data=json.loads(event_path.read_text())
            data["issue"]["user"]["login"]="not-owner"
            event_path.write_text(json.dumps(data), encoding="utf-8")
            with patch.object(endpoint, "request_endpoint") as request:
                self.assertNotEqual(endpoint.main(["--issue"], env), 0)
                request.assert_not_called()

    def test_read_only_probe_uses_only_status(self):
        env = {"GITHUB_REPOSITORY": gate.REPO, "GITHUB_ACTOR": gate.OWNER,
               "GITHUB_EVENT_NAME": "workflow_dispatch",
               "FHQ_TEMP_DB_513_HOST": gate.HOST,
               "FHQ_TEMP_DB_513_USERNAME": gate.USERNAME,
               "FHQ_TEMP_DB_513_PASSWORD": "dummy"}
        with tempfile.TemporaryDirectory() as folder:
            env["RUNNER_TEMP"] = folder
            with patch.object(endpoint, "request_endpoint", return_value=endpoint.verify_response(sample("status"),"status")) as request:
                self.assertEqual(endpoint.main(["--probe"], env), 0)
                request.assert_called_once_with("dummy", "status")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Once-approved TempTest acceptance of the disposable MariaDB PHP bridge.

Mode STATUS is read-only. Mode FULL tests the complete synthetic fixture
and removes it again. No arbitrary SQL or non-TempTest URLs are accepted.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import temp_db_513_bridge as gate
import temp_endpoint_513 as endpoint

REPO = "gregrazzrc-ui/TempTest"
BRANCH = "refs/heads/work/temptest-db513-chat-bridge-20261015"
TRIGGER = Path("deploy/temptest-db-acceptance-trigger.txt")
REPORT = Path("temp513-acceptance.json")
OPERATIONS = ("create", "read", "update", "read", "delete", "read", "cleanup", "status")


def main() -> int:
    report = {"status": "BLOCKED", "database": gate.DATABASE, "checks": []}
    password = None
    created_might_exist = False
    successfully_cleaned = False
    try:
        env = os.environ
        if (env.get("GITHUB_REPOSITORY") != REPO or
                env.get("GITHUB_REF") != BRANCH or
                env.get("GITHUB_ACTOR") != gate.OWNER or
                env.get("GITHUB_EVENT_NAME") != "push"):
            raise gate.ProbeBlocked("UNAUTHORIZED_ACCEPTANCE_CONTEXT")
        mode = TRIGGER.read_text(encoding="utf-8").strip()
        if mode not in ("STATUS", "FULL"):
            raise gate.ProbeBlocked("INVALID_ACCEPTANCE_MODE")
        report["mode"] = mode
        password = gate.read_credentials(env)["password"]

        status = endpoint.request_endpoint(password, "status")
        report["checks"].append({"operation": "status", "passed": True,
                                 "table_exists": status["table_exists"]})
        if mode == "STATUS":
            report["status"] = "PASS"
            return 0
        if status["table_exists"]:
            raise gate.ProbeBlocked("EXISTING_FIXTURE_REFUSED")
        for operation in OPERATIONS:
            if operation == "create":
                created_might_exist = True
            detail = endpoint.request_endpoint(password, operation)
            report["checks"].append({"operation": operation, "passed": True,
                                     "row_count": detail.get("row_count"),
                                     "table_exists": detail.get("table_exists")})
            if operation == "cleanup":
                successfully_cleaned = True
        if report["checks"][-1]["table_exists"]:
            raise gate.ProbeBlocked("FINAL_TABLE_STILL_EXISTS")
        report["status"] = "PASS"
        return 0
    except gate.ProbeBlocked as exc:
        report["reason"] = exc.code
        return 1
    except Exception:
        report["reason"] = "ACCEPTANCE_UNEXPECTED_ERROR"
        return 1
    finally:
        if created_might_exist and not successfully_cleaned and password:
            try:
                cleanup = endpoint.request_endpoint(password, "cleanup")
                report["recovery_cleanup"] = "PASS" if cleanup["cleaned"] else "FAILED"
            except Exception:
                report["recovery_cleanup"] = "FAILED_INSPECTION_REQUIRED"
        dest = Path(os.environ.get("RUNNER_TEMP") or ".") / REPORT
        dest.write_text(json.dumps(report, sort_keys=True, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())

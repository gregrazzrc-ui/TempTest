#!/usr/bin/env python3
"""One-shot authorised integration acceptance for disposable TempTest DB 513 only.

Designed to run on a pinned owner-authored branch push, not on PRs.
Checks endpoint status before writes, creates only one synthetic fixture,
and always tries fixture cleanup after successful creation.
"""
from __future__ import annotations

import json
import os
import sys

import temp_db_513_bridge as gate
import temp_endpoint_513 as endpoint

BRANCH = "refs/heads/work/temptest-db513-chat-bridge-20261015"


def require(cond: bool, reason: str):
    if not cond:
        raise gate.ProbeBlocked(reason)


def main(environ=None) -> int:
    env = os.environ if environ is None else environ
    report = {"database": gate.DATABASE, "test": "TEMPTEST_513_LIVE_CRUD",
              "status": "BLOCKED", "steps": [], "cleanup_verified": False}
    created = False
    try:
        require(env.get("GITHUB_REPOSITORY") == gate.REPO, "WRONG_REPOSITORY")
        require(env.get("GITHUB_ACTOR") == gate.OWNER, "WRONG_ACTOR")
        require(env.get("GITHUB_REF") == BRANCH, "WRONG_BRANCH")
        require(env.get("GITHUB_EVENT_NAME") == "push", "WRONG_EVENT")
        require(env.get("TEMPTEST_513_LIVE_WRITE_APPROVED") == "YES_DB_513_ONLY",
                "OWNER_APPROVAL_MISSING")
        password = gate.read_credentials(env)["password"]

        before = endpoint.request_endpoint(password, "status")
        report["steps"].append("status_before")
        require(before["table_exists"] is False, "PREEXISTING_FIXTURE_REFUSE")
        require(before["read_only"] is True, "INITIAL_STATUS_NOT_READ_ONLY")

        made = endpoint.request_endpoint(password, "create")
        created = True
        report["steps"].append("create")
        require(made["row_count"] == 3, "CREATE_WRONG_ROW_COUNT")

        first = endpoint.request_endpoint(password, "read")
        report["steps"].append("read_after_create")
        require(first["row_count"] == 3, "FIRST_READ_BAD")

        changed = endpoint.request_endpoint(password, "update")
        report["steps"].append("update")
        require(changed["row_count"] == 3, "UPDATE_WRONG_ROW_COUNT")
        require(any(x["id"] == 2 and x["state"] == "UPDATED" for x in changed["rows"]),
                "UPDATE_NOT_PERSISTED")

        second = endpoint.request_endpoint(password, "read")
        report["steps"].append("read_after_update")
        require(any(x["id"] == 2 and x["state"] == "UPDATED" for x in second["rows"]),
                "UPDATE_READBACK_FAILED")

        deleted = endpoint.request_endpoint(password, "delete")
        report["steps"].append("delete")
        require(deleted["row_count"] == 2, "DELETE_WRONG_ROW_COUNT")

        third = endpoint.request_endpoint(password, "read")
        report["steps"].append("read_after_delete")
        require(third["row_count"] == 2, "DELETE_READBACK_FAILED")
        require(tuple(x["id"] for x in third["rows"]) == (1, 2), "DELETE_WRONG_ROWS")

        endpoint.request_endpoint(password, "cleanup")
        report["steps"].append("cleanup")
        created = False

        after = endpoint.request_endpoint(password, "status")
        report["steps"].append("status_after_cleanup")
        require(after["table_exists"] is False, "FIXTURE_STILL_EXISTS")

        report["cleanup_verified"] = True
        report["status"] = "PASS"
        return_code = 0
    except gate.ProbeBlocked as err:
        report["reason"] = err.code
        return_code = 1
    except Exception:
        report["reason"] = "END_TO_END_TEST_FAILED"
        return_code = 1
    finally:
        if created:
            try:
                password = gate.read_credentials(env)["password"]
                endpoint.request_endpoint(password, "cleanup")
                after = endpoint.request_endpoint(password, "status")
                report["cleanup_verified"] = after["table_exists"] is False
            except Exception:
                report["cleanup_verified"] = False
            if report["cleanup_verified"]:
                report["steps"].append("failure_cleanup")
        gate.report_to_file(report, env)
    return return_code


if __name__ == "__main__":
    sys.exit(main())

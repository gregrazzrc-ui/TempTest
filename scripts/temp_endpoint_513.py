#!/usr/bin/env python3
"""TempTest GitHub Actions -> isolated HTTPS PHP PDO endpoint; existing DB secret only."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import ssl
import sys
import urllib.error
import urllib.request

import temp_db_513_bridge as gate

URL = "https://temp.fisherhq.co.uk/temp513-bridge.php"
MAX_RESPONSE_BYTES = 8192


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def verify_response(result: object, operation: str) -> dict:
    if not isinstance(result, dict) or result.get("status") != "PASS":
        raise gate.ProbeBlocked("ENDPOINT_NO_PASS")
    if (result.get("database") != gate.DATABASE or
            result.get("operation") != operation or
            result.get("login_verified") is not True or
            type(result.get("grant_account_differs")) is not bool):
        raise gate.ProbeBlocked("ENDPOINT_IDENTITY_MISMATCH")
    summary = {"operation": operation, "database": gate.DATABASE,
               "login_verified": True,
               "grant_account_differs": result["grant_account_differs"]}
    if operation == "status":
        if result.get("read_only") is not True or type(result.get("table_exists")) is not bool:
            raise gate.ProbeBlocked("ENDPOINT_INVALID_STATUS")
        summary["read_only"] = True
        summary["table_exists"] = result["table_exists"]
        return summary
    if operation == "cleanup":
        if (result.get("cleaned") is not True or
                result.get("table_exists") is not False or result.get("row_count") != 0):
            raise gate.ProbeBlocked("ENDPOINT_CLEANUP_UNVERIFIED")
        summary.update({"cleaned": True, "row_count": 0})
        return summary
    rows = result.get("rows")
    if not isinstance(rows, list) or result.get("table_exists") is not True:
        raise gate.ProbeBlocked("ENDPOINT_INVALID_ROWS")
    expected = {"create": (1, 2, 3), "update": (1, 2, 3),
                "delete": (1, 2), "read": (1, 2, 3)}
    if operation == "read":
        # Read is valid after create, update or delete.
        allowed = ((1, 2, 3), (1, 2))
    else:
        allowed = (expected.get(operation),)
    ids = tuple(r.get("id") for r in rows if isinstance(r, dict))
    if ids not in allowed or result.get("row_count") != len(rows):
        raise gate.ProbeBlocked("ENDPOINT_UNEXPECTED_ROW_COUNT")
    for r in rows:
        if type(r.get("id")) is not int or r.get("label") not in ("Alpha", "Beta", "Gamma"):
            raise gate.ProbeBlocked("ENDPOINT_UNEXPECTED_FIXTURE")
        if r["label"] != ("Alpha", "Beta", "Gamma")[r["id"] - 1]:
            raise gate.ProbeBlocked("ENDPOINT_UNEXPECTED_FIXTURE")
        if r.get("state") not in ("CREATED", "UPDATED"):
            raise gate.ProbeBlocked("ENDPOINT_UNEXPECTED_FIXTURE")
    summary.update({"row_count": len(rows), "rows": rows})
    return summary


def request_endpoint(password: str, operation: str) -> dict:
    if operation not in gate.OPERATIONS:
        raise gate.ProbeBlocked("INVALID_COMMAND")
    if not password:
        raise gate.ProbeBlocked("PASSWORD_SECRET_MISSING")
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        NoRedirect())
    body = json.dumps({"operation": operation, "password": password},
                      separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        URL, data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "TempTest-513-Bridge/1"})
    try:
        with opener.open(request, timeout=15) as response:
            if response.geturl() != URL or response.status != 200:
                raise gate.ProbeBlocked("ENDPOINT_BAD_RESPONSE")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise gate.ProbeBlocked("ENDPOINT_RESPONSE_TOO_LARGE")
        result = json.loads(raw.decode("utf-8"))
    except gate.ProbeBlocked:
        raise
    except Exception:
        # Never echo HTTP error bodies, URLs containing credentials, stack traces, etc.
        raise gate.ProbeBlocked("ENDPOINT_HTTPS_UNREACHABLE_OR_REFUSED") from None
    return verify_response(result, operation)


def main(argv=None, environ=None) -> int:
    parser = argparse.ArgumentParser()
    opts = parser.add_mutually_exclusive_group(required=True)
    opts.add_argument("--issue", action="store_true")
    opts.add_argument("--probe", action="store_true")
    args = parser.parse_args(argv)
    e = dict(os.environ if environ is None else environ)
    report = {"status": "BLOCKED", "database": gate.DATABASE, "operation": "unverified"}
    try:
        if e.get("GITHUB_REPOSITORY") != gate.REPO:
            raise gate.ProbeBlocked("WRONG_REPOSITORY")
        if args.probe:
            if e.get("GITHUB_ACTOR") != gate.OWNER or (
                    e.get("GITHUB_EVENT_NAME") != "workflow_dispatch"):
                raise gate.ProbeBlocked("UNAUTHORIZED_PROBE")
            operation = "status"
        else:
            if (e.get("GITHUB_EVENT_NAME") != "issues" or
                    e.get("GITHUB_REF") != "refs/heads/main"):
                raise gate.ProbeBlocked("UNAUTHORIZED_ISSUE_CONTEXT")
            path = e.get("GITHUB_EVENT_PATH")
            if not path:
                raise gate.ProbeBlocked("MISSING_ISSUE_EVENT")
            number, operation = gate.issue_operation(
                json.loads(Path(path).read_text(encoding="utf-8")))
            report["issue_number"] = number
        report["operation"] = operation
        password = gate.read_credentials(e)["password"]
        report.update(request_endpoint(password, operation))
        report["status"] = "PASS"
        code = 0
    except gate.ProbeBlocked as error:
        report["reason"] = error.code
        code = 1
    except Exception:
        report["reason"] = "ENDPOINT_UNEXPECTED_ERROR"
        code = 1
    gate.report_to_file(report, e)
    return code


if __name__ == "__main__":
    sys.exit(main())

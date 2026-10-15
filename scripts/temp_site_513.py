#!/usr/bin/env python3
"""TempTest only: verify existing IONOS PHP form over authenticated HTTPS.

Only owner-opened GitHub Issues on main can request the site's built-in
all-in-one CRUD test. Feature-branch preflight is connection-only.
"""
from __future__ import annotations
import argparse
import html.parser
import http.cookiejar
import json
import os
from pathlib import Path
import ssl
import sys
import urllib.parse
import urllib.request

import temp_db_513_bridge as bridge

URL = "https://temp.fisherhq.co.uk/"
MAX_BYTES = 262144
SITE_COMMANDS = {"status": "connect", "full-test": "test"}
EXPECTED_CHECKS = ("Connection", "Database identity", "Authenticated account",
                   "Create table", "Insert and read", "Update", "Delete",
                   "Schema change", "Filter and sort", "Transaction rollback",
                   "Transaction commit", "Migration", "Migration reversal", "Cleanup")


class PageParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.csrf = None
        self.rows = []
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("name") == "csrf" and attrs.get("type") == "hidden":
            self.csrf = attrs.get("value")
        elif tag == "tr":
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = ""

    def handle_data(self, data):
        if self._cell is not None:
            self._cell += data

    def handle_endtag(self, tag):
        if tag == "td" and self._row is not None and self._cell is not None:
            self._row.append(self._cell.strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None
            self._cell = None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def verify_page(html: str, operation: str) -> dict:
    parsed = PageParser()
    parsed.feed(html)
    rows = {r[0]: r[1:] for r in parsed.rows if len(r) == 3}
    expected = EXPECTED_CHECKS if operation == "full-test" else EXPECTED_CHECKS[:3]
    if any(name not in rows or rows[name][0] != "PASS" for name in expected):
        raise bridge.ProbeBlocked("SITE_TEST_INCOMPLETE_OR_FAILED")
    if not rows["Database identity"][1].startswith(bridge.DATABASE + " /"):
        raise bridge.ProbeBlocked("SITE_DATABASE_MISMATCH")
    if not rows["Authenticated account"][1].startswith(bridge.USERNAME + "@"):
        raise bridge.ProbeBlocked("SITE_ACCOUNT_MISMATCH")
    if operation == "full-test" and rows["Cleanup"][1] != "Test table and all its records removed.":
        raise bridge.ProbeBlocked("SITE_CLEANUP_UNVERIFIED")
    return {"route": "TempTest HTTPS PHP form", "read_only": operation == "status",
            "verified_checks": len(expected), "cleanup_verified": operation == "full-test"}


def site_request(password: str, operation: str) -> dict:
    if operation not in SITE_COMMANDS:
        raise bridge.ProbeBlocked("SITE_INVALID_OPERATION")
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        NoRedirect())
    def read_response(request):
        try:
            with opener.open(request, timeout=15) as response:
                if response.geturl() != URL or response.status != 200:
                    raise bridge.ProbeBlocked("SITE_UNEXPECTED_RESPONSE")
                content = response.read(MAX_BYTES + 1)
                if len(content) > MAX_BYTES:
                    raise bridge.ProbeBlocked("SITE_RESPONSE_TOO_LARGE")
                return content.decode("utf-8")
        except bridge.ProbeBlocked:
            raise
        except Exception:
            raise bridge.ProbeBlocked("SITE_HTTPS_REQUEST_FAILED") from None
    html = read_response(urllib.request.Request(URL, headers={"User-Agent": "TempTest513Probe/1"}))
    parsed = PageParser()
    parsed.feed(html)
    if not parsed.csrf or len(parsed.csrf) != 64 or not all(c in "0123456789abcdef" for c in parsed.csrf):
        raise bridge.ProbeBlocked("SITE_CSRF_UNAVAILABLE")
    payload = urllib.parse.urlencode({"csrf": parsed.csrf, "password": password,
                                      "action": SITE_COMMANDS[operation]}).encode("utf-8")
    html = read_response(urllib.request.Request(URL, data=payload,
                        headers={"Content-Type": "application/x-www-form-urlencoded",
                                 "User-Agent": "TempTest513Probe/1"}))
    return verify_page(html, operation)


def issue_command(event: object) -> tuple[int, str]:
    if not isinstance(event, dict) or event.get("action") != "opened" or (event.get("repository") or {}).get("full_name") != bridge.REPO:
        raise bridge.ProbeBlocked("SITE_UNAUTHORIZED_EVENT")
    issue = event.get("issue")
    if not isinstance(issue, dict) or (issue.get("user") or {}).get("login") != bridge.OWNER:
        raise bridge.ProbeBlocked("SITE_UNAUTHORIZED_AUTHOR")
    operation = issue.get("title", "")
    if not isinstance(operation, str) or not operation.startswith(bridge.PREFIX):
        raise bridge.ProbeBlocked("SITE_INVALID_COMMAND")
    operation = operation[len(bridge.PREFIX):]
    if operation not in SITE_COMMANDS or issue.get("body", "").strip() != f"TEMPTEST_513_V1\noperation={operation}\ndatabase={bridge.DATABASE}":
        raise bridge.ProbeBlocked("SITE_INVALID_COMMAND")
    number = issue.get("number")
    if type(number) is not int or number < 1:
        raise bridge.ProbeBlocked("SITE_INVALID_ISSUE")
    return number, operation


def main(argv=None, environ=None):
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--probe", action="store_true")
    group.add_argument("--issue", action="store_true")
    args = parser.parse_args(argv)
    e = dict(os.environ if environ is None else environ)
    report = {"status": "BLOCKED", "database": bridge.DATABASE,
              "operation": "status" if args.probe else "unverified"}
    try:
        if e.get("GITHUB_REPOSITORY") != bridge.REPO:
            raise bridge.ProbeBlocked("SITE_WRONG_REPOSITORY")
        if args.probe:
            if (e.get("GITHUB_EVENT_NAME") != "push" or
                e.get("GITHUB_ACTOR") != bridge.OWNER or
                e.get("GITHUB_REF") != "refs/heads/work/temptest-db513-chat-bridge-20261015"):
                raise bridge.ProbeBlocked("SITE_UNAUTHORIZED_PREFLIGHT")
            operation = "status"
        else:
            if e.get("GITHUB_EVENT_NAME") != "issues" or e.get("GITHUB_REF") != "refs/heads/main":
                raise bridge.ProbeBlocked("SITE_UNAUTHORIZED_ISSUE_CONTEXT")
            path = e.get("GITHUB_EVENT_PATH")
            if not path:
                raise bridge.ProbeBlocked("SITE_MISSING_EVENT")
            issue_number, operation = issue_command(json.loads(Path(path).read_text(encoding="utf-8")))
            report["issue_number"] = issue_number
        report["operation"] = operation
        password = bridge.read_credentials(e)["password"]
        report.update(site_request(password, operation))
        report["status"] = "PASS"
        code = 0
    except bridge.ProbeBlocked as error:
        report["reason"] = error.code
        code = 1
    except Exception:
        report["reason"] = "SITE_TEST_ERROR"
        code = 1
    bridge.report_to_file(report, e)
    return code


if __name__ == "__main__":
    sys.exit(main())

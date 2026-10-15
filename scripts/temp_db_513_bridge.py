#!/usr/bin/env python3
"""Dedicated TempTest GitHub Actions bridge for one disposable MariaDB fixture.

Trusted, fixed SQL only. No database connection during imports or unit tests.
A --probe run is strictly read-only. Issue-triggered operations require the
repository owner's exactly formatted issue, as well as GitHub-side owner gates.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import ssl
import sys

REPO = "gregrazzrc-ui/TempTest"
OWNER = "gregrazzrc-ui"
DATABASE = "dbs16231513"
HOST = "db5021656421.hosting-data.io"
USERNAME = "dbu5597618"
TABLE = "temptest_chat_probe_513_v1"
MARKER = "TEMPTEST_513_FIXTURE_V1"
PREFIX = "TEMPTEST-513: "
OPERATIONS = frozenset(("status", "create", "read", "update", "delete", "cleanup"))
FIXTURE = ((1, "Alpha", "CREATED", MARKER),
           (2, "Beta", "CREATED", MARKER),
           (3, "Gamma", "CREATED", MARKER))
COLUMNS = (("id", "tinyint"), ("label", "varchar"),
           ("state", "varchar"), ("marker", "varchar"))


class ProbeBlocked(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def issue_operation(event: object) -> tuple[int, str]:
    if not isinstance(event, dict) or event.get("action") != "opened":
        raise ProbeBlocked("INVALID_EVENT")
    if (event.get("repository") or {}).get("full_name") != REPO:
        raise ProbeBlocked("WRONG_REPOSITORY")
    issue = event.get("issue")
    if not isinstance(issue, dict) or (issue.get("user") or {}).get("login") != OWNER:
        raise ProbeBlocked("UNAUTHORIZED_AUTHOR")
    if issue.get("state") != "open" or not isinstance(issue.get("title"), str):
        raise ProbeBlocked("INVALID_ISSUE")
    title = issue["title"]
    if not title.startswith(PREFIX):
        raise ProbeBlocked("INVALID_COMMAND")
    operation = title[len(PREFIX):]
    if operation not in OPERATIONS:
        raise ProbeBlocked("INVALID_COMMAND")
    exact_body = f"TEMPTEST_513_V1\noperation={operation}\ndatabase={DATABASE}"
    if not isinstance(issue.get("body"), str) or issue["body"].strip() != exact_body:
        raise ProbeBlocked("INVALID_COMMAND_BODY")
    number = issue.get("number")
    if type(number) is not int or number < 1:
        raise ProbeBlocked("INVALID_ISSUE")
    return number, operation


def read_credentials(environ: dict[str, str]) -> dict[str, str]:
    host = environ.get("FHQ_TEMP_DB_513_HOST", "").strip()
    user = environ.get("FHQ_TEMP_DB_513_USERNAME", "").strip()
    password = environ.get("FHQ_TEMP_DB_513_PASSWORD", "")
    if host != HOST:
        raise ProbeBlocked("HOST_IDENTITY_MISMATCH")
    if user != USERNAME:
        raise ProbeBlocked("USERNAME_IDENTITY_MISMATCH")
    if not password:
        raise ProbeBlocked("PASSWORD_SECRET_MISSING")
    return {"host": host, "user": user, "password": password}


def connect(config: dict[str, str]):
    # External runner may not reach the IONOS MySQL hosting network.
    # Never downgrade TLS or fall back to other DB accounts.
    import pymysql
    ctx = ssl.create_default_context()
    try:
        conn = pymysql.connect(host=config["host"], user=config["user"],
                               password=config["password"], database=DATABASE,
                               port=3306, connect_timeout=8, read_timeout=8,
                               write_timeout=8, charset="utf8mb4", autocommit=True,
                               ssl=ctx)
    except Exception:
        raise ProbeBlocked("SECURE_DB_CONNECTION_FAILED") from None
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DATABASE(), CURRENT_USER(), VERSION()")
            row = cur.fetchone()
        if not row or row[0] != DATABASE:
            raise ProbeBlocked("DATABASE_IDENTITY_MISMATCH")
        if not isinstance(row[1], str) or not row[1].startswith(USERNAME + "@"):
            raise ProbeBlocked("ACCOUNT_IDENTITY_MISMATCH")
        if not isinstance(row[2], str) or "mariadb" not in row[2].lower():
            raise ProbeBlocked("ENGINE_IDENTITY_MISMATCH")
    except ProbeBlocked:
        conn.close()
        raise
    except Exception:
        conn.close()
        raise ProbeBlocked("IDENTITY_QUERY_FAILED") from None
    return conn


def table_exists(cur) -> bool:
    cur.execute("SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema=%s AND table_name=%s", (DATABASE, TABLE))
    return int(cur.fetchone()[0]) == 1


def fixture_rows(cur) -> list[tuple]:
    if not table_exists(cur):
        raise ProbeBlocked("FIXTURE_NOT_CREATED")
    cur.execute("SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position",
                (DATABASE, TABLE))
    columns = tuple((str(a), str(b)) for a, b in cur.fetchall())
    if columns != COLUMNS:
        raise ProbeBlocked("FIXTURE_SCHEMA_MISMATCH")
    cur.execute("SELECT id, label, state, marker FROM " + TABLE + " ORDER BY id")
    rows = list(cur.fetchall())
    if (len(rows) > 3 or
        any((type(r[0]) is not int or r[0] not in (1, 2, 3) or
             r[1] != FIXTURE[r[0]-1][1] or r[3] != MARKER or
             r[2] not in ("CREATED", "UPDATED")) for r in rows)):
        raise ProbeBlocked("FIXTURE_CONTENT_MISMATCH")
    return rows


def execute(conn, operation: str) -> dict:
    if operation not in OPERATIONS:
        raise ProbeBlocked("INVALID_COMMAND")
    with conn.cursor() as cur:
        if operation == "status":
            return {"table_exists": table_exists(cur), "read_only": True}
        if operation == "create":
            if table_exists(cur):
                raise ProbeBlocked("FIXTURE_ALREADY_EXISTS")
            cur.execute("CREATE TABLE " + TABLE + " ("
                        "id TINYINT UNSIGNED NOT NULL PRIMARY KEY, "
                        "label VARCHAR(30) NOT NULL, state VARCHAR(20) NOT NULL, "
                        "marker VARCHAR(40) NOT NULL) ENGINE=InnoDB")
            cur.executemany("INSERT INTO " + TABLE + " (id,label,state,marker) "
                            "VALUES (%s,%s,%s,%s)", FIXTURE)
        elif operation == "read":
            pass
        elif operation == "update":
            rows = fixture_rows(cur)
            if not any(r[0] == 2 and r[2] == "CREATED" for r in rows):
                raise ProbeBlocked("EXPECTED_ROW_MISSING")
            cur.execute("UPDATE " + TABLE + " SET state=%s "
                        "WHERE id=%s AND label=%s AND state=%s AND marker=%s",
                        ("UPDATED", 2, "Beta", "CREATED", MARKER))
            if cur.rowcount != 1:
                raise ProbeBlocked("EXPECTED_ROW_MISSING")
        elif operation == "delete":
            rows = fixture_rows(cur)
            if not any(r[0] == 3 and r[2] == "CREATED" for r in rows):
                raise ProbeBlocked("EXPECTED_ROW_MISSING")
            cur.execute("DELETE FROM " + TABLE + " WHERE id=%s AND label=%s AND "
                        "state=%s AND marker=%s", (3, "Gamma", "CREATED", MARKER))
            if cur.rowcount != 1:
                raise ProbeBlocked("EXPECTED_ROW_MISSING")
        elif operation == "cleanup":
            fixture_rows(cur)
            cur.execute("DROP TABLE " + TABLE)
            return {"table_exists": False, "rows": [], "cleaned": True}
        rows = fixture_rows(cur)
        return {"table_exists": True,
                "rows": [{"id": r[0], "label": r[1], "state": r[2]} for r in rows],
                "row_count": len(rows)}


def report_to_file(report: dict, environ: dict[str, str]) -> None:
    folder = Path(environ.get("RUNNER_TEMP") or ".")
    folder.mkdir(exist_ok=True, parents=True)
    (folder / "temptest-db513-result.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


def main(argv: list[str] | None = None, environ: dict[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--probe", action="store_true", help="read-only connection check")
    group.add_argument("--issue", action="store_true", help="owner issue command")
    args = parser.parse_args(argv)
    e = dict(os.environ if environ is None else environ)
    report = {"status": "BLOCKED", "database": DATABASE,
              "operation": "status" if args.probe else "unverified"}
    try:
        if e.get("GITHUB_REPOSITORY") != REPO:
            raise ProbeBlocked("WRONG_REPOSITORY")
        if args.probe:
            if (e.get("GITHUB_REF") !=
                    "refs/heads/work/temptest-db513-chat-bridge-20261015" or
                    e.get("GITHUB_EVENT_NAME") != "push" or
                    e.get("GITHUB_ACTOR") != OWNER):
                raise ProbeBlocked("UNAUTHORIZED_PREFLIGHT")
            operation = "status"
        else:
            if (e.get("GITHUB_EVENT_NAME") != "issues" or
                    e.get("GITHUB_REF") != "refs/heads/main"):
                raise ProbeBlocked("UNAUTHORIZED_ISSUE_CONTEXT")
            event_path = e.get("GITHUB_EVENT_PATH")
            if not event_path:
                raise ProbeBlocked("MISSING_ISSUE_EVENT")
            event = json.loads(Path(event_path).read_text(encoding="utf-8"))
            issue_number, operation = issue_operation(event)
            report["issue_number"] = issue_number
        report["operation"] = operation
        credentials = read_credentials(e)
        conn = connect(credentials)
        try:
            details = execute(conn, operation)
        finally:
            conn.close()
        report.update(details)
        report["status"] = "PASS"
        code = 0
    except ProbeBlocked as exc:
        report["reason"] = exc.code
        code = 1
    except Exception:
        report["reason"] = "UNEXPECTED_TEST_FAILURE"
        code = 1
    report_to_file(report, e)
    return code


if __name__ == "__main__":
    sys.exit(main())

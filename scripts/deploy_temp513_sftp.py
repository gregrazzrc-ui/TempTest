#!/usr/bin/env python3
"""Deploy only the TempTest PHP bridge into a dedicated IONOS SFTP home.

Must be a newly created SFTP account whose home directory is public-temptest.
Requires a separately verified, pinned SSH host public key in deploy/ionos_sftp_known_hosts.
No Fisher HQ credentials, paths, deployments or other files are used.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

REPO = "gregrazzrc-ui/TempTest"
BRANCH = "refs/heads/work/temptest-db513-chat-bridge-20261015"
SOURCE = Path("deploy/temp513-bridge.php")
KNOWN_HOSTS = Path("deploy/ionos_sftp_known_hosts")
DEST = "temp513-bridge.php"
MAX_SOURCE = 25000
MARKERS = (b"TempTest", b"dbs16231513", b"ISOLATED DATABASE LAB")


class Refuse(Exception):
    pass


def verify_local(env: dict[str, str], base: Path) -> tuple[str, str, str, bytes]:
    if env.get("GITHUB_REPOSITORY") != REPO or env.get("GITHUB_REF") != BRANCH:
        raise Refuse("WRONG_REPOSITORY_OR_BRANCH")
    if env.get("GITHUB_EVENT_NAME") != "push" or env.get("GITHUB_ACTOR") != "gregrazzrc-ui":
        raise Refuse("UNAUTHORIZED_TRIGGER")
    if env.get("TEMPTEST_SFTP_UPLOAD_APPROVED") != "YES_ONLY_PUBLIC_TEMPTEST":
        raise Refuse("OWNER_APPROVAL_MISSING")
    host = env.get("FHQ_TEMP_SFTP_HOST", "").strip()
    username = env.get("FHQ_TEMP_SFTP_USERNAME", "").strip()
    password = env.get("FHQ_TEMP_SFTP_PASSWORD", "")
    if not host or not username or not password:
        raise Refuse("SFTP_SECRETS_MISSING")
    if any(c.isspace() or c in "/\\@:" for c in host) or len(host) > 253:
        raise Refuse("INVALID_SFTP_HOST")
    if any(c.isspace() for c in username) or len(username) > 128:
        raise Refuse("INVALID_SFTP_USERNAME")
    source = base / SOURCE
    known = base / KNOWN_HOSTS
    if not source.is_file() or not known.is_file():
        raise Refuse("SOURCE_OR_PINNED_HOST_KEY_MISSING")
    data = source.read_bytes()
    if not data.startswith(b"<?php") or len(data) > MAX_SOURCE:
        raise Refuse("UNEXPECTED_SOURCE_FILE")
    if b"dbs16231513" not in data or b"db5021656421.hosting-data.io" not in data:
        raise Refuse("WRONG_DATABASE_SOURCE")
    known_lines = [x.strip() for x in known.read_text(encoding="utf-8").splitlines() if x.strip() and not x.startswith("#")]
    if len(known_lines) != 1 or known_lines[0].split(" ")[0] != host:
        raise Refuse("HOST_KEY_NOT_VERIFIED")
    return host, username, password, data


def verify_sftp_home(sftp) -> None:
    # A dedicated chroot to public-temptest must already contain the original PHP page.
    # Refuse if a broad webspace/root account can access parent directories.
    try:
        with sftp.open("index.php", "rb") as src:
            data = src.read(250000)
        if b"TempTest" not in data or b"dbs16231513" not in data or b"Database lab" not in data:
            raise Refuse("WRONG_SFTP_HOME")
        if "temp513-bridge.php" in sftp.listdir("."):
            raise Refuse("REMOTE_TARGET_ALREADY_PRESENT_REVIEW_MANUALLY")
    except Refuse:
        raise
    except Exception:
        raise Refuse("SFTP_HOME_CHECK_FAILED") from None


def deploy(host: str, username: str, password: str, data: bytes, base: Path) -> dict:
    import paramiko
    client = paramiko.SSHClient()
    client.load_host_keys(str(base / KNOWN_HOSTS))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        client.connect(hostname=host, port=22, username=username, password=password,
                       look_for_keys=False, allow_agent=False,
                       timeout=10, auth_timeout=10, banner_timeout=10)
        sftp = client.open_sftp()
        try:
            verify_sftp_home(sftp)
            candidate = "temp513-bridge.php.uploading"
            if candidate in sftp.listdir("."):
                raise Refuse("TEMP_FILE_ALREADY_EXISTS")
            try:
                with sftp.open(candidate, "wb") as target:
                    target.write(data)
                    target.flush()
                with sftp.open(candidate, "rb") as result:
                    actual = result.read(MAX_SOURCE + 1)
                if actual != data:
                    raise Refuse("UPLOAD_CONTENT_MISMATCH")
                if DEST in sftp.listdir("."):
                    raise Refuse("TARGET_APPEARED_DURING_UPLOAD")
                sftp.rename(candidate, DEST)
                return {"status": "PASS", "target": "public-temptest/temp513-bridge.php",
                        "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                        "no_database_writes": True}
            finally:
                try:
                    if candidate in sftp.listdir("."):
                        sftp.remove(candidate)
                except Exception:
                    pass
        finally:
            sftp.close()
    except Refuse:
        raise
    except Exception:
        raise Refuse("SFTP_CONNECTION_OR_UPLOAD_FAILED") from None
    finally:
        client.close()


def main() -> int:
    try:
        host, username, password, data = verify_local(os.environ, Path.cwd())
        response = deploy(host, username, password, data, Path.cwd())
        print(json.dumps(response, sort_keys=True))
        return 0
    except Refuse as error:
        print(json.dumps({"status": "BLOCKED", "reason": str(error)}, sort_keys=True))
        return 1
    except Exception:
        print('{"status":"BLOCKED","reason":"DEPLOYMENT_FAILED"}')
        return 1


if __name__ == "__main__":
    sys.exit(main())

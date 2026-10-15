#!/usr/bin/env python3
"""Read-only TempTest SFTP inspection; no paths/credentials/file content printed."""
import json
import os
from pathlib import Path
import sys

HOST = "access-5021528741.webspace-host.com"
USER = "su78426"
REPO = "gregrazzrc-ui/TempTest"


def checked_index(sftp, path):
    try:
        with sftp.open(path, "rb") as f:
            body = f.read(250000)
        return (body.startswith(b"<?php") and b"dbs16231513" in body and
                b"TempTest" in body and b"Database lab" in body)
    except (OSError, IOError):
        return False


def main():
    if os.environ.get("GITHUB_REPOSITORY") != REPO:
        print('{"status":"BLOCKED","reason":"WRONG_REPOSITORY"}')
        return 1
    if os.environ.get("GITHUB_ACTOR") != "gregrazzrc-ui" or os.environ.get("GITHUB_EVENT_NAME") != "push":
        print('{"status":"BLOCKED","reason":"WRONG_EVENT"}')
        return 1
    if os.environ.get("FHQ_TEMP_SFTP_USERNAME", "").strip() != USER:
        print('{"status":"BLOCKED","reason":"SFTP_USERNAME_MISMATCH"}')
        return 1
    secret = os.environ.get("FHQ_TEMP_SFTP_PASSWORD", "")
    if not secret:
        print('{"status":"BLOCKED","reason":"SFTP_PASSWORD_MISSING"}')
        return 1
    try:
        import paramiko
        c = paramiko.SSHClient()
        c.load_host_keys(str(Path("deploy/ionos_sftp_known_hosts")))
        c.set_missing_host_key_policy(paramiko.RejectPolicy())
        try:
            c.connect(hostname=HOST, port=22, username=USER, password=secret,
                      look_for_keys=False, allow_agent=False, timeout=15, auth_timeout=15,
                      banner_timeout=15)
            with c.open_sftp() as sftp:
                root_valid = checked_index(sftp, "index.php")
                subfolder_valid = checked_index(sftp, "public-temptest/index.php")
                home = sftp.normalize(".")
                print(json.dumps({"status":"PASS", "sftp_login":"PASS",
                                  "root_is_temp_site":root_valid,
                                  "subfolder_is_temp_site":subfolder_valid,
                                  "home_is_chroot_root":home == "/",
                                  "destination_ambiguous":root_valid and subfolder_valid}))
        finally:
            c.close()
        return 0
    except Exception:
        print('{"status":"BLOCKED","reason":"SFTP_CONNECT_OR_INSPECT_FAILED"}')
        return 1


if __name__ == "__main__":
    sys.exit(main())

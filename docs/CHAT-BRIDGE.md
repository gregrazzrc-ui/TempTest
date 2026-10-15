# TempTest 513 — GitHub issue to isolated IONOS MariaDB CRUD

## Scope and status

This experiment is **only** in `gregrazzrc-ui/TempTest`. Nothing here belongs in Fisher HQ. The existing `index.php` remains unchanged. The work is in draft PR #1; the new PHP endpoint **has not been uploaded** to IONOS, and no database writes have been performed by the new bridge.

## Existing credentials (no new password or token)

All three are **GitHub Actions repository secrets under TempTest**:

- `FHQ_TEMP_DB_513_HOST` = `db5021656421.hosting-data.io`
- `FHQ_TEMP_DB_513_USERNAME` = `dbu5597618`
- `FHQ_TEMP_DB_513_PASSWORD` = the IONOS MariaDB password

Database `dbs16231513`, port `3306`, MariaDB 11.8. The GitHub workflow supplies the database password over HTTPS at runtime, then PHP uses PDO to authenticate to IONOS. **Never paste the password in Issues, commit it to PHP, or create another database credential.** No additional bridge token is required for this disposable lab. Access to the public endpoint is authenticated by successfully connecting with the existing database password; for production systems use stronger separately managed endpoint authorization.

## Architecture

1. ChatGPT creates an exact allowlisted **TempTest** Issue on the owner's behalf.
2. A GitHub Actions workflow checks author, repository, exact issue title and three-line body.
3. Actions reads the three existing TempTest secrets and sends a small JSON POST over verified HTTPS to `https://temp.fisherhq.co.uk/temp513-bridge.php`.
4. The standalone PHP file uses `new PDO(...)` with the **fixed** temporary host, database, username and password provided by GitHub. It validates `DATABASE()`, `USER()` and MariaDB version, without demanding that `CURRENT_USER()` match the login (MariaDB privilege accounts can differ).
5. PHP performs **only** the fixed synthetic table operation; it returns a small sanitized JSON result.
6. Actions validates the returned database, operation and row shape, prints a sanitized result, and stores a seven-day artifact for ChatGPT to read.

**No arbitrary SQL, table names, customer data, production databases, remote SSH or production deployments are involved.**

## Six test commands

GitHub Issue title must be one of `TEMPTEST-513: status`, `TEMPTEST-513: create`, `TEMPTEST-513: read`, `TEMPTEST-513: update`, `TEMPTEST-513: delete`, `TEMPTEST-513: cleanup`. Its body must be exactly (change the operation to match the title):

```text
TEMPTEST_513_V1
operation=status
database=dbs16231513
```

- `status`: read-only check whether the synthetic table exists.
- `create`: create `temptest_chat_probe_513_v1` with exactly three fake records (Alpha, Beta, Gamma); refuse an existing table.
- `read`: return the fixture rows.
- `update`: change Beta from CREATED to UPDATED.
- `delete`: delete Gamma.
- `cleanup`: drop only the table after verifying its expected schema and marker values.

Each Issue is independently authorized. GitHub workflow serializes operations, so the intended test sequence is status → create → read → update → read → delete → read → cleanup → status.

## Automated IONOS SFTP upload (no manual copying)

The SFTP upload is **staged but not triggered**. In IONOS create a **new SFTP account whose home directory is exclusively `public-temptest`**; it must not have access to Fisher HQ web folders.

Create these **three new GitHub Actions repository secrets in `gregrazzrc-ui/TempTest`**:

- `TEMPTEST_IONOS_SFTP_HOST` = IONOS SFTP hostname (not the MariaDB hostname).
- `TEMPTEST_IONOS_SFTP_USERNAME` = new dedicated IONOS SFTP login.
- `TEMPTEST_IONOS_SFTP_PASSWORD` = new dedicated IONOS SFTP password.

These are **file upload credentials**, distinct from the three existing `FHQ_TEMP_DB_513_*` database secrets. Do not paste the SFTP password into ChatGPT. Confirm the SFTP hostname in chat (hostnames aren't passwords), so the public SSH host key can be verified independently and pinned at `deploy/ionos_sftp_known_hosts`. No host-key pin means the action **fails closed** rather than risking credential exposure.

The upload action is triggered only by an owner-authored commit to `deploy/temptest-upload-trigger.txt` with message marker `[temptest-upload-513]` on the TempTest feature branch. It does **not** merge the PR. It uploads only `deploy/temp513-bridge.php`, refuses to overwrite an existing endpoint, and checks for the expected `index.php` and database identity in the SFTP home before any remote file creation. The result is recorded in GitHub Actions.

## Required owner-reviewed setup before activating

1. Review the draft PR and its GitHub Actions static checks (including `php -l deploy/temp513-bridge.php`).
2. **Only when explicitly approved**, upload that exact PHP file to the separate IONOS `public-temptest` directory as `temp513-bridge.php`; it must resolve at `https://temp.fisherhq.co.uk/temp513-bridge.php` and be served over HTTPS. **Never** upload it to any Fisher HQ web folder.
3. **Only when explicitly approved**, merge PR #1 into **TempTest** `main`. This activates GitHub Issues commands, not any site deployment.
4. From TempTest Actions, manually run `TempTest 513 - Owner HTTPS Test Commands` (workflow_dispatch): this invokes **status only**, no writes. Inspect sanitized GitHub logs.
5. Obtain separate explicit approval for CREATE/UPDATE/DELETE/CLEANUP commands before opening their test Issues.
6. After the exercise, use `cleanup`, remove `temp513-bridge.php` from IONOS, and delete the disposable DB and unused secrets.

## Verified so far

A GitHub-hosted action reached the existing TempTest `index.php` via HTTPS, submitted `Check connection only` using the existing DB password secret, and got passing connection and database identity checks. Direct GitHub-to-IONOS MySQL TCP access failed and is not used. The original page's `CURRENT_USER()` privilege account differed from the assumed login; the staged new bridge checks `USER()` for login identity and merely reports whether the grant account differs. This new endpoint has not yet been deployed or connection-tested live.

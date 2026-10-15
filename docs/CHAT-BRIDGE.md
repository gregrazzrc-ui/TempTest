# TempTest 513 — standalone normal-chat database capability test

**Repository scope:** `gregrazzrc-ui/TempTest` only. `index.php` is unchanged. No site deployment, other repositories, SFTP reuse or database writes have been authorised.

## Existing fixed database identity

- MariaDB database: `dbs16231513`
- Host: `db5021656421.hosting-data.io`
- Username: `dbu5597618`
- TCP port: `3306`
- TempTest GitHub Actions **repository secrets**: `FHQ_TEMP_DB_513_HOST`, `FHQ_TEMP_DB_513_USERNAME`, `FHQ_TEMP_DB_513_PASSWORD`.

The code rejects any different host or username; secrets are never printed or used in PR tests. The password secret must contain the **database** password, not an FTP password.

## How the route works

PR checks run offline Python boundary tests and syntax-check the unchanged `index.php`. On feature-branch pushes, a separate GitHub-hosted Linux job opens the existing `https://temp.fisherhq.co.uk/` page over verified HTTPS, obtains its CSRF token and session cookie, and submits the built-in `connect` action using the TempTest database secret. It parses only the page's PASS rows; the code never logs raw page output or credentials.

The first experiment connecting directly from a GitHub runner to the MariaDB TCP host failed `SECURE_DB_CONNECTION_FAILED`; this could reflect external network/TLS restrictions. We therefore use the **existing PHP hosting route** for read-only connection verification. No new PHP is uploaded.

The PHP page checks database identity and current authenticated account. If the account string reported by the hosting server differs from the expected account, the read-only check reports an explicit `account_verified: false` warning. The separate full test is **blocked before any write** until this discrepancy is resolved.

## Chat-triggered test commands (only after explicit owner approval and merge)

Once the dedicated TempTest draft PR is approved and merged onto TempTest `main`, the `issues: opened` workflow can accept only an exact-format Issue authored by the repository owner. Initially the supported commands are `TEMPTEST-513: status` (connection only) and `TEMPTEST-513: full-test` (existing PHP site's full self-cleaning capability test). The exact body for status is:

```text
TEMPTEST_513_V1
operation=status
database=dbs16231513
```

For the full-test, change the title to `TEMPTEST-513: full-test` and the body operation to `operation=full-test`. The existing PHP page then creates its own `work_capability_site_test` table, tests five records, update/delete, schema changes, transactions, migration reversal and cleanup in one server-side request. **This is not separate persistent CRUD across multiple chat turns.** If separate persistent create/read/update/delete is needed later, a dedicated TempTest-only authenticated server-side bridge must be added and deployed with separate owner permission.

The full-test command performs a first `connect` request and requires the expected authenticated account before invoking any write. It also requires all built-in checks and cleanup to return PASS. The operations and table are fixed; user-supplied SQL is never accepted. No full-test Issues have been created or executed.

## Current validation and approval gates

Review the latest branch/PR Actions evidence. A PASS from offline tests is not live DB proof. Even a PASS from the read-only HTTPS check does not authorise merges or write tests. PR remains draft until the owner explicitly approves merging; no production or live site deployments are part of this task.

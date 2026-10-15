# TempTest 513 — normal chat to disposable database experiment

All implementation and test files are **only in TempTest**. The existing `index.php` page and deployment settings are unchanged. No deploy step is included. No PHP files are uploaded to any server by these workflows.

## Identity and credentials

The only permissible MariaDB target is `dbs16231513`, hostname `db5021656421.hosting-data.io`, account `dbu5597618`, TCP port `3306`. These literal checks are enforced in Python. The three repository **Actions secrets** are `FHQ_TEMP_DB_513_HOST`, `FHQ_TEMP_DB_513_USERNAME` and `FHQ_TEMP_DB_513_PASSWORD`. Do not put credentials in GitHub issues or source files. The password must be the database password, not an FTP/SFTP password. GitHub secrets cannot be read back to verify their contents.

## Deployment and proof of connectivity

The workflow `temp-db-513-check.yml` runs offline tests on PRs and a *read-only* connection preflight on pushes to its designated feature branch. It runs on **GitHub-hosted Linux**, not any other project's private runner. The connection requires TLS with normal public CA and hostname validation and checks the selected database, MariaDB server version and authenticated account. No database modification is permitted in preflight. Its JSON evidence is sanitized and retained for seven days.

**An IONOS hosting-only database may refuse direct connections from GitHub's external runner.** A failed `SECURE_DB_CONNECTION_FAILED` does not invalidate prior IONOS-to-IONOS PHP connectivity; it means the remote route has not been proved. Do not weaken TLS or connect to another environment to work around this. If blocked, arrange a dedicated *TempTest-only* SSH/SFTP route or private authenticated endpoint, review it separately, and require owner approval before deployment.

## Normal-chat issue commands (only after owner-approved merge)

The `temp-db-513-issue.yml` workflow can run only on the repository default branch; the draft PR does not enable it. The repository owner must open a GitHub Issue with an exact title `TEMPTEST-513: status`, `TEMPTEST-513: create`, `TEMPTEST-513: read`, `TEMPTEST-513: update`, `TEMPTEST-513: delete` or `TEMPTEST-513: cleanup`. Exact three-line body with the corresponding operation, e.g.:

```text
TEMPTEST_513_V1
operation=status
database=dbs16231513
```

The owner author and GitHub event are checked before any credentials are used. No arbitrary SQL or user-supplied table names/values are accepted. `status` only checks connection and fixture table existence. `create` creates a new synthetic `temptest_chat_probe_513_v1` table (refuses to reuse an existing one) and inserts three fixed rows. `read` shows those rows, `update` changes Beta to UPDATED, `delete` removes Gamma, and `cleanup` removes only that verified fixture table. Each state change requires an individually opened owner issue; cleanup is never automatic. The synthetic rows remain for owner inspection between commands. A mismatch in schema, marker, account, host or database blocks the operation.

Do **not** merge the PR or perform database writes without explicit owner approval. Validation of Python code is not proof that the GitHub-hosted runner can reach IONOS. Read the actual Actions result before claiming connectivity.

# TempTest 513 — Chat/GitHub Bridge Quick Reference

**Authoritative full setup, actual test results and teardown instructions:** [IONOS MariaDB database how-to](IONOS-MARIADB-DATABASE-HOWTO.md).

## Confirmed status (15 October 2026)

- GitHub Actions → isolated IONOS HTTPS PHP endpoint → disposable MariaDB **dbs16231513**: **LIVE CRUD PASS**.
- Verified SFTP upload to dedicated TempTest hosting folder: **PASS**.
- Three synthetic rows created and checked through read/update/delete; fixture dropped; final status showed it absent: **PASS**.
- [Full acceptance evidence](https://github.com/gregrazzrc-ui/TempTest/actions/runs/38773537809).
- [Verified upload evidence](https://github.com/gregrazzrc-ui/TempTest/actions/runs/38773221229).
- [Draft PR #1](https://github.com/gregrazzrc-ui/TempTest/pull/1) is **not merged**. **ChatGPT → owner GitHub Issue → Actions** is staged, but **not yet end-to-end verified**.

Nothing in this lab requires Fisher HQ's production repository or operational database.

## Current architecture

- **GitHub Actions repository secrets in TempTest:** \`FHQ_TEMP_DB_513_HOST\`, \`FHQ_TEMP_DB_513_USERNAME\`, \`FHQ_TEMP_DB_513_PASSWORD\`, \`FHQ_TEMP_SFTP_USERNAME\`, \`FHQ_TEMP_SFTP_PASSWORD\`.
- SFTP host \`access-5021528741.webspace-host.com\` and username \`su78426\` are pinned in the TempTest deployment script. The dedicated account's SFTP home is already the \`public-temptest\` directory.
- Site endpoint: \`https://temp.fisherhq.co.uk/temp513-bridge.php\`, uploaded and live as part of this temporary experiment. Source: \`deploy/temp513-bridge.php\`.
- MariaDB: host \`db5021656421.hosting-data.io\`, database \`dbs16231513\`, user \`dbu5597618\`, port 3306, engine MariaDB 11.8.
- The PHP endpoint uses PDO and accepts **only** \`status\`, \`create\`, \`read\`, \`update\`, \`delete\`, \`cleanup\` on the fixed synthetic table.
- GitHub supplies the existing **database password secret** at runtime over HTTPS. There is no second database password.
- Only the disposable testing database was used; no production site deployment.

## Verified repeatable acceptance path (no PR merge required)

Feature branch: \`work/temptest-db513-chat-bridge-20261015\`.

Owner commit changing \`deploy/temptest-db-acceptance-trigger.txt\` with marker \`[temptest-acceptance-513]\` triggers \`temp513-db-acceptance.yml\`. Set trigger file to \`STATUS\` to run a read-only check; \`FULL\` runs the synthetic CRUD and cleanup sequence. **Do not run FULL without owner approval**, and refuse if the fixture already exists.

The successful \`FULL\` sequence was: initial status (absent) → create (3) → read (3) → update → read (3) → delete → read (2) → cleanup → final status (absent).

## Normal-chat Issue command path: still pending

Only after an explicit, separate owner-approved merge of PR #1 into **TempTest** \`main\`, the workflow \`.github/workflows/temp-db-513-issue.yml\` can accept an Issue authored by \`gregrazzrc-ui\` with one of the exact titles:

\`TEMPTEST-513: status\`; \`TEMPTEST-513: create\`; \`TEMPTEST-513: read\`; \`TEMPTEST-513: update\`; \`TEMPTEST-513: delete\`; \`TEMPTEST-513: cleanup\`.

For \`status\`, the Issue body is exactly:

\`\`\`text
TEMPTEST_513_V1
operation=status
database=dbs16231513
\`\`\`

Change the operation in the body to the matching title for the others. The chat-triggered workflow has **not** yet been tested via an actual Issue opening.

## Security and cleanup

This is a **temporary lab**, with a public PHP endpoint protected by the **database password**, not an independently authenticated production-grade API. Do not reuse this pattern for business data.

After the test: verify fixture absence; remove \`temp513-bridge.php\` from the dedicated TempTest site; rotate/revoke disposable credentials; remove unused secrets; delete the disposable DB and site only with explicit authorization. **The bridge endpoint has not yet been removed.** Full details and evidence are in the linked how-to.

# IONOS Database Connection — Reusable Chat Action Prompt

**Purpose:** Paste this into a future ChatGPT conversation to set up and validate an IONOS MariaDB connection using the method proven in the isolated TempTest lab. Use normal ChatGPT with the connected GitHub tools; Work mode or Codex is not required.

---

## Copy this prompt into a new chat

**Mission: Connect [PROJECT / GITHUB REPOSITORY] to its intended IONOS MariaDB database and prove the connection.**

Use the tested architecture **GitHub Actions → HTTPS → PHP PDO running on IONOS hosting → MariaDB**. Work in ordinary chat through the connected GitHub integration. Inspect the actual repository, database configuration and deployment setup first. Do **not** assume the TempTest database, website, branch, credential names or hosting folder are the target for this new job.

**Follow this procedure:**

1. **Lock the scope.** Confirm the exact GitHub repository, IONOS database name/host/username, IONOS website, SFTP account and destination web folder. Keep production, development and test environments separate. Do not edit other repositories or databases.
2. **Use GitHub Actions secrets.** Check the appropriate repository-secret names for database host, username and password, plus the SFTP username and password if deployment is needed. The user creates or updates any missing secrets in GitHub. **Never request passwords in chat, commit them, or echo them to logs.** The DB password is different from the SFTP password.
3. **Prepare the PHP/PDO bridge in the right IONOS web folder.** GitHub-hosted runners may not reach the database directly, whereas PHP on the IONOS hosting network can connect. Use the correct PDO MySQL DSN (host, port 3306, dbname, UTF-8), exception handling and prepared statements. Verify `DATABASE()` and the login indicated by `USER()`. Do not confuse `CURRENT_USER()` (grant account) with the supplied login. The bridge must have narrowly defined, authorized operations; never allow arbitrary SQL or caller-selected databases. Enforce HTTPS.
4. **Secure the endpoint for its actual purpose.** The old TempTest experiment used a disposable, password-authenticated public endpoint. **Do not copy that authorization scheme into a real or persistent database.** For business data, keep DB credentials server-side outside the public web root and use independently authenticated, scoped requests to the endpoint, with logging and replay/rate-limit protections appropriate to the system.
5. **Deploy only to the verified folder.** First pin/verify the SFTP server's SSH host key, authenticate with the SFTP GitHub secrets, inspect the remote home and known website identity *read-only*, then upload only the reviewed PHP file. The SFTP login may already be rooted in the target folder, so avoid accidentally duplicating the folder name in the remote path. Verify uploaded bytes/checksum. Do not overwrite unrelated files.
6. **Test in stages.** First run a read-only PDO connection/status check from GitHub Actions through HTTPS. Confirm the target database and login. For a dedicated disposable database, and **only after explicit owner approval for writes**, create a uniquely named synthetic table; test create → read → update → read → delete → read → cleanup → final read-only status. Refuse an existing/mismatched table; clean up only the fixture the test created. For a non-disposable database, remain read-only until a separate safe test plan is approved.
7. **Verify and report.** Read the real GitHub Actions results at the exact tested commit, plus the PHP/DB response and final fixture-absence check. Distinguish code tests from actual live database tests. Record what passed, what remains, and links to evidence. Never claim a ChatGPT → GitHub Issue workflow is tested unless an actual Issue-to-run-to-result cycle has passed.

**Operating boundaries:** Keep changes on a review branch/PR; do not merge, deploy to production, change live data, or remove hosting/database resources without the user's approval. If a required detail is missing, ask only for that detail; otherwise move through the permitted read-only preparation and validation.

**Start now:** Find the relevant GitHub repo and current configuration, identify the minimal safe changes, and show me the first actionable step. Do not make me re-enter credentials that already exist as GitHub secrets.

---

## Proven reference — use as a pattern, not as the new target

- Repo / draft PR: https://github.com/gregrazzrc-ui/TempTest/pull/1
- Full technical how-to: https://github.com/gregrazzrc-ui/TempTest/blob/work/temptest-db513-chat-bridge-20261015/docs/IONOS-MARIADB-DATABASE-HOWTO.md
- SFTP PHP upload (PASS): https://github.com/gregrazzrc-ui/TempTest/actions/runs/38773221229
- Real synthetic MariaDB create/read/update/delete/cleanup (PASS): https://github.com/gregrazzrc-ui/TempTest/actions/runs/38773537809

**What was proved:** GitHub Actions could reach the isolated IONOS PHP endpoint over HTTPS and execute real, fixed, synthetic CRUD operations against disposable MariaDB `dbs16231513`; the fixture was removed afterward. **Not yet proved in that lab:** a normal-chat-created GitHub Issue activating the workflow on the default branch. Do not present that final trigger as validated.
# IONOS DB Setup — Guided Chat Walkthrough

**Shortcut:** `ionos db setup`

**Purpose:** A reusable, conversation-led wizard for connecting the correct GitHub project to an IONOS MariaDB database. The user provides non-secret IONOS configuration, ChatGPT provides the exact GitHub Actions secret *names* and repository destination, the user confirms the secrets are configured, and then ChatGPT performs and validates a read-only connection test.

## Instructions for the assistant in a new chat

When the user says **`ionos db setup`**, **`IONOS DB setup`**, or **`set up an IONOS database`**, look up this guide in the ChatGPT Library at:

`/Reusable Chat Prompts/IONOS-Database-Connection-Chat-Prompt.md`

Then run the following stages **in order** in ordinary chat. Keep the user-facing interaction short and conversational, with one clear next action at each stage. Do not present the whole technical checklist or an input form at once. Do not assume the TempTest database or repository is the new target. Treat this as a human-readable shortcut, not an installed slash command or an automatic pop-up.

### Stage 1 — Welcome and collect setup details

Start with this message:

> Great — I've got our **IONOS DB setup walkthrough**. We'll do it in a few quick stages: details → GitHub secret names → your confirmation → live connection test.
>
> Tell me the **GitHub repository and environment** (test, development, or production), then paste the **non-secret database details** from IONOS. You can paste the whole configuration block; I'll work out what's still missing. **Don't paste passwords.**

Accept whatever the user has. Useful non-secret details include:

- Target GitHub repository, e.g. `owner/project`, and environment (test/dev/production).
- IONOS database name, hostname, port (often 3306), username, and engine/version.
- The IONOS-hosted website/domain that will execute PHP, if applicable.
- SFTP hostname, port (typically 22), username, and intended isolated web folder, **if a PHP file needs deploying**.
- Whether the IONOS database and website already exist; if not, walk through their creation in the IONOS control panel first.

Never request or display database, SFTP or API passwords in chat. Do not ask for details already supplied. If a required value is missing, ask for only the next essential detail. Confirm the repo and environment before touching GitHub.

### Stage 2 — Confirm the connection plan

Briefly summarize the target (repository, environment, database, host, user, website and web folder, where known). Confirm isolation from all other databases and repos.

Check the actual repository's current workflows, existing secret **names**, hosting conventions and whether a working secure connection route already exists. Preferred proven pattern *when appropriate to the hosting setup*:

`GitHub Actions → HTTPS → authenticated PHP/PDO endpoint on IONOS → MariaDB`

This is a pattern, **not** a reason to create an endpoint unnecessarily. If using PHP, keep database credentials server-side for persistent or business data and use independent endpoint authorization. Do not copy the disposable TempTest password-only web endpoint into a production environment. Validate the selected database with `DATABASE()` and the login name with `USER()`; remember that `CURRENT_USER()` can identify a different MariaDB grant account.

### Stage 3 — Produce the exact GitHub Secrets checklist

Now say something like:

> Perfect. For **`owner/project`**, create or confirm the following **GitHub Actions repository secrets**. I'll give you the **secret key names**, never ask you to send the secret values. Add them under **Settings → Secrets and variables → Actions → Repository secrets**. Reuse matching existing secrets instead of creating duplicates.

Generate names tailored to **the actual project/environment**, using existing names where already established. When no convention exists, propose one consistent uppercase prefix such as `IONOS_<PROJECT>_<ENV>`, with only letters, numbers and underscores, followed by:

| Secret name suffix | What the user enters in GitHub, not in chat |
| --- | --- |
| `_DB_HOST` | IONOS database hostname |
| `_DB_USERNAME` | IONOS database username |
| `_DB_PASSWORD` | IONOS database password |
| `_SFTP_USERNAME` | IONOS SFTP username, only if deployment is needed |
| `_SFTP_PASSWORD` | IONOS SFTP password, only if deployment is needed |

If the SFTP host is not pinned in reviewed code, include a separate `_SFTP_HOST` name; otherwise make clear that no host secret is necessary. The database name may be fixed in the reviewed config or supplied through a named variable/secret as appropriate. Use the **literal final key names** in the response, with **the target repository and exact settings location**. Do not confuse secret names with GitHub's internal IDs, and do not expose any secret values.

Then **stop and wait** for a simple user confirmation such as **"secrets added"**, **"done"**, or a correction to the names. Do **not** start a live connection test before confirmation.

### Stage 4 — Prepare and run read-only connection verification

After confirmation:

1. Re-read the exact target repository, selected environment and configuration; verify configured secret *presence* by a safe test workflow rather than pretending GitHub can reveal the secret values.
2. Work on a review branch/PR. Prepare the smallest required GitHub Actions + PHP/PDO integration for the target, reusing existing secure setup when possible.
3. If a PHP bridge must be uploaded, verify the SFTP server identity and restricted remote destination **read-only first**. Ask for **explicit deployment approval** before putting a file on a real website, even a test website. Verify its deployed bytes/checksum; do not overwrite unrelated files.
4. Run the **read-only** live test from GitHub Actions over HTTPS. Confirm that the response comes from the intended MariaDB database and account; return only safe diagnostics, never credentials or private records. Check the *actual* GitHub Actions job result and the exact tested commit.
5. Report clearly **Connected / Blocked / Not yet tested**, with a link to the real validation run and the next action if blocked. Never invent a PASS result. If blocked, investigate one issue at a time without asking the user to re-enter existing passwords.

### Stage 5 — Optional database write test (separate approval)

Only when the owner *explicitly authorizes a disposable test* and the target is safe, create a uniquely named synthetic fixture and verify:

`create → read → update → read → delete → read → cleanup → final status (fixture absent)`

Refuse to overwrite an existing table; limit all commands to the named temporary test table and database. For a production or otherwise valuable database, stay read-only until a separately approved safe plan exists. Never merge, deploy production code, remove a database, rotate credentials or write business records without explicit approval.

### Stage 6 — Short handover

Return a compact completion report: chosen repo/environment, database identity (never passwords), secrets *by name*, connection method, actual read-only test result with GitHub link, any separately approved write-test result, cleanup state, and any outstanding approval gates. Save relevant setup notes to a reviewed repo document/PR; do not change unrelated Fisher HQ resources.

## Tested implementation to use as a technical reference ONLY

- [TempTest database how-to](https://github.com/gregrazzrc-ui/TempTest/blob/work/temptest-db513-chat-bridge-20261015/docs/IONOS-MARIADB-DATABASE-HOWTO.md)
- [Successful isolated SFTP upload](https://github.com/gregrazzrc-ui/TempTest/actions/runs/38773221229)
- [Successful live MariaDB synthetic CRUD and cleanup](https://github.com/gregrazzrc-ui/TempTest/actions/runs/38773537809)

The **GitHub Actions → PHP/PDO → MariaDB** route has been demonstrated. The **normal ChatGPT → newly opened GitHub Issue → default-branch Actions** route was not demonstrated by those runs; do not claim otherwise. Always adapt the host, database, user, secrets and folder for the new project rather than copying TempTest values.

---

**User's shorthand:** `ionos db setup` means **start Stage 1 of this walkthrough**, not automatically deploy files or make database changes.
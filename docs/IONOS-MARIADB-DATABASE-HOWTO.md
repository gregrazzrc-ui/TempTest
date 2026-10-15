# IONOS MariaDB from ChatGPT via GitHub — Tested How-To & Acceptance Report

**Project:** TempTest disposable database lab  
**Verified:** 15 October 2026  
**Status:** Real GitHub Actions → IONOS PHP → MariaDB CRUD and cleanup **PASS**. Draft PR #1 **not merged**; the normal ChatGPT → GitHub Issue trigger has **not yet been exercised end-to-end**.  
**Repository:** [gregrazzrc-ui/TempTest](https://github.com/gregrazzrc-ui/TempTest) — **not** the Fisher HQ application repository.

> **Important boundary:** This is a reproducible record of a *disposable* lab, not production deployment instructions. It uses a public PHP endpoint whose authorization relies on the database password. Do not copy that authorization pattern into a production or customer-data system. Remove the PHP endpoint and rotate the temporary password when finished.

## 1. What we set out to prove

Can regular ChatGPT, using a connected GitHub account, cause controlled operations on an IONOS MariaDB database, with **no Work mode, no credentials pasted into chat, and no access to any Fisher HQ operational database**?

**Proven:** GitHub Actions can use a stored temporary database password to call an IONOS-hosted HTTPS/PHP PDO bridge. We executed a complete sequence of **create, read, update, read, delete, read, cleanup, final status** against three *synthetic* test rows. The test returned PASS and confirmed the test table had been removed.

**Not yet proven:** A newly opened owner-authored GitHub Issue *originating in normal ChatGPT chat* activating the default-branch workflow. That workflow is staged in [draft TempTest PR #1](https://github.com/gregrazzrc-ui/TempTest/pull/1), which was deliberately left **unmerged**. The successful live operations used a separately owner-gated feature-branch **acceptance workflow**.

## 2. Exact isolated environment used

| Component | Verified configuration |
| --- | --- |
| GitHub repository | \`gregrazzrc-ui/TempTest\` |
| Draft PR | [#1](https://github.com/gregrazzrc-ui/TempTest/pull/1) |
| IONOS DB name | \`dbs16231513\` |
| IONOS DB hostname | \`db5021656421.hosting-data.io\` |
| MariaDB user | \`dbu5597618\` |
| Database port / engine | \`3306\` / MariaDB **11.8** (as reported in IONOS) |
| Temporary HTTPS website | \`https://temp.fisherhq.co.uk/\` |
| PHP bridge URL | \`https://temp.fisherhq.co.uk/temp513-bridge.php\` |
| SFTP host / port | \`access-5021528741.webspace-host.com\` / \`22\` |
| SFTP user | \`su78426\` |
| Remote hosting folder | IONOS \`public-temptest\`. The dedicated SFTP account's **home already opens in that directory**; within its SFTP session use \`temp513-bridge.php\`, *not* \`public-temptest/temp513-bridge.php\`. |
| Synthetic fixture table | \`temptest_chat_probe_513_v1\` |

The temporary domain shares a naming family with Fisher HQ, but **the test repository, database, deployment file, and SFTP web-folder target were isolated**. We did not change the production/dev databases or deploy the Fisher HQ application.

## 3. The five required GitHub Secrets

Add the following to **TempTest → Settings → Secrets and variables → Actions → Repository secrets** (not the Fisher HQ repository):

| GitHub Actions secret | Value/source | Purpose |
| --- | --- | --- |
| \`FHQ_TEMP_DB_513_HOST\` | \`db5021656421.hosting-data.io\` | Pinned MariaDB host |
| \`FHQ_TEMP_DB_513_USERNAME\` | \`dbu5597618\` | Database login |
| \`FHQ_TEMP_DB_513_PASSWORD\` | The IONOS *database* password | PDO authentication |
| \`FHQ_TEMP_SFTP_USERNAME\` | \`su78426\` | Restricted webspace upload account |
| \`FHQ_TEMP_SFTP_PASSWORD\` | The IONOS *SFTP* password | Upload authentication |

**The database password and SFTP password are different kinds of credential.** The database password was already present in GitHub and successfully used by Actions. No password was embedded in the PHP file, GitHub issue, or report.

In this verified implementation, the **SFTP hostname is pinned in** \`scripts/deploy_temp513_sftp.py\`; a \`FHQ_TEMP_SFTP_HOST\` GitHub secret is **not required**. GitHub does not reveal saved secret values, so check exact secret names carefully.

## 4. Architecture: why the PHP bridge was necessary

\`\`\`text
Normal ChatGPT  ──(proposed: create exact TempTest Issue)──> GitHub Issue
                                                              |
                                           [default branch + owner validation]
                                                              |
                                                              v
                                                GitHub Actions (Ubuntu)
                                                 TempTest repo secrets
                                                              |
                                                              | HTTPS POST, fixed JSON
                                                              v
                                        temp.fisherhq.co.uk/temp513-bridge.php
                                                 (IONOS PHP / PDO)
                                                              |
                                                IONOS hosting DB network
                                                              |
                                                              v
                                               MariaDB: dbs16231513
\`\`\`

The **working, demonstrated** path started from the owner-controlled GitHub Actions acceptance run rather than a ChatGPT Issue.

We first tried a direct TLS-protected TCP connection from GitHub's hosted runner to the database hostname. That attempt returned \`SECURE_DB_CONNECTION_FAILED\`. This establishes that the tested direct route failed, **not** whether all IONOS accounts block remote TCP. We did not weaken TLS to get around it.

Instead we used the existing PHP hosting, which had already passed a read-only connection check. Then we installed a **small, fixed-operation** PHP endpoint in that *same isolated temporary hosting folder*. GitHub contacts it over HTTPS and supplies the GitHub database password secret at execution time; PHP calls \`new PDO(...)\` from the IONOS hosting environment.

The PHP implementation is at [\`deploy/temp513-bridge.php\`](https://github.com/gregrazzrc-ui/TempTest/blob/work/temptest-db513-chat-bridge-20261015/deploy/temp513-bridge.php). It uses a pinned PDO DSN of the following form, **without storing a password in source**:

\`\`\`php
$pdo = new PDO(
    'mysql:host=db5021656421.hosting-data.io;port=3306;dbname=dbs16231513;charset=utf8mb4',
    'dbu5597618',
    $password, // supplied from the TempTest GitHub database secret over HTTPS
    [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
     PDO::ATTR_EMULATE_PREPARES => false]
);
\`\`\`

The endpoint allows *only* \`status\`, \`create\`, \`read\`, \`update\`, \`delete\`, and \`cleanup\` on a fixed synthetic table. It does **not** accept arbitrary SQL or caller-chosen table names.

### A misleading MariaDB account mismatch

Our original \`index.php\` displayed \`CURRENT_USER()\`, and a strict checker expected it to equal the IONOS login. But in MariaDB, **\`USER()\` describes the login presented by the client**, while **\`CURRENT_USER()\` identifies the matched privilege/grant account**. They can differ. The already successful authentication meant the mismatch did *not* automatically imply a bad password.

The dedicated endpoint checks \`DATABASE()\`, the login component of \`USER()\`, and the MariaDB engine; it does not assume that \`CURRENT_USER()\` must equal the login. The live CRUD acceptance subsequently passed. We did **not** expose the raw grant-account identity in public logs or prove precisely why IONOS mapped it differently.

## 5. Exact implementation steps that worked

### Step A — Keep hosting and database separate

1. Work only in the **TempTest** repo and with the dedicated disposable IONOS database.
2. Confirm IONOS database host, user, name, port and engine as listed in Section 2.
3. Make sure the isolated website responds over HTTPS, PHP and \`pdo_mysql\` are enabled, and the existing \`index.php\` connects to database 513.
4. Never use a Fisher HQ production or dev database as a fallback.

### Step B — Prove SFTP identity and destination *before writing*

1. Use SFTP host \`access-5021528741.webspace-host.com\`, port 22, account \`su78426\`.
2. Observe and pin the SFTP server's ED25519 host key in [\`deploy/ionos_sftp_known_hosts\`](https://github.com/gregrazzrc-ui/TempTest/blob/work/temptest-db513-chat-bridge-20261015/deploy/ionos_sftp_known_hosts).
3. The GitHub [host-key audit](https://github.com/gregrazzrc-ui/TempTest/actions/runs/38772734252) observed fingerprint \`SHA256:1gx2w8Rtv3wCgi7Jh8myf/KVd72cRQbow03UP8P095Q\`. **Check it independently with IONOS** before relying on it outside this lab; an SSH keyscan by itself is not independent identity verification.
4. Run the read-only [SFTP destination audit](https://github.com/gregrazzrc-ui/TempTest/actions/runs/38772988725). It verified \`sftp_login=PASS\`, \`root_is_temp_site=true\`, \`subfolder_is_temp_site=false\`, \`home_is_chroot_root=true\`, and \`destination_ambiguous=false\`.
5. **Stop** if login, host-key verification, or isolated destination checks fail.

### Step C — Upload just one PHP bridge

The deployed file was [\`deploy/temp513-bridge.php\`](https://github.com/gregrazzrc-ui/TempTest/blob/work/temptest-db513-chat-bridge-20261015/deploy/temp513-bridge.php). Upload was performed by [\`scripts/deploy_temp513_sftp.py\`](https://github.com/gregrazzrc-ui/TempTest/blob/work/temptest-db513-chat-bridge-20261015/scripts/deploy_temp513_sftp.py) via the dedicated [SFTP workflow](https://github.com/gregrazzrc-ui/TempTest/blob/work/temptest-db513-chat-bridge-20261015/.github/workflows/temp513-sftp-upload.yml), using the restricted SFTP user and password secret.

- The feature-branch upload workflow watches \`deploy/temptest-upload-trigger.txt\` and requires an owner commit whose message contains \`[temptest-upload-513]\`.
- Before upload, the script checks the pinned SSH host key, expected \`index.php\`, exact DB reference and absence of an existing bridge file.
- It uploads \`temp513-bridge.php.uploading\`, reads the bytes back, checks equality, then renames it to \`temp513-bridge.php\`. It refuses an unreviewed overwrite.

**Verified result:** [GitHub upload run #38773221229](https://github.com/gregrazzrc-ui/TempTest/actions/runs/38773221229) returned \`PASS\`, \`bytes=8961\`, remote target \`public-temptest/temp513-bridge.php\`, and SHA-256 \`a71f460b51e3b7c3a4fb17411aedde7b99573f82673e3c26a62d560f8702ea0e\`. The upload step did not execute SQL.

### Step D — Read-only database acceptance

The [\`temp513-db-acceptance.yml\` workflow](https://github.com/gregrazzrc-ui/TempTest/blob/work/temptest-db513-chat-bridge-20261015/.github/workflows/temp513-db-acceptance.yml) runs [\`scripts/accept_temp513_database.py\`](https://github.com/gregrazzrc-ui/TempTest/blob/work/temptest-db513-chat-bridge-20261015/scripts/accept_temp513_database.py).

In the verified branch it is triggered by an owner-authored commit changing \`deploy/temptest-db-acceptance-trigger.txt\` with message marker \`[temptest-acceptance-513]\`. Content must be exactly **\`STATUS\`** for read-only, or **\`FULL\`** for the synthetic write test.

With \`STATUS\`, GitHub sends the fixed \`status\` operation to the PHP endpoint. [Run #38773458699](https://github.com/gregrazzrc-ui/TempTest/actions/runs/38773458699) returned PASS and confirmed that the synthetic fixture table did not yet exist.

### Step E — Complete live CRUD + cleanup acceptance

An explicitly owner-triggered **\`FULL\`** acceptance repeated the initial status check; refused to reuse an existing fixture; then ran fixed operations in order. GitHub [run #38773537809](https://github.com/gregrazzrc-ui/TempTest/actions/runs/38773537809) returned **SUCCESS**:

| Order | Actual check | Verified evidence |
| --- | --- | --- |
| 1 | \`status\` | Fixture initially absent |
| 2 | \`create\` | Three synthetic records written |
| 3 | \`read\` | Three rows returned |
| 4 | \`update\` | Updated fixture verified |
| 5 | \`read\` | Three rows still returned after update |
| 6 | \`delete\` | One synthetic row deleted |
| 7 | \`read\` | Two rows returned |
| 8 | \`cleanup\` | Fixed test table dropped |
| 9 | \`status\` | **Fixture absent** after cleanup |

The fixture names were Alpha, Beta and Gamma. The update changes Beta's \`state\` from \`CREATED\` to \`UPDATED\`; the delete removes Gamma. Database identity and returned row shape are checked by the Python client. The acceptance script attempts recovery cleanup on failure after it starts creating a fixture, but **cleanup on arbitrary crashes cannot be guaranteed**; inspect the temporary table before rerunning a failed test.

### Step F — Review the GitHub code checks

The current draft PR's code validation ran **25 offline unit tests**, PHP syntax checks on both the existing \`index.php\` and the new endpoint, and passed at PR head \`a6ece52adab3c7c2d95af61521f6d4cc00034d77\`:

- [Successful PR check #38773804071](https://github.com/gregrazzrc-ui/TempTest/actions/runs/38773804071).

The offline checks and live acceptance are **distinct kinds of evidence**; one does not substitute for the other. Later documentation-only commits may cause newer CI runs; always check the **current PR head** before declaring a new green validation.

## 6. How to repeat the test safely

1. Review that the target is the disposable TempTest DB **513**, the PHP endpoint is the expected file, the SFTP account is restricted, and all secret names match Section 3.
2. Confirm the test table is *absent* via \`STATUS\`. If present unexpectedly, **do not run FULL**, and inspect it first.
3. Confirm the user has approved real writes against this disposable database.
4. Run \`FULL\` via the branch's acceptance-trigger workflow and read its **actual GitHub Actions run log or artifact**, not just the workflow name.
5. Require all nine operations to PASS and final \`table_exists=false\`.
6. Investigate rather than retry blindly if any step fails. Never drop other tables.

The above is the **proven repeatable acceptance path**. It does **not** require a PR merge or putting passwords into ChatGPT.

## 7. Activating individual commands from ordinary chat: still pending

The desired future route is **ChatGPT → owner-created TempTest GitHub Issue → GitHub Actions → the same PHP endpoint**. The implementation is staged in the draft PR but not active on \`main\`.

After separate owner approval to merge **TempTest PR #1 only**, the workflow \`.github/workflows/temp-db-513-issue.yml\` can respond to an **Issue opened by \`gregrazzrc-ui\`** with an exact title, such as:

\`\`\`text
TEMPTEST-513: status
\`\`\`

and exact three-line Issue body:

\`\`\`text
TEMPTEST_513_V1
operation=status
database=dbs16231513
\`\`\`

For other commands, use \`create\`, \`read\`, \`update\`, \`delete\`, or \`cleanup\` in both the title and body. No arbitrary SQL may be supplied. **Do not claim the normal-chat issue path is verified until an actual new Issue opens, the Actions run executes and a matching sanitized result is read back in chat.**

## 8. Security boundaries and teardown

**This is a temporary capability demonstration, not a production-ready API.** The PHP endpoint accepts a database password in an HTTPS POST body, and anyone who already knows that password could invoke its limited operations. The test has a fixed database and a single synthetic table, but the public URL must not be considered safe indefinitely. Database transport from PHP to IONOS was not independently verified as TLS, even though the GitHub-to-PHP leg used HTTPS.

Before using a similar design for business data, add independently authenticated requests (separate short-lived API credentials and replay protection), scope/audit authorization, apply rate limits, deploy with a controlled release process, rotate credentials, and restrict data-access permissions appropriately. Do **not** reuse this lab's PHP endpoint, database password or SFTP permissions for Fisher HQ.

When the experiment is finished:

1. Confirm no synthetic fixture remains using read-only \`status\` and, if necessary, manual inspection of *only* the temporary DB.
2. Remove \`temp513-bridge.php\` from the **\`public-temptest\`** folder. This has **not** been done yet.
3. Revoke/rotate the disposable database password and SFTP credentials; remove unused TempTest GitHub Secrets after they are no longer needed.
4. Delete the temporary database/site only when their complete removal is explicitly authorised.
5. Keep the GitHub Actions logs and this how-to as an audit record; avoid keeping live test infrastructure active unnecessarily.

## 9. Final verified outcome

| Question | Answer |
| --- | --- |
| Can GitHub Actions authenticate to the temporary IONOS DB through PHP? | **Yes — real PASS** |
| Can the dedicated SFTP account write only to the expected temporary web root? | **The inspected SFTP home and uploaded file matched the isolated test site.** |
| Were create/read/update/delete actually executed? | **Yes — real MariaDB PASS** |
| Was the fixture removed at the end? | **Yes — subsequent status returned absent** |
| Did any Fisher HQ application deployment or database participate? | **No, not in the recorded lab runs** |
| Is the ChatGPT → GitHub Issue workflow activated and end-to-end validated? | **No — draft PR #1 is unmerged; that final step remains** |

**Bottom line:** We built and proved an isolated, password-from-GitHub, HTTPS/PHP-PDO bridge to **IONOS MariaDB 11.8**. The database access and full synthetic CRUD acceptance work. The final normal-chat command trigger and later teardown are separate remaining tasks.

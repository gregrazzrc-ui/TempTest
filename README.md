# TempTest — IONOS database lab

A standalone PHP test page for https://temp.fisherhq.co.uk. It is independent of Fisher HQ production.

**Current verified GitHub → IONOS MariaDB lab:** See [IONOS MariaDB Database How-To & Acceptance Report](docs/IONOS-MARIADB-DATABASE-HOWTO.md). It records successful SFTP upload, real synthetic CRUD and cleanup, evidence links, and the still-pending normal-chat Issue trigger. The original manual PHP page below remains available as a separate diagnostic.

## Hosting
1. Create a dedicated IONOS webspace folder, for example /temptest. Do not use the production folder.
2. Upload index.php into that folder.
3. Point temp.fisherhq.co.uk to that folder in IONOS.
4. Enable HTTPS and PHP 8.1 or newer with the PDO MySQL extension.
5. Visit the HTTPS site and enter the temporary database password. First use **Check connection only**, then **Run isolated test & clean up**.

The database is fixed to dbs16231513 at db5021656421.hosting-data.io, using dbu5597618.
The password is entered at runtime; it is not in this repository, session storage or application logs. No password is prefilled.
HTTPS protects the browser-to-PHP request. Database transport uses the IONOS hosting network; this page does not claim verified TLS on that separate connection.
The application fails closed if HTTPS is not reported by the server. If a proxy is used, configure HTTPS detection correctly at the server; do not blindly trust a forwarded header.

## What it does
Connection-only checks read the actual selected database, server version and authenticated account.
The full test creates the uniquely named work_capability_site_test table, then checks:
- five inserted records and SELECT;
- two updates and one deletion;
- an added column and a filtered/sorted query;
- transaction commit and rollback;
- a column-and-index schema migration and its explicit reverse migration;
- removal of the test table and records.

An existing table of the same name is never reused or dropped. Cleanup is attempted only when this request successfully created its own table.
If PHP is killed or the server disconnects, cleanup cannot be guaranteed: inspect phpMyAdmin for work_capability_site_test before rerunning.
Schema reversal uses ALTER TABLE; it is separate from transaction rollback.
The test does not delete the database or modify other tables.
Only executed checks receive results; subsequent checks stop on failure.

## GitHub-to-IONOS connection (verified TempTest-only bridge)
A dedicated GitHub Actions SFTP upload workflow successfully placed `deploy/temp513-bridge.php` in the isolated `public-temptest` hosting directory. The separate MariaDB acceptance workflow then used the **existing TempTest GitHub database Secrets** to run actual create/read/update/delete/cleanup through the HTTPS PHP PDO endpoint. A final database `status` verified the fixture was removed. See the [full how-to](docs/IONOS-MARIADB-DATABASE-HOWTO.md) for the exact setup, branch workflows, confirmed run IDs and safe teardown.

The PHP site is hosted by IONOS, **not GitHub Pages**. The bridge is temporary and remains uploaded until deliberately removed. The normal-chat → GitHub Issue path is staged in **draft PR #1** but has not been tested end-to-end because it is not merged onto `main`.

## Verification status
The earlier phpMyAdmin experiment was followed by actual GitHub Actions live database acceptance on 15 October 2026: **PASS** ([run #38773537809](https://github.com/gregrazzrc-ui/TempTest/actions/runs/38773537809)). Offline Python tests and PHP syntax validation also passed. The old manual page and the new GitHub-operated PHP endpoint are distinct interfaces. Remove the temporary bridge, site and database when the lab is finished and removal is explicitly authorised.

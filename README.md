# TempTest — IONOS database lab

A standalone PHP test page for https://temp.fisherhq.co.uk. It is independent of Fisher HQ production.

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

## Deployment from GitHub
No automatic deployment has been configured. Before adding it, identify the IONOS SFTP/SSH endpoint, account, dedicated destination folder and authentication method. Keep deployment credentials in GitHub Actions secrets, never committed files.
The repository alone does not host PHP. GitHub Pages cannot execute this page.
Do not point a deployment at Fisher HQ's production folder.

## Verification status
The equivalent CRUD, schema, transaction and cleanup operations were executed successfully through IONOS phpMyAdmin before this page was created.
This PHP page must still be linted and tested on PHP hosting. The local preparation environment has no PHP interpreter.
The phpMyAdmin test used its own IONOS account; this page intentionally tests the supplied database user separately.
Remove the site and temporary database after the exercise.

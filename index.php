<?php
declare(strict_types=1);
ini_set('display_errors', '0');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: no-referrer');
header("Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'");
$secure = !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off';
session_set_cookie_params(['httponly' => true, 'secure' => $secure, 'samesite' => 'Strict']);
session_start();
if (empty($_SESSION['csrf'])) { $_SESSION['csrf'] = bin2hex(random_bytes(32)); }
$results = [];
$error = '';
$pdo = null;
$created = false;
$table = 'work_capability_site_test';
function rowResult(string $test, bool $ok, string $evidence): void {
    global $results;
    $results[] = [$test, $ok ? 'PASS' : 'FAIL', $evidence];
    if (!$ok) { throw new RuntimeException('Verification failed.'); }
}
function esc(string $value): string { return htmlspecialchars($value, ENT_QUOTES, 'UTF-8'); }
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!$secure) {
        $error = 'Enable HTTPS before submitting a database password.';
    } elseif (!hash_equals($_SESSION['csrf'], (string)($_POST['csrf'] ?? ''))) {
        $error = 'This form expired. Reload the page and try again.';
    } elseif (!in_array($_POST['action'] ?? '', ['connect', 'test'], true)) {
        $error = 'Unknown action.';
    } elseif (!extension_loaded('pdo_mysql')) {
        $error = 'The PHP PDO MySQL driver is unavailable. Enable it in your hosting configuration.';
    } elseif (empty($_POST['password'])) {
        $error = 'Enter the temporary database password.';
    } else {
        try {
            $pdo = new PDO(
                'mysql:host=db5021656421.hosting-data.io;port=3306;dbname=dbs16231513;charset=utf8mb4',
                'dbu5597618',
                (string)$_POST['password'],
                [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                 PDO::ATTR_EMULATE_PREPARES => false,
                 PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                 PDO::ATTR_TIMEOUT => 10]
            );
            unset($_POST['password']);
            $identity = $pdo->query('SELECT DATABASE() AS db, VERSION() AS version, CURRENT_USER() AS account')->fetch();
            rowResult('Connection', true, 'Connected from this PHP hosting server.');
            rowResult('Database identity', $identity['db'] === 'dbs16231513', $identity['db'] . ' / ' . $identity['version']);
            rowResult('Authenticated account', true, $identity['account']);
            if ($_POST['action'] === 'test') {
                // A normal table is intentional: DDL, persistence and cleanup must be tested.
                // No IF NOT EXISTS: never reuse or delete an existing table.
                $pdo->exec("CREATE TABLE work_capability_site_test (id INT PRIMARY KEY, label VARCHAR(40) NOT NULL, score INT NOT NULL) ENGINE=InnoDB");
                $created = true;
                rowResult('Create table', count($pdo->query('SHOW COLUMNS FROM work_capability_site_test')->fetchAll()) === 3, 'Three-column test table verified.');
                $pdo->exec("INSERT INTO work_capability_site_test VALUES (1,'Alpha',10),(2,'Beta',20),(3,'Gamma',30),(4,'Delta',40),(5,'Epsilon',50)");
                $records = $pdo->query('SELECT * FROM work_capability_site_test ORDER BY id')->fetchAll();
                rowResult('Insert and read', count($records) === 5 && $records[4]['label'] === 'Epsilon', 'Five sample records retrieved.');
                $pdo->exec('UPDATE work_capability_site_test SET score=score+5 WHERE id IN (1,2)');
                rowResult('Update', (int)$pdo->query('SELECT COUNT(*) FROM work_capability_site_test WHERE (id=1 AND score=15) OR (id=2 AND score=25)')->fetchColumn() === 2, 'Both changed values verified.');
                $pdo->exec('DELETE FROM work_capability_site_test WHERE id=5');
                rowResult('Delete', (int)$pdo->query('SELECT COUNT(*) FROM work_capability_site_test')->fetchColumn() === 4 && (int)$pdo->query('SELECT COUNT(*) FROM work_capability_site_test WHERE id=5')->fetchColumn() === 0, 'Four remain; deleted record absent.');
                $pdo->exec('ALTER TABLE work_capability_site_test ADD COLUMN note VARCHAR(80) NULL');
                $baseline = $pdo->query('SHOW COLUMNS FROM work_capability_site_test')->fetchAll();
                rowResult('Schema change', count($baseline) === 4 && $baseline[3]['Field'] === 'note', 'Added note column verified.');
                $scores = array_map('intval', $pdo->query('SELECT score FROM work_capability_site_test WHERE score>=25 ORDER BY score DESC')->fetchAll(PDO::FETCH_COLUMN));
                rowResult('Filter and sort', $scores === [40,30,25], 'Scores returned in order: 40, 30, 25.');
                $pdo->beginTransaction();
                $pdo->exec('UPDATE work_capability_site_test SET score=999 WHERE id=1');
                $during = (int)$pdo->query('SELECT score FROM work_capability_site_test WHERE id=1')->fetchColumn();
                $pdo->rollBack();
                rowResult('Transaction rollback', $during === 999 && (int)$pdo->query('SELECT score FROM work_capability_site_test WHERE id=1')->fetchColumn() === 15, 'Uncommitted 999 reverted to 15.');
                $pdo->beginTransaction();
                $pdo->exec("UPDATE work_capability_site_test SET note='committed' WHERE id=2");
                $pdo->commit();
                rowResult('Transaction commit', $pdo->query('SELECT note FROM work_capability_site_test WHERE id=2')->fetchColumn() === 'committed', 'Committed value read back.');
                $pdo->exec('ALTER TABLE work_capability_site_test ADD COLUMN migration_flag INT NOT NULL DEFAULT 0, ADD INDEX work_test_score (score)');
                $columns = $pdo->query('SHOW COLUMNS FROM work_capability_site_test')->fetchAll();
                $indexes = $pdo->query('SHOW INDEX FROM work_capability_site_test')->fetchAll();
                rowResult('Migration', count($columns) === 5 && in_array('work_test_score', array_column($indexes, 'Key_name'), true), 'New column and index verified.');
                $pdo->exec('ALTER TABLE work_capability_site_test DROP INDEX work_test_score, DROP COLUMN migration_flag');
                rowResult('Migration reversal', $pdo->query('SHOW COLUMNS FROM work_capability_site_test')->fetchAll() === $baseline && count($pdo->query('SHOW INDEX FROM work_capability_site_test')->fetchAll()) === 1, 'Original columns restored; only primary index remains.');
            }
        } catch (Throwable $e) {
            // Never display raw database errors, stack traces, DSNs or credentials.
            $code = $e instanceof PDOException ? (int)($e->errorInfo[1] ?? 0) : 0;
            $messages = [1045 => 'Database authentication was refused. Check the temporary password and account.',
                1044 => 'This database account lacks a required permission.',
                1050 => 'The test table already exists. It was not reused or removed.',
                2002 => 'The hosting server could not reach the database.',
                2005 => 'The database hostname could not be resolved.'];
            $error = $messages[$code] ?? 'The operation did not complete. Review the results below; no success is assumed.';
        } finally {
            unset($_POST['password']);
            if ($pdo instanceof PDO && $pdo->inTransaction()) { $pdo->rollBack(); }
            if ($created && $pdo instanceof PDO) {
                try {
                    $pdo->exec('DROP TABLE work_capability_site_test');
                    $names = $pdo->query('SHOW TABLES')->fetchAll(PDO::FETCH_COLUMN);
                    $gone = !in_array($table, $names, true);
                    $results[] = ['Cleanup', $gone ? 'PASS' : 'FAIL', $gone ? 'Test table and all its records removed.' : 'Test table still present; manual cleanup required.'];
                } catch (Throwable $cleanupError) {
                    $results[] = ['Cleanup', 'FAIL', 'Could not verify removal. Inspect work_capability_site_test in phpMyAdmin.'];
                }
            }
            $pdo = null;
        }
    }
}
?>
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>TempTest · Database lab</title>
<style>
:root{color-scheme:light;font:16px/1.6 system-ui,sans-serif;color:#18312d;background:#f1f5f2}*{box-sizing:border-box}body{margin:0}main{max-width:1000px;margin:60px auto;padding:0 24px}.eyebrow{font-size:12px;letter-spacing:.16em;font-weight:750;color:#52736b}h1{font-size:clamp(32px,6vw,56px);letter-spacing:-.05em;line-height:1.1;margin:14px 0 20px}.lead{font-size:19px;color:#52736b;max-width:650px}.card{background:white;border:1px solid #d9e4df;border-radius:18px;padding:28px;margin:26px 0;box-shadow:0 8px 32px #16382c06}.meta{display:flex;gap:24px;flex-wrap:wrap;font-size:14px}.meta span{display:block;color:#647a72;font-size:12px}label{display:block;font-weight:650;margin-bottom:8px}input{font:inherit;padding:12px;border:1px solid #b5cac1;border-radius:8px;width:100%;max-width:480px}.actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:18px}button{font:inherit;font-weight:650;padding:12px 20px;border-radius:8px;border:1px solid #1b6650;background:#1b6650;color:white;cursor:pointer}button.secondary{background:white;color:#1b6650}.small{font-size:13px;color:#647a72}.error{background:#fff0ec;border-left:4px solid #b34327;padding:16px}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:12px;border-bottom:1px solid #e4ece8}.pass{color:#146744;font-weight:750}.fail{color:#a13624;font-weight:750}footer{font-size:13px;color:#647a72;padding-bottom:40px}@media(max-width:600px){main{margin-top:28px}.card{padding:18px}button{width:100%}}
</style></head>
<body><main>
<div class="eyebrow">TEMPTEST / ISOLATED DATABASE LAB</div>
<h1>A small site.<br>A real database test.</h1>
<p class="lead">Check the connection from IONOS hosting, then verify records, schema changes and transaction behaviour.</p>
<div class="card meta"><div><span>DATABASE</span>dbs16231513</div><div><span>ENGINE</span>MariaDB</div><div><span>INTENDED SITE</span>temp.fisherhq.co.uk</div></div>
<div class="card">
<h2>Run a check</h2>
<p>Use the temporary database password. It is sent only to this hosting server over HTTPS for this request, and is not saved by this application.</p>
<?php if (!$secure): ?><p class="error">HTTPS is required before submitting credentials.</p><?php endif; ?>
<form method="post" autocomplete="off">
<input type="hidden" name="csrf" value="<?= esc($_SESSION['csrf']) ?>">
<label for="password">Temporary database password</label>
<input type="password" id="password" name="password" required autocomplete="off">
<div class="actions"><button class="secondary" name="action" value="connect" <?= !$secure ? 'disabled' : '' ?>>Check connection only</button><button name="action" value="test" <?= !$secure ? 'disabled' : '' ?>>Run isolated test &amp; clean up</button></div>
<p class="small">The full test creates only work_capability_site_test, then removes it. Existing tables are never reused. The database itself is not deleted.</p>
</form></div>
<?php if ($error !== ''): ?><p class="error" role="alert"><?= esc($error) ?></p><?php endif; ?>
<?php if ($results): ?><div class="card"><h2>Actual execution results</h2><div class="table-wrap"><table><thead><tr><th>Test</th><th>Status</th><th>Evidence</th></tr></thead><tbody>
<?php foreach ($results as $r): ?><tr><td><?= esc($r[0]) ?></td><td class="<?= $r[1] === 'PASS' ? 'pass' : 'fail' ?>"><?= esc($r[1]) ?></td><td><?= esc($r[2]) ?></td></tr><?php endforeach; ?>
</tbody></table></div><p class="small">Only completed checks appear here. If an operation fails, later tests are not run; cleanup is still attempted for the table this request created.</p></div><?php endif; ?>
<footer>Temporary diagnostic site · Separate from Fisher HQ production · Remove after testing.</footer>
</main></body></html>

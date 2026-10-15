<?php
/**
 * TempTest ONLY: isolated disposable MariaDB 513 CRUD endpoint.
 *
 * Staged source, not yet deployed. Must be placed only inside public-temptest.
 * Server-side env TEMPTEST_513_BRIDGE_KEY must be set independently of GitHub.
 * The database password is provided via HTTPS by the GitHub Actions client;
 * it must never be written in this file or committed to the repository.
 */
declare(strict_types=1);
ini_set('display_errors', '0');
ini_set('log_errors', '0');
header('Cache-Control: no-store, private');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: no-referrer');
header("Content-Security-Policy: default-src 'none'; frame-ancestors 'none'");
header('Content-Type: application/json; charset=utf-8');

const TEMP513_DATABASE = 'dbs16231513';
const TEMP513_HOST = 'db5021656421.hosting-data.io';
const TEMP513_USER = 'dbu5597618';
const TEMP513_TABLE = 'temptest_chat_probe_513_v1';
const TEMP513_MARKER = 'TEMPTEST_513_FIXTURE_V1';

final class Temp513Error extends RuntimeException {}
function temp513_reply(int $status, array $data): void {
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR);
}
function temp513_block(string $reason): never {
    throw new Temp513Error($reason);
}
function temp513_fixture(PDO $pdo): array {
    $exists = $pdo->prepare('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=? AND table_name=?');
    $exists->execute([TEMP513_DATABASE, TEMP513_TABLE]);
    if ((int)$exists->fetchColumn() !== 1) {
        temp513_block('FIXTURE_NOT_CREATED');
    }
    $cols = $pdo->prepare('SELECT column_name, data_type FROM information_schema.columns WHERE table_schema=? AND table_name=? ORDER BY ordinal_position');
    $cols->execute([TEMP513_DATABASE, TEMP513_TABLE]);
    $actual = $cols->fetchAll(PDO::FETCH_NUM);
    $expected = [
        ['id', 'tinyint'],
        ['label', 'varchar'],
        ['state', 'varchar'],
        ['marker', 'varchar']
    ];
    if ($actual !== $expected) {
        temp513_block('FIXTURE_SCHEMA_MISMATCH');
    }
    $rows = $pdo->query('SELECT id,label,state,marker FROM ' . TEMP513_TABLE . ' ORDER BY id')->fetchAll(PDO::FETCH_ASSOC);
    if (count($rows) > 3) {
        temp513_block('FIXTURE_CONTENT_MISMATCH');
    }
    foreach ($rows as $row) {
        $id = (int)$row['id'];
        $labels = [1 => 'Alpha', 2 => 'Beta', 3 => 'Gamma'];
        if (!isset($labels[$id]) || $row['label'] !== $labels[$id] ||
            $row['marker'] !== TEMP513_MARKER ||
            !in_array($row['state'], ['CREATED', 'UPDATED'], true)) {
            temp513_block('FIXTURE_CONTENT_MISMATCH');
        }
    }
    return $rows;
}
function temp513_exists(PDO $pdo): bool {
    $query = $pdo->prepare('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=? AND table_name=?');
    $query->execute([TEMP513_DATABASE, TEMP513_TABLE]);
    return (int)$query->fetchColumn() === 1;
}
function temp513_execute(PDO $pdo, string $operation): array {
    if ($operation === 'status') {
        return ['read_only' => true, 'table_exists' => temp513_exists($pdo)];
    }
    if ($operation === 'create') {
        if (temp513_exists($pdo)) {
            temp513_block('FIXTURE_ALREADY_EXISTS');
        }
        $pdo->exec('CREATE TABLE ' . TEMP513_TABLE . ' (id TINYINT UNSIGNED NOT NULL PRIMARY KEY, label VARCHAR(30) NOT NULL, state VARCHAR(20) NOT NULL, marker VARCHAR(40) NOT NULL) ENGINE=InnoDB');
        $stmt = $pdo->prepare('INSERT INTO ' . TEMP513_TABLE . ' (id,label,state,marker) VALUES (?,?,?,?)');
        foreach ([[1, 'Alpha'], [2, 'Beta'], [3, 'Gamma']] as $fixture) {
            $stmt->execute([$fixture[0], $fixture[1], 'CREATED', TEMP513_MARKER]);
        }
    } elseif ($operation === 'read') {
        // Read-only operation. Validate fixture before returning rows.
    } elseif ($operation === 'update') {
        $rows = temp513_fixture($pdo);
        $found = false;
        foreach ($rows as $row) {
            if ((int)$row['id'] === 2 && $row['state'] === 'CREATED') {
                $found = true;
            }
        }
        if (!$found) {
            temp513_block('EXPECTED_ROW_MISSING');
        }
        $stmt = $pdo->prepare('UPDATE ' . TEMP513_TABLE . ' SET state=? WHERE id=? AND label=? AND state=? AND marker=?');
        $stmt->execute(['UPDATED', 2, 'Beta', 'CREATED', TEMP513_MARKER]);
        if ($stmt->rowCount() !== 1) {
            temp513_block('EXPECTED_ROW_MISSING');
        }
    } elseif ($operation === 'delete') {
        $rows = temp513_fixture($pdo);
        $found = false;
        foreach ($rows as $row) {
            if ((int)$row['id'] === 3 && $row['state'] === 'CREATED') {
                $found = true;
            }
        }
        if (!$found) {
            temp513_block('EXPECTED_ROW_MISSING');
        }
        $stmt = $pdo->prepare('DELETE FROM ' . TEMP513_TABLE . ' WHERE id=? AND label=? AND state=? AND marker=?');
        $stmt->execute([3, 'Gamma', 'CREATED', TEMP513_MARKER]);
        if ($stmt->rowCount() !== 1) {
            temp513_block('EXPECTED_ROW_MISSING');
        }
    } elseif ($operation === 'cleanup') {
        temp513_fixture($pdo); // Refuse to remove any non-matching table or schema.
        $pdo->exec('DROP TABLE ' . TEMP513_TABLE);
        return ['table_exists' => temp513_exists($pdo), 'cleaned' => !temp513_exists($pdo), 'row_count' => 0];
    } else {
        temp513_block('UNKNOWN_OPERATION');
    }
    $rows = temp513_fixture($pdo);
    $result = [];
    foreach ($rows as $r) {
        $result[] = ['id' => (int)$r['id'], 'label' => $r['label'], 'state' => $r['state']];
    }
    return ['table_exists' => true, 'row_count' => count($result), 'rows' => $result];
}
function temp513_main(): void {
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
        temp513_block('POST_REQUIRED');
    }
    if (!extension_loaded('pdo_mysql')) {
        temp513_block('PDO_MYSQL_UNAVAILABLE');
    }
    // Server-side shared key must be set securely in IONOS PHP environment.
    $key = getenv('TEMPTEST_513_BRIDGE_KEY');
    $provided = $_SERVER['HTTP_X_TEMPTEST_BRIDGE_TOKEN'] ?? '';
    if (!is_string($key) || strlen($key) < 32 ||
        !is_string($provided) || !hash_equals($key, $provided)) {
        temp513_block('AUTHORIZATION_REFUSED');
    }
    if (isset($_SERVER['CONTENT_LENGTH']) && (int)$_SERVER['CONTENT_LENGTH'] > 2048) {
        temp513_block('REQUEST_TOO_LARGE');
    }
    $raw = file_get_contents('php://input', false, null, 0, 2049);
    if (!is_string($raw) || strlen($raw) > 2048) {
        temp513_block('REQUEST_TOO_LARGE');
    }
    $request = json_decode($raw, true);
    if (!is_array($request) || array_keys($request) !== ['operation', 'password']) {
        temp513_block('INVALID_REQUEST');
    }
    $operation = $request['operation'];
    if (!is_string($operation) || !in_array($operation, ['status', 'create', 'read', 'update', 'delete', 'cleanup'], true)) {
        temp513_block('UNKNOWN_OPERATION');
    }
    if (!isset($request['password']) || !is_string($request['password']) ||
        $request['password'] === '' || strlen($request['password']) > 256) {
        temp513_block('MISSING_DATABASE_PASSWORD');
    }
    $password = $request['password'];
    unset($request, $raw);
    try {
        $pdo = new PDO('mysql:host=' . TEMP513_HOST . ';port=3306;dbname=' . TEMP513_DATABASE . ';charset=utf8mb4',
            TEMP513_USER, $password, [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_EMULATE_PREPARES => false,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_TIMEOUT => 8,
            ]);
    } catch (PDOException $exception) {
        temp513_block('DATABASE_CONNECTION_FAILED');
    }
    unset($password);
    $identity = $pdo->query('SELECT DATABASE() AS db, USER() AS login_user, CURRENT_USER() AS grant_user, VERSION() AS version')->fetch(PDO::FETCH_ASSOC);
    // MariaDB USER() = supplied login; CURRENT_USER() = account granting permissions.
    if (!$identity || $identity['db'] !== TEMP513_DATABASE ||
        explode('@', (string)$identity['login_user'], 2)[0] !== TEMP513_USER ||
        stripos((string)$identity['version'], 'MariaDB') === false) {
        temp513_block('DATABASE_IDENTITY_MISMATCH');
    }
    $details = temp513_execute($pdo, $operation);
    temp513_reply(200, [
        'status' => 'PASS',
        'database' => TEMP513_DATABASE,
        'operation' => $operation,
        'login_verified' => true,
        'grant_account_differs' => $identity['grant_user'] !== $identity['login_user'],
    ] + $details);
}
try {
    temp513_main();
} catch (Temp513Error $exception) {
    temp513_reply(403, ['status' => 'BLOCKED', 'reason' => $exception->getMessage()]);
} catch (Throwable $exception) {
    // Never disclose PHP exceptions, SQL, credential values, DSNs or stack traces.
    temp513_reply(500, ['status' => 'BLOCKED', 'reason' => 'TEMPTEST_OPERATION_FAILED']);
}

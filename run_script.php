<?php
header('Content-Type: application/json');

// Path to Python executable - adjust if necessary
// Assuming typical XAMPP Windows setup where python is in path or specific location
// Using the one found in previous steps: C:\Users\PROMAT1_W10\AppData\Local\Programs\Python\Python310\python.exe

$pythonPath = "python";
$scriptPath = "sync_bcv.py";

// Verify file existence
if (!file_exists($scriptPath)) {
    echo json_encode(['success' => false, 'error' => 'Script python no encontrado.']);
    exit;
}

// Determine Action
$action = isset($_REQUEST['action']) ? $_REQUEST['action'] : 'status';

if ($action === 'update') {
    $flag = "--update";
} else {
    $flag = "--status";
}

// Execute command
// 2>&1 redirects stderr to stdout so we capture debug prints too if needed, 
// but our script writes JSON to stdout and debug to stderr.
// We want clean JSON from stdout.

$command = "$pythonPath $scriptPath $flag";
$output = [];
$returnCode = 0;

exec($command, $output, $returnCode);

// output is an array of lines. The last line should be the JSON.
// Debug lines might be present if we didn't redirect well, but script puts check logs to stderr.
// exec captures stdout.

$fullOutput = implode("\n", $output);

// Find the last valid JSON object in the output (in case of warning prints)
// Simple approach: try to parse the whole string, if fails, try finding { ... }
$jsonStart = strpos($fullOutput, '{');
$jsonEnd = strrpos($fullOutput, '}');

if ($jsonStart !== false && $jsonEnd !== false) {
    $jsonStr = substr($fullOutput, $jsonStart, $jsonEnd - $jsonStart + 1);
    $data = json_decode($jsonStr, true);
    
    if ($data) {
        // Enforce success flag if missing in valid json
        if (!isset($data['success']) && isset($data['rate'])) {
             // status/dry-run might not have success explicit if legacy, but our new code adds it
             // pass through
        }
        echo json_encode(['success' => true, 'output' => $data]);
    } else {
         echo json_encode(['success' => false, 'error' => 'Error decodificando JSON de Python', 'raw_output' => $fullOutput]);
    }
} else {
    echo json_encode(['success' => false, 'error' => 'No se recibió respuesta válida del script', 'raw_output' => $fullOutput, 'code' => $returnCode]);
}
?>

# Start the FastAPI backend (Windows PowerShell)
# Run from the project root, or double-click.
#
# IMPORTANT: --host 127.0.0.1 is required (Vite proxy needs explicit IPv4)
# IMPORTANT: do NOT add --reload (uvicorn's watchfiles crashes in new PS windows on Windows)
#
# Mac / Linux equivalent:
#   python -m uvicorn api.main:app --host 127.0.0.1 --port 8000

$root = if ($PSScriptRoot) { $PSScriptRoot } else { $PWD.Path }
Set-Location "$root"

# Kill anything already holding port 8000
$listening = netstat -ano | Select-String ":8000\s.*LISTENING"
if ($listening) {
    $pid = ($listening -split '\s+')[-1]
    Write-Host "Stopping existing process on port 8000 (PID $pid)..."
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

python -m uvicorn api.main:app --host 127.0.0.1 --port 8000

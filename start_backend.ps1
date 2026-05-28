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
$listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    $portProcessIds = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($portProcessId in $portProcessIds) {
        Write-Host "Stopping existing process on port 8000 (PID $portProcessId)..."
        try {
            Stop-Process -Id $portProcessId -Force -ErrorAction Stop
        }
        catch {
            Write-Host "Stop-Process failed for PID $portProcessId, trying taskkill..." -ForegroundColor Yellow
            taskkill /PID $portProcessId /F | Out-Null
        }
    }
}

# Final guard: if 8000 is still in use, fail fast with owning process info.
$remaining = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($remaining) {
    $remainingInfo = $remaining | Select-Object LocalAddress, LocalPort, OwningProcess
    Write-Host "Port 8000 is still in use. Cannot start backend." -ForegroundColor Red
    $remainingInfo | Format-Table -AutoSize
    exit 1
}

python -m uvicorn api.main:app --host 127.0.0.1 --port 8000

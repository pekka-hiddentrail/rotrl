# Start the Vite dev server (Windows PowerShell)
# Run from the project root.
#
# Mac / Linux equivalent:
#   cd ui && npm run dev
#
# Then open http://localhost:5173

$root = if ($PSScriptRoot) { $PSScriptRoot } else { $PWD.Path }
Set-Location "$root"

# Kill anything already holding port 5173
$listeners = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    $portProcessIds = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($portProcessId in $portProcessIds) {
        Write-Host "Stopping existing process on port 5173 (PID $portProcessId)..."
        try {
            Stop-Process -Id $portProcessId -Force -ErrorAction Stop
        }
        catch {
            Write-Host "Stop-Process failed for PID $portProcessId, trying taskkill..." -ForegroundColor Yellow
            taskkill /F /T /PID $portProcessId | Out-Null
        }
    }
}

# Final guard: if 5173 is still in use, fail fast.
$remaining = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($remaining) {
    $remainingInfo = $remaining | Select-Object LocalAddress, LocalPort, OwningProcess
    Write-Host "Port 5173 is still in use. Cannot start UI." -ForegroundColor Red
    $remainingInfo | Format-Table -AutoSize
    exit 1
}

npm run dev

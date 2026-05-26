# Start the FastAPI backend (Windows PowerShell)
# Run from the project root.
#
# IMPORTANT: --host 127.0.0.1 is required (Vite proxy needs explicit IPv4)
# IMPORTANT: do NOT add --reload (uvicorn's watchfiles crashes in new PS windows)
#
# Mac / Linux equivalent:
#   python -m uvicorn api.main:app --host 127.0.0.1 --port 8000

Set-Location "$PSScriptRoot"
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000

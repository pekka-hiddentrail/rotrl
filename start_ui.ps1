# Start the Vite dev server (Windows PowerShell)
# Run from the project root.
#
# Mac / Linux equivalent:
#   cd ui && npm run dev
#
# Then open http://localhost:5173

$root = if ($PSScriptRoot) { $PSScriptRoot } else { $PWD.Path }
npm run dev

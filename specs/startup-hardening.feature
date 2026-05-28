# FEATURE — Startup Hardening (Windows)

**ID:** startup-hardening
**Status:** Approved
**Area:** Runtime / Tooling
**Tags:** @startup @windows @dev-tooling @process-cleanup

---

## Story

> As a **developer**,
> I want `dev.py` and the PowerShell helper scripts to detect and kill stale processes on the
> required ports before starting, and to cleanly terminate all child processes on exit,
> so that repeated `python dev.py` invocations never fail due to orphaned listeners.

On Windows, uvicorn `--reload` spawns a watcher parent and a worker child. A hard terminal
close or Ctrl-C at the wrong moment leaves both alive. The next `dev.py` run then crashes
because port 8000 is still held. This feature makes all startup paths self-healing.

---

## Background

- Given the developer is on Windows
- And the project root is in PATH / cwd
- And no manual steps are required beyond `python dev.py`

---

## Acceptance Criteria

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-001 — dev.py kills any existing listener on port 8000 before starting the API
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A stale uvicorn process is holding port 8000

```gherkin
Given a process is listening on port 8000
When  the developer runs "python dev.py"
Then  dev.py prints a message identifying the stale PID and kills it
And   the new uvicorn process starts successfully on port 8000
And   dev.py does not exit with an error
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-002 — dev.py kills any existing listener on port 5173 before starting the UI
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** A stale Vite process is holding port 5173

```gherkin
Given a process is listening on port 5173
When  the developer runs "python dev.py"
Then  dev.py prints a message identifying the stale PID and kills it
And   "npm run dev" starts successfully on port 5173
And   dev.py does not exit with an error
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-003 — Port cleanup kills the entire process tree, not just the top-level PID
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The stale listener has child processes (uvicorn --reload worker, npm child)

```gherkin
Given a uvicorn --reload process on port 8000 with an active worker child
When  dev.py performs port cleanup
Then  both the watcher parent and the worker child are terminated
And   port 8000 is free within 2 seconds
And   no zombie Python child processes remain
```

> **Implementation note:** Use `taskkill /F /T /PID <pid>` on Windows to kill the whole tree.
> Fall back to `psutil.Process(pid).kill()` if `taskkill` is unavailable (e.g. CI / Wine).

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-004 — Fast-fail with clear message if port is still occupied after kill attempt
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** The kill attempt fails (e.g. access denied, system process)

```gherkin
Given a process on port 8000 that cannot be killed
When  dev.py attempts cleanup and the port remains occupied
Then  dev.py prints a clear error naming the port and the remaining PID
And   dev.py exits with a non-zero exit code without attempting to start
```

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-005 — Ctrl-C from dev.py terminates both API and UI process trees cleanly
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Developer stops the session with Ctrl-C

```gherkin
Given dev.py has started both the API (uvicorn --reload) and the UI (npm run dev)
When  the developer presses Ctrl-C
Then  both the API and UI process trees are fully terminated
And   ports 8000 and 5173 are free immediately after exit
And   no orphaned Python or Node child processes remain
And   dev.py prints "Done." and exits with code 0
```

> **Implementation note:** Replace `proc.terminate() / proc.wait()` with
> `taskkill /F /T /PID <pid>` for each subprocess on Windows.
> `proc.terminate()` on Windows sends `SIGTERM` to the top-level process only;
> uvicorn's `--reload` worker and npm's Node child are not reached.

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-006 — start_backend.ps1 already handles port 8000 cleanup
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Developer uses the standalone PowerShell helper

```gherkin
Given a process is listening on port 8000
When  the developer runs ".\start_backend.ps1"
Then  the existing listener is killed (Stop-Process with taskkill fallback)
And   uvicorn starts successfully
And   if the port is still held after the kill, the script exits with code 1
```

> **Status:** Already implemented. No changes needed.

---

<!-- ─────────────────────────────────────────────────────────────────────── -->
### AC-007 — start_ui.ps1 kills any existing listener on port 5173
<!-- ─────────────────────────────────────────────────────────────────────── -->

**Scenario:** Developer uses the standalone PowerShell helper for the UI

```gherkin
Given a process is listening on port 5173
When  the developer runs ".\start_ui.ps1"
Then  the existing listener is killed
And   "npm run dev" starts successfully
And   if the port is still held after the kill, the script exits with code 1
```

---

## Out of Scope

- Non-Windows platforms (Mac/Linux don't have the `taskkill` / `Stop-Process` constraint)
- Detecting port conflicts for Ollama (port 11434) — separate concern
- Session crash recovery (separate TODO item — snapshot/restore)
- Automatic port reassignment — always fail fast so the developer knows something is wrong

---

## Notes

- Port detection: `subprocess.run(["netstat", "-ano"], capture_output=True, text=True)` on Windows,
  or the `socket` module (`sock.connect_ex(("127.0.0.1", port)) == 0`) to test occupancy.
- Tree kill helper: `subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], ...)`.
  Wrap in a helper `_kill_tree(pid)` shared between startup cleanup and shutdown.
- After a kill attempt, re-check the port with a short poll (up to 2 s, 100 ms interval)
  before declaring success or fast-failing.
- `psutil` is already a transitive dependency via uvicorn's `--reload` watchfiles; using it
  directly in `dev.py` is safe. However, the `taskkill` approach requires no extra imports
  and works when `psutil` is absent.

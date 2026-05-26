# Session Boot Flow

This document shows what happens today when launching a normal session in this repo.

## Current Startup Reality

The launcher currently enters the boot pipeline directly. There is no separate normal-session runtime path wired yet.

## Boot Flow (Plain Boxes - No Mermaid Needed)

```text
+-----------------------------------------------------------+
| Start: Run gm_launcher.py                                 |
+-----------------------------------------------------------+
                            |
                            v
+-----------------------------------------------------------+
| Check Ollama: GET /api/tags                               |
+-----------------------------------------------------------+
         | reachable                            | not reachable
         v                                      v
+-------------------------------+   +-----------------------------------+
| Create GMConfig and GMAgent   |   | Stop: launcher exits with error   |
+-------------------------------+   +-----------------------------------+
                |
                v
+-----------------------------------------------------------+
| boot_session(session_number)                              |
+-----------------------------------------------------------+
                |
                v
+-----------------------------------------------------------+
| boot_once(session_number)                                 |
+-----------------------------------------------------------+
                |
                v
+-----------------------------------------------------------+
| Load boot contexts                                        |
| - 7 System Authority files                                |
|   (includes 3 GM operating rules files)                   |
| - Optional PLAYER_CHARACTERS.md                           |
| - Optional PLAYER_LIMITS_AND_EXPECTATIONS.md              |
| - Optional SESSION_NOTES_LAST.md                          |
+-----------------------------------------------------------+
                |
                v
+-----------------------------------------------------------+
| Load .agents/GM/SESSION_BOOT_PROMPT.md                    |
+-----------------------------------------------------------+
                |
                v
+-----------------------------------------------------------+
| Inject placeholders with loaded context                   |
+-----------------------------------------------------------+
                |
                v
+-----------------------------------------------------------+
| LLM Call 1: /api/chat                                     |
| System: full rendered boot prompt                         |
| User: Begin Session Boot                                  |
+-----------------------------------------------------------+
                |
                v
+-----------------------------------------------------------+
| Receive opening narration                                 |
+-----------------------------------------------------------+
                |
                v
+-----------------------------------------------------------+
| Extract checklist from # Session Boot Output              |
+-----------------------------------------------------------+
                |
                v
+-----------------------------------------------------------+
| LLM Call 2: semantic audit                                |
| Output: strict JSON checks                                |
+-----------------------------------------------------------+
                |
                v
+-----------------------------------------------------------+
| Deterministic verification in Python                      |
| - loaded files checks                                     |
| - ending text checks                                      |
| - urgency/escalation checks                               |
+-----------------------------------------------------------+
         | all pass                              | any fail
         v                                       v
+-------------------------------+   +-----------------------------------+
| Print PASS report              |   | Stop: RuntimeError verification   |
+-------------------------------+   +-----------------------------------+
                |
                v
+-----------------------------------------------------------+
| Boot complete; control can move to gameplay loop          |
+-----------------------------------------------------------+
```

## Boot Flow (Mermaid, Optional)

```mermaid
flowchart TD
    A[Start: Run gm_launcher.py] --> B[Check Ollama: GET /api/tags]
    B -->|Not reachable| X1[Stop: launcher exits with error]
    B -->|Reachable| C[Create GMConfig and GMAgent]

    C --> D[boot_session(session_number)]
    D --> E[boot_once(session_number)]

    E --> F[Load boot contexts]
    F --> F1[Load 7 System Authority files\nincluding 3 GM operating rules files]
    F --> F2[Optionally load PLAYER_CHARACTERS.md]
    F --> F3[Optionally load PLAYER_LIMITS_AND_EXPECTATIONS.md]
    F --> F4[Optionally load SESSION_NOTES_LAST.md]

    F1 --> G[Load canonical template: .agents/GM/SESSION_BOOT_PROMPT.md]
    F2 --> G
    F3 --> G
    F4 --> G

    G --> H[Inject placeholders into template]
    H --> I[LLM Call 1: /api/chat\nSystem = full rendered boot prompt\nUser = Begin Session Boot]

    I --> J[Receive opening narration]
    J --> K[Extract checklist items from # Session Boot Output]

    K --> L[LLM Call 2: semantic audit\nReturn strict JSON checks]
    L --> M[Deterministic verification in Python\nloaded files + ending checks + urgency checks]

    M -->|Any check fails| X2[Stop: RuntimeError boot verification failed]
    M -->|All checks pass| N[Print PASS report]
    N --> O[Boot complete\nControl can move to gameplay loop]
```

## Step-by-Step Notes

1. Launcher starts and pings Ollama.
2. Boot path is invoked immediately.
3. Minimal boot contexts are loaded and merged.
4. Canonical boot template is loaded and placeholders are replaced.
5. First LLM call generates opening narration.
6. Checklist is read from the template file.
7. Second LLM call audits narration semantics and returns strict JSON.
8. Python verifier combines deterministic checks with audit results.
9. Boot hard-fails on any failed checklist item.
10. If all pass, boot is considered valid.

## Why Boot Feels Heavy

- Two LLM calls happen every startup.
- The first call sends a large rendered system prompt each time.
- Verification is fail-fast, so any mismatch restarts the startup cycle.

## Important File Path Assumption

Boot optional player files are currently searched under adventure_path root, while player identity files in this repo live under players. That means identity files may not be included unless mirrored or remapped.

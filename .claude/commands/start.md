---
description: Start a Job Hunter Agent session — read prior context, launch the desktop app, report status.
---

1. Read `state/session-log.md` (if it doesn't exist yet, say so and skip —
   don't create it until there's something real to log). This is the only
   memory of prior sessions; read it before doing anything else.
2. Read `config/preferences.json` and check `data/resume/` for a resume
   file. If either is missing, tell the user to set it up (via the desktop
   app's Setup tab) rather than guessing.
3. Launch the desktop app as a background/detached process appropriate for
   the current shell (e.g. `Start-Process` on Windows, `python app.py &` on
   macOS/Linux) — it must not block this conversation. Confirm it started.
4. Summarize for the user in a few lines: what the session log says happened
   last time (if anything), whether preferences/resume/Google connection are
   all set, and ask what they want to do next.

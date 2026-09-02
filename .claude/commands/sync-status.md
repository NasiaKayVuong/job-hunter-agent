---
description: Scan recent email for application status updates and, with confirmation, update the tracker.
---

1. Run `python tools/tracker.py list` to see currently tracked applications.
2. Run `python tools/gmail_scan.py scan --days 30` (read-only — see
   `CLAUDE.md`). Optionally narrow with `--company` per tracked company.
3. For each candidate email, match it against a tracked row by company/sender
   domain. Present matches to the user with the guessed status (never treat
   the guess as confirmed) and ask what the real new stage is, if any.
4. Only for rows the user confirms, run `python tools/tracker.py update-stage
   --row N --stage "..."`.
5. Also run `python tools/gcal.py list --days 30` and mention any upcoming
   interviews so the user has the full picture in one place.

---
description: Scan recent email for application status updates and new opportunities; with confirmation, update the tracker and Listings.
---

1. Run `python tools/tracker.py list` and `python tools/listings.py list` to
   see what's already tracked/listed.
2. Run `python tools/gmail_scan.py scan --days 30` (read-only — see
   `CLAUDE.md`). Optionally narrow with `--company` per tracked company.
3. For each candidate email, read it and decide which kind it is:
   - **Status update on an existing application** — match it against a
     tracked row by company/sender domain. Present matches to the user with
     the guessed status (never treat the guess as confirmed) and ask what
     the real new stage is, if any. Only for rows the user confirms, run
     `python tools/tracker.py update-stage --row N --stage "..."`.
   - **A new opportunity** (recruiter outreach, a role pitched directly,
     etc.) — see `CLAUDE.md`'s "New opportunities found in email": dedup,
     filter, and if it survives, `python tools/listings.py add` with
     `--source "Email (recruiter outreach)"` or similar, then tell the user.
4. Also run `python tools/gcal.py list --days 30` and mention any upcoming
   interviews so the user has the full picture in one place.

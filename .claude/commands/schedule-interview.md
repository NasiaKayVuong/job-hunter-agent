---
description: Create a calendar event for a scheduled interview and log it in the tracker.
---

Ask the user for whatever you don't already have: company, role, round/stage
(e.g. "Phone Screen", "Onsite"), date, start time, end time (default 1 hour if
unstated), and timezone if ambiguous.

Then:

1. Create the event: `python tools/gcal.py create --summary "Interview:
   <Company> — <Round>" --start <ISO8601> --end <ISO8601>`. Never add
   attendees — the tool has no such option.
2. If this company/role is already in the tracker, update its stage:
   `python tools/tracker.py update-stage --row N --stage "<Round>"`. If it
   isn't tracked yet, ask the user whether to add it now.
3. Confirm back to the user with the event's `html_link` from the tool output.

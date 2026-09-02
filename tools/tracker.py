#!/usr/bin/env python3
"""Application tracker, backed by a Google Sheet.

Columns (in order):
  date_applied, company, title, job_url, source, location, job_type,
  resume_version, cover_letter_version, skill_match, current_stage,
  stage_history, notes

- source: the job platform/site actually applied on (LinkedIn, Indeed, the
  company's own career site, etc.)
- job_type: remote / hybrid / onsite
- resume_version / cover_letter_version: filename or identifier of the
  tailored materials used (see applications/<company>-<role>/)
- skill_match: a rough JD-to-resume match assessment (e.g. "8/10" or "80%"
  plus a short reason) — this is Claude's judgment call at apply time, not a
  verified score, and should be read as a rough signal, not ground truth.
- current_stage: Applied / Phone Screen / Technical / Onsite / Offer /
  Rejected / Withdrawn (free text — use whatever stages actually apply)
- stage_history: a running log, e.g. "Applied 2026-09-02; Phone Screen
  2026-09-10", appended to (never overwritten) as the round progresses

The first run creates a new Sheet (via the Sheets API), files it inside a
"Job Tracker" folder in the user's Drive (created if needed — see
tools/drive.py ensure_folders(), which also makes the "Resumes" and
"Cover Letters" subfolders drafts get saved into), and saves the Sheet's ID to
config/tracker.json (gitignored, since the ID + its contents are personal).
Every other run reads that file to know which Sheet to use.

Usage:
  python tools/tracker.py add --company "..." --title "..." [--job-url ...]
      [--source ...] [--location ...] [--job-type ...] [--resume-version ...]
      [--cover-letter-version ...] [--skill-match ...] [--stage "Applied"]
      [--notes "..."]
  python tools/tracker.py update-stage --row N --stage "Phone Screen" [--date YYYY-MM-DD]
  python tools/tracker.py list
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from googleapiclient.discovery import build  # noqa: E402

from auth.google_auth import get_credentials  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "tracker.json"

HEADER = [
    "date_applied",
    "company",
    "title",
    "job_url",
    "source",
    "location",
    "job_type",
    "resume_version",
    "cover_letter_version",
    "skill_match",
    "current_stage",
    "stage_history",
    "notes",
]

SHEET_TITLE = "Job Hunter Agent — Application Tracker"
DATA_RANGE = "A2:M"  # everything below the header


def _sheets():
    return build("sheets", "v4", credentials=get_credentials())


def _load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _load_sheet_id():
    return _load_config().get("sheet_id")


def _save_sheet_id(sheet_id):
    config = _load_config()
    config["sheet_id"] = sheet_id
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def ensure_sheet():
    """Create the tracker Sheet on first use, inside the Job Tracker Drive
    folder (see tools/drive.py ensure_folders()). Cached thereafter."""
    sheet_id = _load_sheet_id()
    if sheet_id:
        return sheet_id

    from tools.drive import ensure_folders  # local import: avoids a hard
    from tools.drive import _service as _drive_service  # dependency for callers that only need read_all()/add_application()

    service = _sheets()
    spreadsheet = (
        service.spreadsheets()
        .create(body={"properties": {"title": SHEET_TITLE}})
        .execute()
    )
    sheet_id = spreadsheet["spreadsheetId"]
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="A1:M1",
        valueInputOption="RAW",
        body={"values": [HEADER]},
    ).execute()

    # Move it out of Drive root and into Job Tracker/.
    folder_id = ensure_folders()["job_tracker_folder_id"]
    drive_service = _drive_service()
    existing = drive_service.files().get(fileId=sheet_id, fields="parents").execute()
    previous_parents = ",".join(existing.get("parents", []))
    drive_service.files().update(
        fileId=sheet_id,
        addParents=folder_id,
        removeParents=previous_parents,
        fields="id, parents",
    ).execute()

    _save_sheet_id(sheet_id)
    return sheet_id


def add_application(row):
    sheet_id = ensure_sheet()
    values = [[row.get(col, "") for col in HEADER]]
    _sheets().spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range="A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()
    return row


def read_all():
    sheet_id = ensure_sheet()
    result = (
        _sheets()
        .spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=DATA_RANGE)
        .execute()
    )
    rows = result.get("values", [])
    out = []
    for i, r in enumerate(rows, start=2):  # row 1 is the header
        padded = r + [""] * (len(HEADER) - len(r))
        out.append({"row": i, **dict(zip(HEADER, padded))})
    return out


def update_stage(row_number, new_stage, on_date=None):
    on_date = on_date or date.today().isoformat()
    sheet_id = ensure_sheet()
    service = _sheets()

    current = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=f"A{row_number}:M{row_number}")
        .execute()
        .get("values", [[]])
    )
    existing = current[0] if current else []
    existing += [""] * (len(HEADER) - len(existing))
    history = existing[HEADER.index("stage_history")]
    entry = f"{new_stage} {on_date}"
    history = f"{history}; {entry}" if history else entry

    existing[HEADER.index("current_stage")] = new_stage
    existing[HEADER.index("stage_history")] = history

    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"A{row_number}:M{row_number}",
        valueInputOption="USER_ENTERED",
        body={"values": [existing]},
    ).execute()
    return {"row": row_number, "current_stage": new_stage, "stage_history": history}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add a new tracked application")
    p_add.add_argument("--company", required=True)
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--job-url", default="")
    p_add.add_argument("--source", default="")
    p_add.add_argument("--location", default="")
    p_add.add_argument("--job-type", default="", help="remote / hybrid / onsite")
    p_add.add_argument("--resume-version", default="")
    p_add.add_argument("--cover-letter-version", default="")
    p_add.add_argument("--skill-match", default="")
    p_add.add_argument("--stage", default="Applied")
    p_add.add_argument("--notes", default="")
    p_add.add_argument("--date-applied", default=date.today().isoformat())

    p_update = sub.add_parser("update-stage", help="Append a new stage to an existing row")
    p_update.add_argument("--row", type=int, required=True, help="Sheet row number (from `list`)")
    p_update.add_argument("--stage", required=True)
    p_update.add_argument("--date", default=None)

    sub.add_parser("list", help="Print all tracked applications as JSON")

    args = parser.parse_args()

    if args.command == "add":
        result = add_application(
            {
                "date_applied": args.date_applied,
                "company": args.company,
                "title": args.title,
                "job_url": args.job_url,
                "source": args.source,
                "location": args.location,
                "job_type": args.job_type,
                "resume_version": args.resume_version,
                "cover_letter_version": args.cover_letter_version,
                "skill_match": args.skill_match,
                "current_stage": args.stage,
                "stage_history": f"{args.stage} {args.date_applied}",
                "notes": args.notes,
            }
        )
    elif args.command == "update-stage":
        result = update_stage(args.row, args.stage, args.date)
    elif args.command == "list":
        result = read_all()
    else:
        parser.error("unknown command")
        return

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

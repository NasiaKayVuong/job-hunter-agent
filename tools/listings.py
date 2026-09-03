#!/usr/bin/env python3
"""Candidate job listings — a shortlist, not an application record.

Backed by a second tab ("Listings") inside the same Google Sheet as the
application tracker (tools/tracker.py) — same spreadsheet, one more worksheet.

Columns:
  date_found, company, title, location, job_type, comp_range, source, url,
  match_notes, status

- status: New / Interested / Passed / Applied — set by the user (via the
  desktop app's Listings tab) or by Claude when a listing becomes a real
  application (see tools/tracker.py add_application(), a separate record).
- match_notes: why it matched the resume/preferences — Claude's rationale
  at search time, not a verified score.

This is where Claude records what a search turned up, before the user
decides what to pursue. It is not the tracker — nothing here means an
application was actually submitted.

Usage:
  python tools/listings.py add --company "..." --title "..." [--location ...]
      [--job-type ...] [--comp-range ...] [--source ...] [--url ...]
      [--match-notes ...] [--status "New"]
  python tools/listings.py update-status --row N --status "Interested"
  python tools/listings.py list
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from googleapiclient.discovery import build  # noqa: E402

from auth.google_auth import get_credentials  # noqa: E402
from tools.tracker import ensure_sheet  # noqa: E402  reuse the same spreadsheet

TAB_TITLE = "Listings"
HEADER = [
    "date_found",
    "company",
    "title",
    "location",
    "job_type",
    "comp_range",
    "source",
    "url",
    "match_notes",
    "status",
]
DATA_RANGE = f"{TAB_TITLE}!A2:J"
STATUS_COL_LETTER = chr(ord("A") + HEADER.index("status"))


def _sheets():
    return build("sheets", "v4", credentials=get_credentials())


def ensure_listings_tab():
    """Create the Listings tab in the tracker spreadsheet if it doesn't
    already exist. Idempotent. Returns the spreadsheet ID (same one
    tools/tracker.py uses)."""
    spreadsheet_id = ensure_sheet()
    service = _sheets()
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id, fields="sheets.properties.title").execute()
    titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
    if TAB_TITLE not in titles:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": TAB_TITLE}}}]},
        ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{TAB_TITLE}!A1:J1",
            valueInputOption="RAW",
            body={"values": [HEADER]},
        ).execute()
    return spreadsheet_id


def add_listing(row):
    spreadsheet_id = ensure_listings_tab()
    row.setdefault("status", "New")
    values = [[row.get(col, "") for col in HEADER]]
    _sheets().spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{TAB_TITLE}!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()
    return row


def list_listings():
    spreadsheet_id = ensure_listings_tab()
    result = (
        _sheets()
        .spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=DATA_RANGE)
        .execute()
    )
    rows = result.get("values", [])
    out = []
    for i, r in enumerate(rows, start=2):  # row 1 is the header
        padded = r + [""] * (len(HEADER) - len(r))
        out.append({"row": i, **dict(zip(HEADER, padded))})
    return out


def update_status(row_number, status):
    spreadsheet_id = ensure_listings_tab()
    _sheets().spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{TAB_TITLE}!{STATUS_COL_LETTER}{row_number}",
        valueInputOption="USER_ENTERED",
        body={"values": [[status]]},
    ).execute()
    return {"row": row_number, "status": status}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Record a candidate listing found during search")
    p_add.add_argument("--company", required=True)
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--location", default="")
    p_add.add_argument("--job-type", default="")
    p_add.add_argument("--comp-range", default="")
    p_add.add_argument("--source", default="")
    p_add.add_argument("--url", default="")
    p_add.add_argument("--match-notes", default="")
    p_add.add_argument("--status", default="New")
    p_add.add_argument("--date-found", default=date.today().isoformat())

    p_update = sub.add_parser("update-status", help="Change a listing's status")
    p_update.add_argument("--row", type=int, required=True)
    p_update.add_argument("--status", required=True)

    sub.add_parser("list", help="Print all candidate listings as JSON")

    args = parser.parse_args()

    if args.command == "add":
        result = add_listing(
            {
                "date_found": args.date_found,
                "company": args.company,
                "title": args.title,
                "location": args.location,
                "job_type": args.job_type,
                "comp_range": args.comp_range,
                "source": args.source,
                "url": args.url,
                "match_notes": args.match_notes,
                "status": args.status,
            }
        )
    elif args.command == "update-status":
        result = update_status(args.row, args.status)
    elif args.command == "list":
        result = list_listings()
    else:
        parser.error("unknown command")
        return

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

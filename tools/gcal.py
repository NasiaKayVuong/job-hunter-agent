#!/usr/bin/env python3
"""Google Calendar CLI for tracking interviews.

Deliberately narrow: creates and lists events on the user's own primary
calendar only. There is no --attendees flag and the event body never
includes an "attendees" field — this tool cannot send a calendar invite to
anyone, by construction, not just by convention. If you want to invite an
interviewer or recruiter, do that yourself in Google Calendar directly.

Usage:
  python tools/gcal.py create --summary "..." --start ISO8601 --end ISO8601 \
      [--description "..."] [--location "..."]
  python tools/gcal.py list [--days 30]

Both subcommands print JSON to stdout.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from googleapiclient.discovery import build  # noqa: E402

from auth.google_auth import get_credentials  # noqa: E402


def _service():
    return build("calendar", "v3", credentials=get_credentials())


def create_event(summary, start, end, description="", location=""):
    body = {
        "summary": summary,
        "description": description,
        "location": location,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
        "reminders": {"useDefault": True},
        # No "attendees" key — see module docstring. Do not add one.
    }
    event = _service().events().insert(calendarId="primary", body=body).execute()
    return {
        "event_id": event["id"],
        "summary": event.get("summary"),
        "start": event["start"].get("dateTime"),
        "end": event["end"].get("dateTime"),
        "html_link": event.get("htmlLink"),
    }


def list_upcoming(days=30):
    now = datetime.now(timezone.utc)
    until = now + timedelta(days=days)
    result = (
        _service()
        .events()
        .list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=until.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return [
        {
            "event_id": e["id"],
            "summary": e.get("summary"),
            "start": e["start"].get("dateTime", e["start"].get("date")),
            "end": e["end"].get("dateTime", e["end"].get("date")),
            "html_link": e.get("htmlLink"),
        }
        for e in result.get("items", [])
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create", help="Create an event on the primary calendar")
    p_create.add_argument("--summary", required=True)
    p_create.add_argument("--start", required=True, help="ISO 8601, e.g. 2026-09-10T14:00:00-07:00")
    p_create.add_argument("--end", required=True, help="ISO 8601")
    p_create.add_argument("--description", default="")
    p_create.add_argument("--location", default="")

    p_list = sub.add_parser("list", help="List upcoming events")
    p_list.add_argument("--days", type=int, default=30)

    args = parser.parse_args()

    if args.command == "create":
        result = create_event(args.summary, args.start, args.end, args.description, args.location)
    elif args.command == "list":
        result = list_upcoming(args.days)
    else:
        parser.error("unknown command")
        return

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

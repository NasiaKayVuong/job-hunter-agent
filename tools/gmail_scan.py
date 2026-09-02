#!/usr/bin/env python3
"""Read-only Gmail scan for application status updates.

Uses the gmail.readonly scope only — there is no send/reply/modify code path
anywhere in this file or anywhere else in this repo. It searches for likely
interview/rejection/offer emails and prints candidates with a *guessed*
status for a human (or Claude, with the user watching) to confirm before
anything gets written to the tracker via tools/tracker.py update-stage.
Never treat the guess as ground truth — subject-line keyword matching is
approximate and will misclassify some emails.

Usage:
  python tools/gmail_scan.py scan [--days 30] [--company "Acme"]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from googleapiclient.discovery import build  # noqa: E402

from auth.google_auth import get_credentials  # noqa: E402

REJECTION_HINTS = [
    "unfortunately", "regret to inform", "not moving forward",
    "other candidates", "will not be moving forward", "decided not to proceed",
]
INTERVIEW_HINTS = [
    "interview", "schedule a call", "next steps", "phone screen",
    "would like to speak", "chat with", "meet the team",
]
OFFER_HINTS = ["offer", "excited to extend", "pleased to offer"]


def _service():
    return build("gmail", "v1", credentials=get_credentials())


def _guess_status(subject, snippet):
    text = f"{subject} {snippet}".lower()
    if any(h in text for h in OFFER_HINTS):
        return "possible offer"
    if any(h in text for h in REJECTION_HINTS):
        return "possible rejection"
    if any(h in text for h in INTERVIEW_HINTS):
        return "possible interview/next step"
    return "unclassified"


def scan(days=30, company=None):
    query_parts = [f"newer_than:{days}d", "(interview OR offer OR unfortunately OR \"next steps\")"]
    if company:
        query_parts.append(f'"{company}"')
    query = " ".join(query_parts)

    service = _service()
    results = service.users().messages().list(userId="me", q=query, maxResults=25).execute()
    candidates = []
    for msg in results.get("messages", []):
        full = (
            service.users()
            .messages()
            .get(userId="me", id=msg["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"])
            .execute()
        )
        headers = {h["name"]: h["value"] for h in full.get("payload", {}).get("headers", [])}
        snippet = full.get("snippet", "")
        candidates.append(
            {
                "message_id": msg["id"],
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "snippet": snippet,
                "guessed_status": _guess_status(headers.get("Subject", ""), snippet),
            }
        )
    return candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Search recent mail for likely application status updates")
    p_scan.add_argument("--days", type=int, default=30)
    p_scan.add_argument("--company", default=None, help="Narrow the search to one company/sender")

    args = parser.parse_args()
    if args.command == "scan":
        result = scan(args.days, args.company)
    else:
        parser.error("unknown command")
        return

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Create Gmail drafts, optionally with a file attached. Never sends anything.

Uses the gmail.compose scope, which allows creating and editing drafts —
NOT sending. There is no send-capable code path anywhere in this file, or
anywhere else in this repo: no call to users().messages().send(), no
users().drafts().send(). If you're looking for a way to send a drafted
reply automatically, it doesn't exist here on purpose — the user opens
Gmail and sends it themselves. Same shape as the existing Gmail Hand's
"no send tool exists in this server at all" guarantee.

Usage:
  python tools/gmail_draft.py create --to a@b.com --subject "..." \
      --body-file path/to/body.txt [--attach path/to/resume.pdf ...]
"""

import argparse
import base64
import json
import mimetypes
import sys
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from googleapiclient.discovery import build  # noqa: E402

from auth.google_auth import get_credentials  # noqa: E402


def _service():
    return build("gmail", "v1", credentials=get_credentials())


def create_draft(to, subject, body_text, attachments=None):
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body_text)

    for path in attachments or []:
        path = Path(path)
        mime_type, _ = mimetypes.guess_type(str(path))
        maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
        msg.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)

    encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = _service().users().drafts().create(userId="me", body={"message": {"raw": encoded}}).execute()
    return {
        "draft_id": draft["id"],
        "message_id": draft["message"]["id"],
        "to": to,
        "subject": subject,
        "attachments": [Path(p).name for p in (attachments or [])],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create", help="Create a Gmail draft (never sends)")
    p_create.add_argument("--to", required=True)
    p_create.add_argument("--subject", required=True)
    p_create.add_argument("--body-file", required=True, help="Path to a text file with the draft body")
    p_create.add_argument("--attach", action="append", default=[], help="File to attach; repeat for multiple")

    args = parser.parse_args()

    if args.command == "create":
        body_text = Path(args.body_file).read_text(encoding="utf-8")
        result = create_draft(args.to, args.subject, body_text, args.attach)
    else:
        parser.error("unknown command")
        return

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

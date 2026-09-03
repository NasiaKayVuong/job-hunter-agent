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
      [--reply-to-message-id GMAIL_MESSAGE_ID]

--reply-to-message-id makes this a proper threaded reply (same Gmail thread,
correct In-Reply-To/References headers, subject prefixed "Re: " if it isn't
already) instead of a standalone draft that happens to mention the same
topic. Pass the message_id from a tools/gmail_scan.py result.
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


def create_draft(to, subject, body_text, attachments=None, reply_to_message_id=None):
    msg = EmailMessage()
    msg["To"] = to
    thread_id = None

    if reply_to_message_id:
        service = _service()
        original = (
            service.users()
            .messages()
            .get(userId="me", id=reply_to_message_id, format="metadata", metadataHeaders=["Message-ID", "Subject"])
            .execute()
        )
        thread_id = original.get("threadId")
        headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
        original_msg_id = headers.get("Message-ID")
        if original_msg_id:
            msg["In-Reply-To"] = original_msg_id
            msg["References"] = original_msg_id
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

    msg["Subject"] = subject
    msg.set_content(body_text)

    for path in attachments or []:
        path = Path(path)
        mime_type, _ = mimetypes.guess_type(str(path))
        maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
        msg.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)

    encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    message_body = {"raw": encoded}
    if thread_id:
        message_body["threadId"] = thread_id

    draft = _service().users().drafts().create(userId="me", body={"message": message_body}).execute()
    return {
        "draft_id": draft["id"],
        "message_id": draft["message"]["id"],
        "thread_id": thread_id,
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
    p_create.add_argument("--reply-to-message-id", default=None, help="Gmail message ID to thread this reply under")

    args = parser.parse_args()

    if args.command == "create":
        body_text = Path(args.body_file).read_text(encoding="utf-8")
        result = create_draft(args.to, args.subject, body_text, args.attach, args.reply_to_message_id)
    else:
        parser.error("unknown command")
        return

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

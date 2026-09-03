"""Shared Google OAuth helper for Calendar, Gmail (read + draft-only), Sheets, and Drive.

One installed-app OAuth client, one token, one scope set. Run this file
directly the first time to do the interactive browser consent; after that,
`get_credentials()` silently refreshes the saved token. `connection_status()`
checks whether that's already true without ever opening a browser or blocking
— used by the desktop app's Connections tab.

Setup (see README.md for the full walkthrough):
  1. Create a Google Cloud project, enable the Calendar, Gmail, Sheets, and
     Drive APIs, and create an OAuth Client ID of type "Desktop app".
  2. Download its JSON and save it as data/google/client_secret.json
     (gitignored — never commit this file).
  3. Run: python auth/google_auth.py
"""

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

REPO_ROOT = Path(__file__).resolve().parent.parent
GOOGLE_DIR = REPO_ROOT / "data" / "google"
CLIENT_SECRET_PATH = GOOGLE_DIR / "client_secret.json"
TOKEN_PATH = GOOGLE_DIR / "token.json"

# Deliberately minimal. gmail.compose allows creating/editing DRAFTS only --
# it does NOT allow sending on its own, and there is no send-capable code
# path anywhere in this repo (see tools/gmail_draft.py's own docstring).
# Drive access is read-only for browsing/importing plus "create files this
# app creates" for saving drafts — never broad read/write over the whole Drive.
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
]


def connection_status():
    """Non-interactive check — never opens a browser, never blocks."""
    if not CLIENT_SECRET_PATH.exists():
        return {"client_secret_present": False, "connected": False}
    if not TOKEN_PATH.exists():
        return {"client_secret_present": True, "connected": False}
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    except (ValueError, OSError):
        return {"client_secret_present": True, "connected": False}
    connected = bool(creds and (creds.valid or (creds.expired and creds.refresh_token)))
    return {"client_secret_present": True, "connected": connected}


def get_credentials():
    if not CLIENT_SECRET_PATH.exists():
        raise FileNotFoundError(
            f"Missing {CLIENT_SECRET_PATH}. Follow the Google setup steps in "
            "README.md, then save your OAuth client JSON there."
        )

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        GOOGLE_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    return creds


if __name__ == "__main__":
    get_credentials()
    print(f"Authorized. Token saved to {TOKEN_PATH}.")
    print("Scopes granted: calendar, gmail.readonly, gmail.compose, spreadsheets, drive.readonly, drive.file.")

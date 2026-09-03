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

import urllib.parse
import webbrowser
import wsgiref.simple_server
import wsgiref.util
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


_SUCCESS_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Job Hunter Agent — Connected</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
          background: #f7f7f5; color: #1c1c1e; display: flex; align-items: center;
          justify-content: center; height: 100vh; margin: 0; }}
  .card {{ background: #fff; border: 1px solid #e2e2e0; border-radius: 12px;
           padding: 2rem 2.5rem; text-align: center; max-width: 420px; }}
  h1 {{ font-size: 1.2rem; margin: 0 0 0.5rem; }}
  p {{ color: #6b6b70; font-size: 0.9rem; }}
  a.btn {{ display: inline-block; margin-top: 1rem; padding: 0.65rem 1.2rem;
           background: #3d5a80; color: #fff; text-decoration: none; border-radius: 8px;
           font-weight: 600; font-size: 0.9rem; }}
  .countdown {{ font-size: 0.8rem; color: #9a9ca1; margin-top: 1rem; }}
</style></head>
<body>
  <div class="card">
    <h1>&#x2713; Google account connected</h1>
    <p>You can return to Job Hunter Agent now.</p>
    <a class="btn" href="{dashboard_url}">Return to Job Hunter Agent</a>
    <p class="countdown" id="countdown">This tab will try to close in 5&hellip;</p>
  </div>
  <script>
    var n = 5;
    var el = document.getElementById("countdown");
    var timer = setInterval(function () {{
      n -= 1;
      if (n > 0) {{
        el.textContent = "This tab will try to close in " + n + "…";
      }} else {{
        clearInterval(timer);
        window.close();
        // Most browsers refuse to close a tab that wasn't opened by script
        // (this one was opened by the OS, not window.open()) — if we're
        // still here a moment later, stop pretending it's about to close.
        setTimeout(function () {{ el.textContent = "You can close this tab now."; }}, 300);
      }}
    }}, 1000);
  </script>
</body></html>"""

_ERROR_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Job Hunter Agent — Connection failed</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
          background: #f7f7f5; color: #1c1c1e; display: flex; align-items: center;
          justify-content: center; height: 100vh; margin: 0; }}
  .card {{ background: #fff; border: 1px solid #e2e2e0; border-radius: 12px;
           padding: 2rem 2.5rem; text-align: center; max-width: 420px; }}
  h1 {{ font-size: 1.2rem; margin: 0 0 0.5rem; color: #a3312a; }}
  p {{ color: #6b6b70; font-size: 0.9rem; }}
  a.btn {{ display: inline-block; margin-top: 1rem; padding: 0.65rem 1.2rem;
           background: #3d5a80; color: #fff; text-decoration: none; border-radius: 8px;
           font-weight: 600; font-size: 0.9rem; }}
</style></head>
<body>
  <div class="card">
    <h1>Connection failed</h1>
    <p>{error}</p>
    <a class="btn" href="{dashboard_url}">Return to Job Hunter Agent</a>
  </div>
</body></html>"""


class _AuthRedirectApp:
    """Minimal WSGI app for the local OAuth callback.

    google_auth_oauthlib's own InstalledAppFlow.run_local_server() serves its
    success/error page as Content-Type: text/plain, so no HTML it's given —
    button, countdown, auto-close script, any of it — can ever render. This
    reimplements just the local-redirect-catching piece with a real
    text/html response instead; everything else (redirect_uri construction,
    authorization_url/fetch_token calls) matches what run_local_server does.
    """

    def __init__(self, dashboard_url):
        self.last_request_uri = None
        self._dashboard_url = dashboard_url

    def __call__(self, environ, start_response):
        self.last_request_uri = wsgiref.util.request_uri(environ)
        query = urllib.parse.parse_qs(environ.get("QUERY_STRING", ""))
        error = query.get("error", [None])[0]
        if error:
            body = _ERROR_HTML.format(error=error, dashboard_url=self._dashboard_url)
        else:
            body = _SUCCESS_HTML.format(dashboard_url=self._dashboard_url)
        encoded = body.encode("utf-8")
        start_response(
            "200 OK",
            [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(encoded)))],
        )
        return [encoded]


def _run_local_auth_flow(flow):
    from ui.server import PORT

    dashboard_url = f"http://localhost:{PORT}/?tab=connections"
    wsgi_app = _AuthRedirectApp(dashboard_url)
    local_server = wsgiref.simple_server.make_server("localhost", 0, wsgi_app)

    try:
        flow.redirect_uri = f"http://localhost:{local_server.server_port}/"
        auth_url, _ = flow.authorization_url()
        webbrowser.open(auth_url, new=1, autoraise=True)
        local_server.handle_request()

        query = urllib.parse.parse_qs(urllib.parse.urlparse(wsgi_app.last_request_uri).query)
        error = query.get("error", [None])[0]
        if error:
            raise RuntimeError(f"Google sign-in was not completed: {error}")

        # oauthlib insists the authorization response look like https, even
        # though this is really a local http callback — same substitution
        # run_local_server() does internally.
        authorization_response = wsgi_app.last_request_uri.replace("http", "https")
        flow.fetch_token(authorization_response=authorization_response)
    finally:
        local_server.server_close()

    return flow.credentials


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
            creds = _run_local_auth_flow(flow)
        GOOGLE_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    return creds


if __name__ == "__main__":
    get_credentials()
    print(f"Authorized. Token saved to {TOKEN_PATH}.")
    print("Scopes granted: calendar, gmail.readonly, gmail.compose, spreadsheets, drive.readonly, drive.file.")

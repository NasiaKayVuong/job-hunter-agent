#!/usr/bin/env python3
"""Local server backing the Job Hunter Agent dashboard.

Core (Setup tab: preferences + resume) needs no external packages — stdlib
only, matching the rest of this file's original design. The Connections/
Applications/Calendar tabs talk to Google APIs and need the packages in
requirements.txt; if those aren't installed, those endpoints return a clear
JSON error instead of crashing the server, so the Setup tab keeps working
either way.

Run standalone (opens in your normal browser):
    python ui/server.py
Run as a desktop window instead:
    python app.py
"""

import base64
import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
UI_DIR = Path(__file__).resolve().parent

# Running this file directly (`python ui/server.py`) puts ui/ on sys.path,
# not the repo root — without this, `from auth...` / `from tools...` below
# fail with ModuleNotFoundError regardless of whether requirements.txt is
# installed, and get misreported as "not installed".
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
CONFIG_DIR = REPO_ROOT / "config"
RESUME_DIR = REPO_ROOT / "data" / "resume"
PREFS_PATH = CONFIG_DIR / "preferences.json"

PORT = 8787

STATIC_FILES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/style.css": "style.css",
    "/app.js": "app.js",
}


def current_resume_filename():
    if not RESUME_DIR.exists():
        return None
    files = [p for p in RESUME_DIR.iterdir() if p.is_file() and not p.name.startswith(".")]
    return files[0].name if files else None


def _google_unavailable_error():
    return {
        "error": "Google integration not installed or not set up. "
        "Run `pip install -r requirements.txt`, then see the Connections tab."
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep the terminal quiet; this is a local UI, not a server to monitor

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    # ---- GET ----

    def do_GET(self):
        if self.path == "/api/preferences":
            self._get_preferences()
            return
        if self.path == "/api/google/status":
            self._get_google_status()
            return
        if self.path.startswith("/api/applications"):
            self._get_applications()
            return
        if self.path.startswith("/api/calendar/upcoming"):
            self._get_calendar_upcoming()
            return
        if self.path == "/api/drive/resumes":
            self._get_drive_resumes()
            return

        rel = STATIC_FILES.get(self.path)
        if rel is None:
            self.send_error(404, "Not found")
            return
        file_path = UI_DIR / rel
        content_type, _ = mimetypes.guess_type(str(file_path))
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _get_preferences(self):
        prefs = None
        if PREFS_PATH.exists():
            try:
                prefs = json.loads(PREFS_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                prefs = None
        self._send_json(200, {
            "preferences": prefs,
            "resume_filename": current_resume_filename(),
        })

    def _get_google_status(self):
        try:
            from auth.google_auth import connection_status
        except ImportError:
            self._send_json(200, {"client_secret_present": False, "connected": False, "installed": False})
            return
        status = connection_status()
        status["installed"] = True
        self._send_json(200, status)

    def _get_applications(self):
        try:
            from tools.tracker import read_all
        except ImportError:
            self._send_json(200, _google_unavailable_error())
            return
        try:
            self._send_json(200, {"applications": read_all()})
        except Exception as e:  # Google API errors, not-yet-connected, etc.
            self._send_json(200, {"error": str(e)})

    def _get_calendar_upcoming(self):
        try:
            from tools.gcal import list_upcoming
        except ImportError:
            self._send_json(200, _google_unavailable_error())
            return
        try:
            self._send_json(200, {"events": list_upcoming(days=30)})
        except Exception as e:
            self._send_json(200, {"error": str(e)})

    def _get_drive_resumes(self):
        try:
            from tools.drive import list_candidate_resumes
        except ImportError:
            self._send_json(200, _google_unavailable_error())
            return
        try:
            self._send_json(200, {"files": list_candidate_resumes()})
        except Exception as e:
            self._send_json(200, {"error": str(e)})

    # ---- POST ----

    def do_POST(self):
        if self.path == "/api/save":
            self._post_save()
            return
        if self.path == "/api/google/connect":
            self._post_google_connect()
            return
        if self.path == "/api/drive/import-resume":
            self._post_drive_import_resume()
            return
        self.send_error(404, "Not found")

    def _post_save(self):
        try:
            payload = self._read_json_body()
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "Invalid JSON body"})
            return

        preferences = payload.get("preferences")
        if preferences is not None:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            PREFS_PATH.write_text(json.dumps(preferences, indent=2) + "\n", encoding="utf-8")

        resume = payload.get("resume")
        if resume:
            filename = resume.get("filename")
            data_b64 = resume.get("data_base64")
            if filename and data_b64:
                RESUME_DIR.mkdir(parents=True, exist_ok=True)
                for old in RESUME_DIR.iterdir():
                    if old.is_file() and not old.name.startswith("."):
                        old.unlink()
                safe_name = Path(filename).name
                (RESUME_DIR / safe_name).write_bytes(base64.b64decode(data_b64))

        self._send_json(200, {"ok": True})

    def _post_google_connect(self):
        try:
            from auth.google_auth import get_credentials
        except ImportError:
            self._send_json(200, _google_unavailable_error())
            return
        try:
            get_credentials()  # blocks this request until the browser consent completes
            self._send_json(200, {"ok": True})
        except Exception as e:
            self._send_json(200, {"error": str(e)})

    def _post_drive_import_resume(self):
        try:
            from tools.drive import import_resume
        except ImportError:
            self._send_json(200, _google_unavailable_error())
            return
        try:
            payload = self._read_json_body()
            file_id = payload.get("file_id")
            if not file_id:
                self._send_json(400, {"error": "Missing file_id"})
                return
            self._send_json(200, import_resume(file_id))
        except Exception as e:
            self._send_json(200, {"error": str(e)})


def create_server():
    return ThreadingHTTPServer(("127.0.0.1", PORT), Handler)


def main():
    server = create_server()
    print(f"Job Hunter Agent running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

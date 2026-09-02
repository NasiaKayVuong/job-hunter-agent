#!/usr/bin/env python3
"""Local-only UI for setting job-search preferences and uploading a resume.

No external dependencies (stdlib only). Binds to localhost only. Writes
config/preferences.json and data/resume/<file> in the repo root — both are
gitignored, so nothing here ever gets committed.
"""

import base64
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
UI_DIR = Path(__file__).resolve().parent
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


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep the terminal quiet; this is a local setup tool

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/preferences":
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

    def do_POST(self):
        if self.path != "/api/save":
            self.send_error(404, "Not found")
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
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
                # Only one resume on file at a time — remove prior uploads first.
                for old in RESUME_DIR.iterdir():
                    if old.is_file() and not old.name.startswith("."):
                        old.unlink()
                safe_name = Path(filename).name  # strip any path components
                (RESUME_DIR / safe_name).write_bytes(base64.b64decode(data_b64))

        self._send_json(200, {"ok": True})


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Job Hunter Agent setup UI running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

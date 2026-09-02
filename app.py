#!/usr/bin/env python3
"""Job Hunter Agent desktop app.

Starts the local dashboard server in a background thread and opens it in a
native window (via pywebview) instead of a browser tab. This is a viewer/
input surface only — setup, connection status, the applications tracker, and
upcoming interviews. All searching, drafting, and autofilling happens through
Claude Code (see CLAUDE.md), not this window.

Needs: pip install -r requirements.txt
Falls back to printing a browser URL if pywebview isn't installed.
"""

import sys
import threading

from ui.server import PORT, create_server


def main():
    server = create_server()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://localhost:{PORT}"

    try:
        import webview
    except ImportError:
        print("pywebview isn't installed (pip install -r requirements.txt).")
        print(f"Open this in your browser instead: {url}")
        try:
            thread.join()
        except KeyboardInterrupt:
            pass
        return

    webview.create_window("Job Hunter Agent", url, width=1100, height=800, min_size=(720, 560))
    webview.start()
    server.shutdown()


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()

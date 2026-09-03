#!/usr/bin/env python3
"""Job Hunter Agent desktop app.

Starts the local dashboard server in a background thread and opens it in a
native window (via pywebview) instead of a browser tab. This is a viewer/
input surface only — setup, connection status, the applications tracker, and
upcoming interviews. All searching, drafting, and autofilling happens through
Claude Code (see CLAUDE.md), not this window.

On first launch (Google OAuth not fully set up yet), a second, smaller
"guide" window opens on top of the main one, pointed straight at the
Connections tab, so a first-time user isn't left hunting for where to go.

Needs: pip install -r requirements.txt
Falls back to printing a browser URL if pywebview isn't installed.
"""

import sys
import threading

from ui.server import PORT, create_server


def _google_setup_incomplete():
    """True if there's a first-run OAuth step left to walk the user through.

    Best-effort: if requirements.txt isn't installed yet, or the check itself
    fails for any reason, skip the guide window rather than block startup.
    """
    try:
        from auth.google_auth import connection_status
        status = connection_status()
        return not (status.get("client_secret_present") and status.get("connected"))
    except Exception:
        return False


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

    webview.create_window(
        "Job Hunter Agent", url, width=1100, height=800, min_size=(720, 560)
    )

    if _google_setup_incomplete():
        # Created after the main window, so most platforms hand it focus and
        # draw it on top — reads as "above" without needing manual x/y math
        # that would vary by screen size.
        webview.create_window(
            "Job Hunter Agent — Google Setup Guide",
            f"{url}/?tab=connections",
            width=520,
            height=680,
            min_size=(420, 480),
        )

    webview.start()
    server.shutdown()


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()

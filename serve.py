#!/usr/bin/env python3
"""
Build the site and serve dist/ locally for testing.

    py serve.py                 # build, then serve on http://localhost:8000
    py serve.py --port 9000     # pick a port
    py serve.py --no-build      # serve whatever is already in dist/
    py serve.py --no-open       # don't auto-open a browser

Stop it with Ctrl+C (or the "shutdown arman" workflow).
"""

from __future__ import annotations

import argparse
import http.server
import socketserver
import subprocess
import sys
import threading
import webbrowser
from functools import partial
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
DIST = ROOT / "dist"


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serve dist/ with clean-URL support and quiet, readable logging."""

    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".svg": "image/svg+xml",
        ".json": "application/json",
        ".webmanifest": "application/manifest+json",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST), **kwargs)

    def send_head(self):
        # Map "/writeups/foo/" and "/writeups/foo" to their index.html.
        path = self.translate_path(self.path)
        p = Path(path)
        if not p.exists() and not self.path.endswith("/"):
            candidate = Path(self.translate_path(self.path + "/index.html"))
            if candidate.exists():
                self.path = self.path + "/"
        return super().send_head()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stdout.write("  %s\n" % (fmt % args))

    def log_error(self, *args):
        pass  # 404s during dev are noise


def build() -> bool:
    print("Building site…")
    result = subprocess.run([sys.executable, str(ROOT / "build.py")], cwd=ROOT)
    if result.returncode != 0:
        print("Build failed — not starting the server.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    if not args.no_build:
        if not build():
            return 1

    if not DIST.exists():
        print("dist/ does not exist yet. Run without --no-build first.")
        return 1

    socketserver.TCPServer.allow_reuse_address = True
    try:
        httpd = socketserver.TCPServer(("127.0.0.1", args.port), Handler)
    except OSError as exc:
        print(f"Could not bind port {args.port}: {exc}")
        print("Another server may already be running. Try 'shutdown arman' or --port.")
        return 1

    url = f"http://localhost:{args.port}/"
    print("\n" + "=" * 52)
    print(f"  Serving  {url}")
    print(f"  Folder   {DIST}")
    print("  Stop     Ctrl+C  (or: shutdown arman)")
    print("=" * 52 + "\n")

    if not args.no_open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down…")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

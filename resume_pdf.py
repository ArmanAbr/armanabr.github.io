#!/usr/bin/env python3
"""
Rebuild the site, then print the document-style resume at dist/resume/print/
(templates/resume_print.html) to static/Arman_Abrahamyan_Resume.pdf with headless
Chrome (or Edge), and rebuild once more so the new PDF lands in dist/. Run it
whenever content/pages/resume.md changes.

Usage:
    py resume_pdf.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
OUT = ROOT / "static" / "Arman_Abrahamyan_Resume.pdf"
PAGE = ROOT / "dist" / "resume" / "print" / "index.html"

CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_browser() -> str | None:
    for name in ("google-chrome", "chromium", "chrome", "msedge"):
        if shutil.which(name):
            return shutil.which(name)
    return next((c for c in CANDIDATES if Path(c).is_file()), None)


def main() -> int:
    browser = find_browser()
    if not browser:
        print("No Chrome/Edge found - print dist/resume/ to PDF by hand instead.")
        return 1
    subprocess.run([sys.executable, str(ROOT / "build.py")], check=True)
    subprocess.run([browser, "--headless=new", "--disable-gpu",
                    "--no-pdf-header-footer", f"--print-to-pdf={OUT}",
                    PAGE.as_uri()], check=True)
    subprocess.run([sys.executable, str(ROOT / "build.py")], check=True)
    print(f"Resume PDF -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

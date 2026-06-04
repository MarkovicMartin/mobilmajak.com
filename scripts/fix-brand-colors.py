#!/usr/bin/env python3
"""Nahradí staré hex barvy tokeny CI v frontend/src/**/*.css"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "frontend" / "src"
REPLACEMENTS = [
    ("#667eea", "var(--brand-navy)"),
    ("#764ba2", "var(--brand-navy-hover)"),
    ("#ff6b9d", "var(--brand-pink)"),
    ("#c44569", "var(--brand-pink-hover)"),
    ("#3498db", "var(--brand-navy)"),
    ("#2980b9", "var(--brand-navy-hover)"),
    ("#1f618d", "var(--brand-navy-hover)"),
    ("#ff72b6", "var(--brand-pink)"),
    ("#9b6bff", "var(--brand-navy)"),
]

# Pouze celé deklarace (#fff;), ne prefix v #fffbeb / #fffdf0
BG_RE = [
    (r"background:\s*white\s*;", "background: var(--bg-card);"),
    (r"background:\s*#fff\s*;", "background: var(--bg-card);"),
    (r"background:\s*#ffffff\s*;", "background: var(--bg-card);"),
    (r"background-color:\s*white\s*;", "background-color: var(--bg-card);"),
    (r"background-color:\s*#fff\s*;", "background-color: var(--bg-card);"),
    (r"background-color:\s*#ffffff\s*;", "background-color: var(--bg-card);"),
]

SKIP_SUFFIXES = ("STYLES.md",)

def main():
    changed = 0
    for path in SRC.rglob("*.css"):
        if path.name in SKIP_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        new = text
        for old, new_val in REPLACEMENTS:
            new = new.replace(old, new_val)
        for pattern, repl in BG_RE:
            new = re.sub(pattern, repl, new, flags=re.IGNORECASE)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
            print(path.relative_to(REPO))
    print(f"Updated {changed} files")

if __name__ == "__main__":
    main()

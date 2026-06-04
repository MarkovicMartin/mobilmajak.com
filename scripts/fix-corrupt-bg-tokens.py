#!/usr/bin/env python3
"""Opraví var(--bg-card)XXX vzniklé chybným nahrazováním #fff v delších hex."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "frontend" / "src"

FIXES = {
    "var(--bg-card)beb": "#fffbeb",
    "var(--bg-card)fff": "var(--bg-card)",
    "var(--bg-card)5f5": "#f5f5f5",
    "var(--bg-card)8e1": "#fff8e1",
    "var(--bg-card)7ed": "#fff7ed",
    "var(--bg-card)1f2": "#fff1f2",
    "var(--bg-card)3cd": "#fff3cd",
    "var(--bg-card)df0": "#fffdf0",
    "var(--bg-card)af0": "#fffaf0",
    "var(--bg-card)3f0": "#f0fff0",
}

def main():
    n = 0
    for path in SRC.rglob("*.css"):
        text = path.read_text(encoding="utf-8")
        new = text
        for old, val in FIXES.items():
            new = new.replace(old, val)
        if new != text:
            path.write_text(new, encoding="utf-8")
            n += 1
            print(path.relative_to(REPO))
    print(f"Fixed {n} files")

if __name__ == "__main__":
    main()

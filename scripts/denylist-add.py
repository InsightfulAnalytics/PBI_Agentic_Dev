#!/usr/bin/env python3
"""Add a term to the personal-data denylist without writing the term to disk.

The denylist ships in a public repository, so it stores SHA-256 of the normalised term
rather than the term itself. This helper does the normalising and hashing so the two
never drift apart.

Usage::

    python scripts/denylist-add.py "Some Client Ltd" "client name"
    python scripts/denylist-add.py --check "Some Client Ltd"

``--check`` reports whether a term is already listed and writes nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import unicodedata
from pathlib import Path

# check-skill-hygiene.py is not a legal module name, so normalise() is duplicated here.
# scripts/selftest-hygiene.py asserts the two copies agree.

HASHES = Path(__file__).resolve().parent.parent / ".github" / "denylist-hashes.txt"


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9@.\\/_-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def digest(term: str) -> str:
    return hashlib.sha256(normalise(term).encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("term", help="the literal term to protect")
    ap.add_argument("label", nargs="?", default="denylisted term",
                    help="a label describing the CLASS of term, never the term itself")
    ap.add_argument("--check", action="store_true", help="report membership, write nothing")
    args = ap.parse_args()

    norm = normalise(args.term)
    if not norm:
        print("term normalises to nothing", file=sys.stderr)
        return 2
    words = len(norm.split())
    h = digest(args.term)

    existing = HASHES.read_text(encoding="utf-8") if HASHES.exists() else ""
    if h in existing:
        print(f"already listed ({words} word(s) after normalisation)")
        return 0
    if args.check:
        print(f"not listed ({words} word(s) after normalisation)")
        return 1

    if words > 5:
        print(f"term normalises to {words} words; the checker only hashes 1..5 word n-grams. "
              f"Raise MAX_NGRAM in scripts/check-skill-hygiene.py or use a shorter distinctive term.",
              file=sys.stderr)
        return 2
    if args.label.lower().strip() in norm or norm in args.label.lower():
        print("refusing: the label leaks the term it protects. Describe the class instead, "
              "for example 'client name'.", file=sys.stderr)
        return 2

    with HASHES.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(f"{h}  {args.label}\n")
    print(f"added ({words} word(s) after normalisation)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

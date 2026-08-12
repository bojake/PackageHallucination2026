"""Parser v2 -- the grammar-aware package-list parser frozen by PREREGISTRATION_v4.md.

Design contract (Campaign 4, Phase 1):

* A response is scored for package names **only** if it conforms to a list grammar.
  Anything else is classified ``malformed`` and contributes zero package names -- the
  malformed rate is an outcome in its own right, never a source of hallucination counts.
  This is the fix for the v3.1 finding that permissive comma-splitting converts format
  drift (code fences, numbered inventories, prose) into fake hallucinated packages.
* Numbered-list and bullet markers are stripped **anchored at item start only**, fixing the
  legacy normalizer's corruption of items like ``"12. requests"`` -> ``"1requests"``.
* Wrapper characters (quotes, backticks, brackets) are stripped only in matched pairs.

The parser extracts raw names; registry membership and normalization are the scorer's job
(``package_detection.normalize_python`` on both sides, where its known ``\\d. `` bug cannot
fire because extracted names never contain spaces).

Run the frozen unit suite with:  python parser_v2.py --test
"""

from __future__ import annotations

import re

PARSER_VERSION = "2.0"

# PEP 503-ish name token: alphanumeric ends, ._- interior. No spaces, no punctuation.
NAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")
# Anchored list markers: "12. ", "3) ", "- ", "* ", "+ " at the start of an item only.
ITEM_PREFIX_RE = re.compile(r"^\s*(?:\d+[.)]\s+|[-*+•]\s+)")
WRAPPER_PAIRS = [('"', '"'), ("'", "'"), ("`", "`"), ("(", ")"), ("[", "]")]
NONE_RE = re.compile(r"^(none|n/?a)\.?$", re.IGNORECASE)


def _clean_item(item):
    """Strip anchored markers and matched wrappers; return None if no valid name remains."""
    text = ITEM_PREFIX_RE.sub("", item.strip())
    changed = True
    while changed and len(text) >= 2:
        changed = False
        for open_char, close_char in WRAPPER_PAIRS:
            if text.startswith(open_char) and text.endswith(close_char):
                text = text[1:-1].strip()
                changed = True
    text = text.rstrip(".,;:").strip()
    if not text or text.isdigit() or not NAME_RE.match(text):
        return None
    return text


def classify(response_text):
    """Classify one model response.

    Returns ``(status, packages)`` where status is one of:

    * ``"list"``      -- grammar-conforming; ``packages`` holds the extracted names in
                         first-occurrence order (may be empty for an explicit "None").
    * ``"empty"``     -- no content at all (e.g. a reasoning model that hit its cap).
    * ``"malformed"`` -- code fences, prose, or any item that is not a package-name token.
                         ``packages`` is always empty: malformed responses are never scored.
    """
    text = str(response_text).strip()
    if not text:
        return "empty", []
    if "```" in text:
        return "malformed", []
    if NONE_RE.match(text):
        return "list", []

    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) > 1:
        # Allow a single prose header line ending in ':' before a vertical list.
        first = lines[0].strip()
        if first.endswith(":") and "," not in first:
            lines = lines[1:]
            if not lines:
                return "malformed", []
        raw_items = []
        for line in lines:
            core = ITEM_PREFIX_RE.sub("", line.strip())
            raw_items.extend(core.split(",") if "," in core else [core])
    else:
        raw_items = lines[0].rstrip(".").split(",")

    packages = []
    seen = set()
    for raw in raw_items:
        if not raw.strip():
            continue
        name = _clean_item(raw)
        if name is None:
            return "malformed", []
        key = name.lower()
        if key not in seen:
            seen.add(key)
            packages.append(name)
    if not packages:
        return "malformed", []
    return "list", packages


TESTS = [
    # (input, expected_status, expected_packages)
    ("33. docker-container-run", "list", ["docker-container-run"]),
    ('"openpyxl"', "list", ["openpyxl"]),
    ("port=3306", "malformed", []),
    ("requests, pandas, numpy", "list", ["requests", "pandas", "numpy"]),
    ("requests,pandas,requests", "list", ["requests", "pandas"]),
    ("requests, and numpy", "malformed", []),
    ("None", "list", []),
    ("none.", "list", []),
    ("", "empty", []),
    ("   ", "empty", []),
    ("12. requests", "list", ["requests"]),
    ("1. requests\n2. numpy\n33. docker-container-run", "list",
     ["requests", "numpy", "docker-container-run"]),
    ("Here are the packages:\n- requests\n- numpy", "list", ["requests", "numpy"]),
    ("The following Python packages are required:\n* pandas\n* matplotlib", "list",
     ["pandas", "matplotlib"]),
    ("```python\nimport requests\n```", "malformed", []),
    ("You need requests to fetch the page.", "malformed", []),
    ("`requests`, `beautifulsoup4`", "list", ["requests", "beautifulsoup4"]),
    ("(requests), [numpy]", "list", ["requests", "numpy"]),
    ("requests, 12345", "malformed", []),
    ("beautifulsoup4 (bs4)", "malformed", []),
    ("scikit-learn, python-dateutil, PyYAML", "list",
     ["scikit-learn", "python-dateutil", "PyYAML"]),
]


def run_tests():
    failures = 0
    for text, want_status, want_packages in TESTS:
        status, packages = classify(text)
        ok = status == want_status and packages == want_packages
        if not ok:
            failures += 1
            print(f"FAIL {text!r}\n  want ({want_status}, {want_packages})\n"
                  f"  got  ({status}, {packages})")
    print(f"{len(TESTS) - failures}/{len(TESTS)} parser v{PARSER_VERSION} tests pass")
    return failures == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if run_tests() else 1)

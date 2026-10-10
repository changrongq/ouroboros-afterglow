"""
refresh_manifest_roles.py (RC9 helper) — regenerate the EXECUTION_CRITICAL_ROLE_TABLE
block in the MANIFEST directly from the single registry, so the role table can
never drift from the actual file hashes.

Build-side helper (NOT execution-critical). Run before freeze.

Usage:
    python refresh_manifest_roles.py
"""
from __future__ import annotations

import re
from pathlib import Path

from manifest_bind import role_table_lines

MANIFEST = Path(__file__).resolve().parent.parent / "reports" / "AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md"
BEGIN = "EXECUTION_CRITICAL_ROLE_TABLE_BEGIN"
END = "EXECUTION_CRITICAL_ROLE_TABLE_END"


def main() -> int:
    text = MANIFEST.read_text(encoding="utf-8")
    new_block = role_table_lines()
    body = new_block.split("EXECUTION_CRITICAL_ROLE_TABLE_END")[0].rstrip("\n")

    if "__ROLE_TABLE__" in text:
        text2 = text.replace("__ROLE_TABLE__", body).replace("\r\n", "\n")
    else:
        # anchored replace of an existing BEGIN..END block
        pattern = re.compile(r"```text\r?\n" + BEGIN + r"\r?\n.*?\r?\n" + END + r"\r?\n```", re.DOTALL)
        if not pattern.search(text):
            print("ERROR: role table marker/block not found")
            return 2
        replacement = "```text\n" + body + "\n" + END + "\n```"
        text2 = pattern.sub(replacement, text, count=1).replace("\r\n", "\n")

    MANIFEST.write_text(text2, encoding="utf-8")
    print("role table refreshed;", MANIFEST.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".venv", "build", "dist", "cache", "logs", "output", "__pycache__", ".pytest_cache"}
TEXT_SUFFIXES = {".py", ".md", ".txt", ".toml", ".json", ".yml", ".yaml", ".bat", ".ps1", ".example", ".gitignore", ".gitattributes", ".editorconfig"}
PATTERNS = {
    "OpenAI secret key": re.compile(r"\bsk-(?!test-|example|placeholder)[A-Za-z0-9_-]{16,}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def candidate_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        if path.name.startswith("build_") and path.suffix == ".log":
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"README", "LICENSE"}:
            yield path


def main() -> int:
    findings: list[str] = []
    for path in candidate_files():
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                findings.append(f"{path.relative_to(ROOT)}: possible {label}")
    if findings:
        print("Secret scan failed:", *findings, sep="\n- ")
        return 1
    print("Secret scan passed: no credential patterns found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


#!/usr/bin/env python3
"""Public-safety scanner for the solo-biz-playbook repository.

This is a conservative pre-push helper. It does not decide what is publishable;
it flags terms that should be blocked or reviewed under docs/publication-safety.md.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".html",
    ".svg",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".py",
    ".js",
    ".mjs",
    ".ts",
    ".tsx",
    ".css",
}

SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__"}


@dataclass(frozen=True)
class Finding:
    severity: str
    label: str
    path: Path
    line: int
    text: str


BLOCK_PATTERNS = [
    ("local absolute path", re.compile(r"/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("secret-like token", re.compile(r"\b(?:api[_-]?key|secret|token|webhook)[\"'\s:=]+[A-Za-z0-9_./+=-]{16,}", re.I)),
    ("email address", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("calendar id", re.compile(r"\b[A-Za-z0-9._%+-]+@group\.calendar\.google\.com\b")),
    ("notion/database id", re.compile(r"\b[0-9a-f]{32}\b|\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)),
]

REVIEW_TERMS = [
    "출판사",
    "고객사",
    "기업교육",
    "강의 플랫폼",
    "멘토링 플랫폼",
    "계약서",
    "예약판매",
    "홈서버",
    "Mac mini",
    "Tailscale",
    "Discord",
    "Notion",
    "Supabase",
    "Gmail",
    "Google Drive",
    "Obsidian",
    "유튜브",
    "YouTube",
    "SNS",
    "한빛",
    "ggplab",
    "GGPLab",
]

ALLOW_REVIEW_PATHS = {
    Path("README.md"),
    Path("examples/my-canvas.md"),
    Path("docs/publication-safety.md"),
    Path("scripts/public_safety_check.py"),
}

ALLOW_BLOCK_SNIPPETS = [
    "user@example.com",
    "xxxxxxxx@group.calendar.google.com",
    "/Users/name/",
    "/home/name/",
]


def git_files(staged: bool) -> list[Path]:
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"] if staged else ["git", "ls-files"]
    output = subprocess.check_output(cmd, cwd=ROOT, text=True)
    return [ROOT / line for line in output.splitlines() if line]


def walk_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.is_file() and path.suffix in TEXT_EXTENSIONS:
            files.append(path)
    return files


def is_text_file(path: Path) -> bool:
    return path.is_file() and path.suffix in TEXT_EXTENSIONS


def scan_file(path: Path) -> list[Finding]:
    rel = path.relative_to(ROOT)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return []

    findings: list[Finding] = []
    for index, line in enumerate(lines, start=1):
        for label, pattern in BLOCK_PATTERNS:
            if pattern.search(line) and not any(snippet in line for snippet in ALLOW_BLOCK_SNIPPETS):
                findings.append(Finding("BLOCK", label, rel, index, line.strip()))
        if rel not in ALLOW_REVIEW_PATHS:
            for term in REVIEW_TERMS:
                if term in line:
                    findings.append(Finding("REVIEW", f"possibly identifying term: {term}", rel, index, line.strip()))
    return findings


def print_findings(findings: list[Finding]) -> None:
    for finding in findings:
        print(f"{finding.severity}: {finding.path}:{finding.line}: {finding.label}")
        print(f"  {finding.text[:240]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan public repo files for publication-safety risks.")
    parser.add_argument("--staged", action="store_true", help="scan only staged files")
    parser.add_argument("--all", action="store_true", help="scan all repo files, including untracked text files")
    args = parser.parse_args()

    candidates = walk_files() if args.all else git_files(staged=args.staged)
    files = [path for path in candidates if is_text_file(path)]

    findings: list[Finding] = []
    for path in files:
        findings.extend(scan_file(path))

    block_count = sum(1 for item in findings if item.severity == "BLOCK")
    review_count = sum(1 for item in findings if item.severity == "REVIEW")

    print_findings(findings)
    print(f"\nScanned {len(files)} files. BLOCK={block_count}, REVIEW={review_count}")
    if review_count:
        print("Review findings are not automatically fatal; apply docs/publication-safety.md.")
    return 1 if block_count else 0


if __name__ == "__main__":
    sys.exit(main())

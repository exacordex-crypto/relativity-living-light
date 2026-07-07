#!/usr/bin/env python3
"""Audit URL provenance hygiene for repository YAML and Markdown files.

This tool is intentionally local-only. It does not fetch URLs and does not
validate scientific claims. It checks whether URL fields and URL mentions are
traceable through checkbox-style curation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

REPO = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = REPO / "artifacts" / "real-data-url-audit"
URL_RE = re.compile(r"https?://[^\s)\]}>\"']+")
YAML_URL_RE = re.compile(r"^\s*url\s*:\s*(?P<value>.+?)\s*$")
CHECKBOX_RE = re.compile(r"^\s*-\s*\[(?P<mark>[ xX])\]\s*(?P<body>.*)$")
SKIP_PARTS = {".git", "artifacts", "node_modules", ".gradle", "build"}
TEXT_SUFFIXES = {".yml", ".yaml", ".md"}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    severity: str
    rule: str
    value: str
    detail: str


def iter_text_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        yield path


def line_has_checkbox(line: str) -> bool:
    return bool(CHECKBOX_RE.match(line))


def extract_checkbox_urls(lines: list[str]) -> set[str]:
    urls: set[str] = set()
    for line in lines:
        if line_has_checkbox(line):
            urls.update(URL_RE.findall(line))
    return urls


def audit_file(path: Path, checkbox_urls: set[str]) -> list[Finding]:
    rel = path.relative_to(REPO).as_posix()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return [Finding(rel, 0, "WARN", "decode", "", "file is not UTF-8 text")]

    findings: list[Finding] = []
    for idx, line in enumerate(lines, start=1):
        yaml_url = YAML_URL_RE.match(line)
        if yaml_url:
            value = yaml_url.group("value").strip().strip('"\'')
            if value in {"", "TOKEN_VAZIO", "TODO", "TBD", "null", "None"}:
                findings.append(Finding(rel, idx, "ERROR", "empty_yaml_url", value, "url field is empty or placeholder"))
            elif value.startswith("http") and value not in checkbox_urls:
                findings.append(Finding(rel, idx, "WARN", "yaml_url_not_in_checkbox", value, "url appears in YAML but not in a checkbox curation line"))

        for url in URL_RE.findall(line):
            if path.suffix.lower() == ".md" and line_has_checkbox(line):
                continue
            if url not in checkbox_urls and "YML_OPERATIONAL_EXCELLENCE_HOTFIX.md" not in rel:
                findings.append(Finding(rel, idx, "INFO", "url_without_checkbox", url, "url mention is not linked to checkbox curation"))
    return findings


def build_report(findings: list[Finding]) -> tuple[dict, str]:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1

    summary = {
        "schema": "rll.real_data_url_audit.v1",
        "claim_boundary": "URL audit checks provenance hygiene only; it does not validate RLL or scientific superiority.",
        "total_findings": len(findings),
        "counts_by_severity": counts,
        "blocking_errors": counts.get("ERROR", 0),
    }

    md = [
        "# Real Data URL Audit Report",
        "",
        f"- total_findings: `{summary['total_findings']}`",
        f"- blocking_errors: `{summary['blocking_errors']}`",
        f"- claim_boundary: `{summary['claim_boundary']}`",
        "",
        "| severity | rule | path | line | value | detail |",
        "|---|---|---|---:|---|---|",
    ]
    for finding in findings:
        value = finding.value.replace("|", "\\|")
        detail = finding.detail.replace("|", "\\|")
        md.append(f"| {finding.severity} | {finding.rule} | `{finding.path}` | {finding.line} | `{value}` | {detail} |")
    return summary, "\n".join(md) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit URL provenance hygiene in YAML/Markdown files.")
    parser.add_argument("--root", type=Path, default=REPO)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on ERROR findings.")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    files = list(iter_text_files(root))
    all_lines: list[str] = []
    for path in files:
        try:
            all_lines.extend(path.read_text(encoding="utf-8").splitlines())
        except UnicodeDecodeError:
            continue
    checkbox_urls = extract_checkbox_urls(all_lines)

    findings: list[Finding] = []
    for path in files:
        findings.extend(audit_file(path, checkbox_urls))

    summary, markdown = build_report(findings)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / "real_data_url_audit_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.report_dir / "REAL_DATA_URL_AUDIT.md").write_text(markdown, encoding="utf-8")
    (args.report_dir / "real_data_url_audit_findings.json").write_text(
        json.dumps([asdict(finding) for finding in findings], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.strict and summary["blocking_errors"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

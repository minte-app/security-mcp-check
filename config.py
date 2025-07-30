import os
from collections import defaultdict
from pathlib import Path

import logfire
import yaml
from dotenv import load_dotenv

from deps.deps import Finding

load_dotenv(override=True)

logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))
logfire.instrument_pydantic_ai()

CONFIG_PATH = Path("config.yaml")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_whitelist() -> list[str]:
    config = load_config()
    return config.get("whitelist", {}).get("extensions", [])


def load_blacklist() -> tuple[set[str], set[str]]:
    config = load_config()
    blacklist_cfg = config.get("blacklist", {})
    ignored_dirs = set(blacklist_cfg.get("directories", []))
    ignored_files = set(blacklist_cfg.get("files", []))
    return ignored_dirs, ignored_files


def generate_markdown_report(findings: list[Finding], unanalyzed_files: list[str], output_path: Path):
    """Generates a Markdown report with colors from the list of findings."""
    report_content = "# Security Analysis Report\n\nThis report details the security vulnerabilities found by the AI agent.\n"

    if not findings:
        report_content += "\n**No security vulnerabilities were found in the analyzed files.**\n"
    else:
        findings_by_file = defaultdict(list)
        for f in findings:
            findings_by_file[f.file_path].append(f)

        for file_path, file_findings in sorted(findings_by_file.items()):
            report_content += f"\n---\n\n### File: `{file_path}`\n\n"
            report_content += "| Severity | Issue | Explanation | Recommendation | Aprox Line |\n"
            report_content += "|----------|-------|-------------|----------------|------------|\n"
            for f in sorted(file_findings, key=lambda x: x.severity):
                line = f.line_hint if f.line_hint is not None else "N/A"
                recommendation = f.recommendation if f.recommendation is not None else "-"

                severity_cell = f.severity
                if f.severity == "CRITICAL":
                    severity_cell = "<font color='red'>CRITICAL</font>"
                elif f.severity == "WARNING":
                    severity_cell = "<font color='orange'>WARNING</font>"

                report_content += f"| {severity_cell} | {f.issue} | {f.explanation} | {recommendation} | {line} |\n"

    if unanalyzed_files:
        report_content += """\n---\n\n## Unanalyzed Files\n\n
            The following files were not analyzed because their extensions are not in the whitelist or they are in the blacklist:\n\n"""
        report_content += "\n".join([f"- `{f}`" for f in sorted(unanalyzed_files)])

    # Ensure the reports directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_content, encoding="utf-8")

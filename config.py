import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

import logfire
import yaml
from dotenv import load_dotenv

from deps.deps import Finding

load_dotenv(override=True)

logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))
logfire.instrument_pydantic_ai()

CONFIG_PATH = Path("config.yaml")
CACHE_FILE = Path(".agent_cache.json")


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


def load_cache() -> dict[str, Any]:
    """Loads the cache file from disk."""
    if not CACHE_FILE.exists():
        return {}
    with open(CACHE_FILE) as f:
        try:
            # Cast to handle the case where the file is empty or malformed
            return cast(dict[str, Any], json.load(f))
        except json.JSONDecodeError:
            return {}


def save_cache(cache: dict[str, Any]):
    """Saves the cache to disk."""
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def _calculate_hash(file_path: Path) -> str:
    """Calculates the SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def filter_files_by_cache(
    repo_root: Path,
    repo_identifier: str,
    all_files: list[str],
    repo_cache: dict[str, str],
) -> tuple[list[str], list[str], dict[str, str]]:
    """
    Filters files based on their hash, comparing them to a cached version.

    Args:
        repo_root: The absolute path to the repository's root.
        repo_identifier: The unique identifier for the repository (URL or local path).
        all_files: A list of all file paths (relative to repo_root) to be checked.
        repo_cache: The existing cache for this specific repository.

    Returns:
        A tuple containing:
        - A list of files that have changed or are new.
        - A list of files that have not changed.
        - A dictionary with the new, updated hashes for all files.
    """
    files_to_analyze = []
    skipped_files = []
    new_repo_cache = {}

    for file_path_str in all_files:
        file_path = repo_root / file_path_str
        if not file_path.exists():
            continue

        current_hash = _calculate_hash(file_path)
        new_repo_cache[file_path_str] = current_hash

        if repo_cache.get(file_path_str) == current_hash:
            skipped_files.append(file_path_str)
        else:
            files_to_analyze.append(file_path_str)

    return files_to_analyze, skipped_files, new_repo_cache


def generate_markdown_report(findings: list[Finding], unanalyzed_files: list[str], skipped_files: list[str], output_path: Path):
    """Generates a Markdown report with colors from the list of findings."""
    report_content = "# Security Analysis Report\n\nThis report details the security vulnerabilities found by the AI agent.\n"

    if not findings and not skipped_files:
        report_content += "\n**No security vulnerabilities were found in the analyzed files.**\n"
    elif not findings and skipped_files:
        report_content += "\n**No new security vulnerabilities were found. All files passed the cache check.**\n"
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

    if skipped_files:
        report_content += """\n---\n\n### Skipped Files (Unchanged)\n\nThe following files were not analyzed in this run because their content has not changed since the last analysis:\n\n"""
        report_content += "\n".join([f"- `{f}`" for f in sorted(skipped_files)])

    if unanalyzed_files:
        report_content += """\n---\n\n### Unanalyzed Files\n\nThe following files were not analyzed because their extensions are not in the whitelist or they are in the blacklist:\n\n"""
        report_content += "\n".join([f"- `{f}`" for f in sorted(unanalyzed_files)])

    # Ensure the reports directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_content, encoding="utf-8")

import argparse
import asyncio
import json
import re
import subprocess
import yaml
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Set, Tuple, List

import httpx

import config  # Import to override environment variables
from deps.deps import FindingsList, Finding
from agent.rules import load_rules

def load_whitelist(path: Path) -> list[str]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("whitelist", {}).get("extensions", [])

def load_blacklist(path: Path) -> Tuple[Set[str], Set[str]]:
    if not path.exists():
        return set(), set()
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    blacklist_cfg = cfg.get("blacklist", {})
    ignored_dirs = set(blacklist_cfg.get("directories", []))
    ignored_files = set(blacklist_cfg.get("files", []))
    return ignored_dirs, ignored_files

def parse_args():
    parser = argparse.ArgumentParser(description="AI Security Agent")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="URL of the GitHub repo (e.g., https://github.com/user/repo)")
    group.add_argument("--directory", type=Path, help="Local path to the already cloned repo")
    
    return parser.parse_args()

def get_repo(url: str, base_dir: Path = Path("repos")) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    repo_name = url.rstrip("/").split("/")[-1].removesuffix(".git")
    repo_path = base_dir / repo_name

    def get_default_branch(path: Path) -> str:
        try:
            result = subprocess.run(
                ["git", "remote", "show", "origin"], 
                cwd=path, 
                check=True, 
                capture_output=True, 
                text=True
            )
            match = re.search(r"HEAD branch: (\S+)", result.stdout)
            if match:
                return match.group(1)
            # Fallback for older Git versions or unusual remote configs
            return "master"
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback if git command fails or not in a git repo
            return "master"

    if repo_path.exists():
        print(f"[+] Repository already exists at {repo_path}.")
        print(f"[+] Resetting to remote state of default branch...")
        try:
            subprocess.run(["git", "fetch", "origin"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(["git", "reset", "--hard", "origin/HEAD"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(["git", "clean", "-fdx"], cwd=repo_path, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"[x] Error resetting repository: {e.stderr}")
            raise
    else:
        print(f"[*] Cloning repository {url}...")
        clone_cmd = ["git", "clone", url]
        try:
            subprocess.run(clone_cmd, cwd=base_dir, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"[x] Error cloning repository: {e.stderr}")
            raise
    return repo_path

def build_file_index(root: Path, allowed_exts: Set[str], ignored_dirs: Set[str], ignored_files: Set[str]) -> tuple[list[str], list[str]]:
    indexed_files = []
    non_indexed_files = []

    for p in root.rglob("*"):
        relative_path = p.relative_to(root)
        if any(part in ignored_dirs for part in relative_path.parts):
            continue
        if p.is_file():
            if p.name in ignored_files:
                continue
            path_str = relative_path.as_posix()
            if p.suffix.lower() in allowed_exts:
                indexed_files.append(path_str)
            else:
                non_indexed_files.append(path_str)
    return indexed_files, non_indexed_files

def generate_markdown_report(findings: List[Finding], unanalyzed_files: List[str], output_path: Path):
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
            report_content += "| Severity | Issue | Explanation | Recommendation | Line |\n"
            report_content += "|----------|-------|-------------|----------------|------|\n"
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
        report_content += "\n---\n\n## Unanalyzed Files\n\nThe following files were not analyzed because their extensions are not in the whitelist or they are in the blacklist:\n\n"
        report_content += "\n".join([f"- `{f}`" for f in sorted(unanalyzed_files)])

    # Ensure the reports directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_content, encoding="utf-8")

async def main():
    args = parse_args()

    # 1. Load configurations
    whitelisted_exts = set(e.lower() for e in load_whitelist(Path("whitelist.yaml")))
    if not whitelisted_exts:
        print("[x] The 'whitelist.yaml' file does not exist or is empty. Nothing to analyze.")
        return

    ignored_dirs, ignored_files = load_blacklist(Path("blacklist.yaml"))
    rules_map = load_rules(Path("rules"), allowed_extensions=whitelisted_exts)
    if not rules_map:
        print("[x] No rules found for the extensions specified in 'whitelist.yaml'.")
        return
    print(f"[+] {len(rules_map)} language rule(s) loaded according to the whitelist.")

    for ext in whitelisted_exts:
        if ext not in rules_map:
            print(f"[!] Warning: Extension '{ext}' is in the whitelist but no rule was found for it.")

    # 2. Get the source code
    if args.url:
        try:
            repo_root = get_repo(args.url, Path("repos"))
        except subprocess.CalledProcessError:
            print("[x] The repository URL is incorrect or does not exist.")
            return
    else:
        if not args.directory or not args.directory.is_dir():
            print("[x] The specified directory does not exist.")
            return
        repo_root = args.directory.resolve()

    # 3. Index files
    file_index, non_indexed_files = build_file_index(repo_root, whitelisted_exts, ignored_dirs, ignored_files)
    repo_name = repo_root.name
    report_path = Path("reports") / f"{repo_name}-security-report.md"

    if not file_index:
        print("[x] No files with the whitelisted extensions were found in the repository.")
        generate_markdown_report([], non_indexed_files, report_path)
        print(f"[+] Report generated for unanalyzed files at: {report_path.resolve()}")
        return

    # 4. Import and run the agent
    from agent.pydantic_agent import Deps, analyzer, security_agent

    all_findings = []
    async with httpx.AsyncClient() as client:
        for file_path in file_index:
            file_ext = Path(file_path).suffix.lower()
            active_rule = rules_map.get(file_ext)

            if not active_rule:
                continue

            print(f"[*] Analyzing {file_path} with {active_rule.language} rules...")
            
            deps = Deps(
                repo_root=repo_root,
                file_index=file_path,
                analyzer=analyzer,
                active_rule=active_rule,
                http=client,
                selector=None,
            )
            
            instructions = (
                f"Analyze the file '{file_path}' using the rules for {active_rule.language}. "
                "First, call `read_current_file` to get the code, then call `analyze_code` to analyze it."
            )

            try:
                result = await security_agent.run(instructions, deps=deps)
                findings_list: FindingsList = result.output
                findings = findings_list.__root__

                if findings:
                    for finding in findings:
                        all_findings.append(finding)
                    print(f"[+] Found {len(findings)} potential issues in {file_path}")
                else:
                    print(f"[+] {file_path} analyzed. No issues found.")
            except json.JSONDecodeError:
                print(f"[!] Could not decode the response for {file_path}. Output: {result.output}")
            except Exception as e:
                print(f"[x] Error analyzing {file_path}: {e}")

    # 5. Generate and save the final report
    generate_markdown_report(all_findings, non_indexed_files, report_path)
    print(f"\n--- FINAL REPORT ---")
    print(f"[+] Report successfully generated at: {report_path.resolve()}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            pass
        else:
            raise
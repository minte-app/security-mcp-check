import re
import httpx
import json
from typing import List, Tuple

_GH_TREE_RE = re.compile(r"https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.*)")
_GH_BLOB_RE = re.compile(r"https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.*)")

# -----------------------------
# URL helpers
# -----------------------------

def parse_github_url(url: str) -> Tuple[str, str, str, str]:
    """Return (owner, repo, branch, base_path) from a tree/blob URL."""
    m = _GH_TREE_RE.match(url) or _GH_BLOB_RE.match(url)
    if not m:
        raise ValueError(f"URL no reconocida: {url}")
    owner, repo, branch, path = m.groups()
    base_path = path.rsplit('/', 1)[0] if '/' in path else ''
    return owner, repo, branch, base_path


def build_raw_url(owner: str, repo: str, branch: str, path: str) -> str:
    """Return raw.githubusercontent URL for a path (no leading slash)."""
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path.lstrip('/')}"

# -----------------------------
# LLM output helpers
# -----------------------------

def coerce_paths(output) -> List[str]:
    """Accept list/JSON/str and return list[str]."""
    if isinstance(output, list):
        return output
    try:
        parsed = json.loads(output)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    parts = [p.strip() for p in str(output).replace('', ',').split(',')]
    return [p for p in parts if p]

# -----------------------------
# GitHub REST API helpers
# -----------------------------
async def list_files_from_github_api(owner: str, repo: str, branch: str, base_path: str,
                                     extensions=(".js", ".ts"), token: str | None = None) -> List[Tuple[str, str]]:
    """Return list of (path, raw_url) for all files with given extensions under base_path using GitHub Contents API.
    Walks directories recursively.
    """
    base_path = base_path.strip('/')
    api_root = f"https://api.github.com/repos/{owner}/{repo}/contents"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async def walk(path: str, acc: List[Tuple[str, str]]):
        url = f"{api_root}/{path}" if path else api_root
        params = {"ref": branch}
        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            items = r.json()
        if isinstance(items, dict):
            # single file case
            if items.get('type') == 'file' and items['name'].endswith(extensions):
                acc.append((items['path'], items['download_url']))
            return
        for it in items:
            if it['type'] == 'dir':
                await walk(it['path'], acc)
            elif it['type'] == 'file' and it['name'].endswith(extensions):
                acc.append((it['path'], it['download_url']))

    results: List[Tuple[str, str]] = []
    await walk(base_path, results)
    return results

# -----------------------------
# Raw download
# -----------------------------
async def download_raw_file(raw_url: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(raw_url)
        r.raise_for_status()
        return r.text
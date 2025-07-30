from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

import dspy
import httpx

from agent.rules import LanguageRule


@dataclass
class Deps:
    """Dependencies accessible via RunContext.deps"""

    repo_root: Path
    file_index: str  # File currently being analyzed
    selector: dspy.Module
    analyzer: dspy.Module
    active_rule: Optional[LanguageRule] = None  # Rule for the current language
    http: Optional[httpx.AsyncClient] = None


@dataclass
class Finding:
    file_path: str
    issue: str
    severity: Literal["CRITICAL", "WARNING"]
    explanation: str
    recommendation: Optional[str]
    line_hint: Optional[int]


@dataclass
class FindingsList:
    __root__: list[Finding]

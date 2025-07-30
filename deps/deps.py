from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

import dspy
import httpx

from agent.rules import LanguageRule


@dataclass
class Deps:
    """Dependencias accesibles vía RunContext.deps"""

    repo_root: Path
    file_index: str  # Fichero que se está analizando
    selector: dspy.Module
    analyzer: dspy.Module
    active_rule: Optional[LanguageRule] = None # Regla para el lenguaje actual
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

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

import dspy
import httpx


@dataclass
class Deps:
    """Dependencias accesibles vía RunContext.deps"""

    repo_root: Path  # Ruta al repositorio clonado
    file_index: list[str]  # Lista de los archivos a verificar
    selector: dspy.Module  # dspy.ChainOfThought(FileDiscovery)
    analyzer: dspy.Module  # dspy.ReAct(JSStaticAnalysis)
    http: Optional[httpx.AsyncClient] = None  # cliente HTTP reutilizable


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

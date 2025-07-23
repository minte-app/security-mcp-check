from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
import httpx
import dspy

@dataclass
class Deps:
    """Dependencias accesibles vía RunContext.deps"""
    repo_root: Path         # Ruta al repositorio clonado
    file_index: List[str]   # Lista de los archivos a verificar
    selector: dspy.Module          # dspy.ChainOfThought(FileDiscovery)
    analyzer: dspy.Module          # dspy.ReAct(JSStaticAnalysis)
    http: Optional[httpx.AsyncClient] = None  # cliente HTTP reutilizable
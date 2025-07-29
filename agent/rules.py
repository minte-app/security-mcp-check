
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Set

@dataclass
class LanguageRule:
    language: str
    extensions: list[str]
    prompt: str

def load_rules(rules_dir: Path, allowed_extensions: Optional[Set[str]] = None) -> dict[str, LanguageRule]:
    """Carga reglas de los subdirectorios, opcionalmente filtrando por extensiones."""
    rules_map = {}
    if not rules_dir.is_dir():
        return rules_map

    for lang_dir in rules_dir.iterdir():
        if not lang_dir.is_dir():
            continue

        config_path = lang_dir / "config.yaml"
        prompt_path = lang_dir / "prompt.md"

        if not config_path.exists() or not prompt_path.exists():
            continue

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        prompt = prompt_path.read_text(encoding="utf-8").strip()

        rule = LanguageRule(
            language=config.get("language", lang_dir.name),
            extensions=config.get("extensions", []),
            prompt=prompt
        )

        # Si no se especifica un filtro, se cargan todas las reglas
        if allowed_extensions is None:
            for ext in rule.extensions:
                rules_map[ext.lower()] = rule
        else:
            # Cargar solo si alguna de las extensiones de la regla está en la whitelist
            for ext in rule.extensions:
                if ext.lower() in allowed_extensions:
                    rules_map[ext.lower()] = rule
            
    return rules_map

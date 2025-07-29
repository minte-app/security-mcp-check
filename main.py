import argparse
import asyncio
import json
import subprocess
import yaml
from dataclasses import asdict
from pathlib import Path
from typing import Set, Tuple

import httpx

import config  # necesario para overridear variables de entorno
from deps.deps import FindingsList
from agent.rules import load_rules

# Extrae la lista de extensiones a comprobar
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
    group.add_argument("--url", help="URL del repo GitHub (ej: https://github.com/user/repo)")
    group.add_argument("--directory", type=Path, help="Ruta local al repo ya clonado")
    return parser.parse_args()


# Clona el repositorio y devuelve la ruta donde se encuentra
def clone_repo(url: str, base_dir: Path = Path("repos")) -> Path:
    # Asegura que existe la carpeta de todos los repositorios clonados
    base_dir.mkdir(parents=True, exist_ok=True)
    # Con "--depth 1" solo descarga el ultimo commit para agilizar, si es necesario historial commmits --> quitar
    subprocess.run(["git", "clone", "--depth", "1", url], cwd=base_dir, check=True)
    # Deduce el nombre de la carpeta que se acaba de crear para devolver ruta completa
    repo_name = url.rstrip("/").split("/")[-1].removesuffix(".git")
    return base_dir / repo_name


# Devuelve una lista de strings con las rutas relativas de cada fichero (incluido subcarpetas)
def build_file_index(root: Path, exts, ignored_dirs, ignored_files) -> tuple[list[str], list[str]]:
    exts_lower = {e.lower() for e in exts}
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
            if p.suffix.lower() in exts_lower:
                indexed_files.append(path_str)
            else:
                non_indexed_files.append(path_str)
    return indexed_files, non_indexed_files

async def main():
    args = parse_args()

    # 1. Cargar configuraciones
    whitelisted_exts = set(e.lower() for e in load_whitelist(Path("whitelist.yaml")))
    if not whitelisted_exts:
        print("❌ El fichero 'whitelist.yaml' no existe o está vacío. No hay nada que analizar.")
        return

    ignored_dirs, ignored_files = load_blacklist(Path("blacklist.yaml"))
    rules_map = load_rules(Path("rules"), allowed_extensions=whitelisted_exts)
    if not rules_map:
        print("❌ No se encontraron reglas para las extensiones especificadas en 'whitelist.yaml'.")
        return
    print(f"✅ {len(rules_map)} reglas de lenguaje cargadas según la whitelist.")

    for ext in whitelisted_exts:
        if ext not in rules_map:
            print(f"⚠️ Aviso: La extensión '{ext}' está en la whitelist pero no se encontró una regla para ella.")

    # 2. Obtener el código fuente
    if args.url:
        try:
            repo_root = clone_repo(args.url, Path("repos"))
        except subprocess.CalledProcessError:
            print("❌ La url del repositorio es incorrecta o no existe.")
            return
    else:
        if not args.directory or not args.directory.is_dir():
            print("❌ El directorio especificado no existe.")
            return
        repo_root = args.directory.resolve()

    # 3. Indexar ficheros
    file_index, non_indexed_files = build_file_index(repo_root, whitelisted_exts, ignored_dirs, ignored_files)
    if not file_index:
        print("❌ No se encontraron ficheros con las extensiones de la whitelist en el repositorio.")
        return

    # 4. Importar y ejecutar el agente
    from agent.pydantic_agent import Deps, analyzer, security_agent

    all_findings = []
    async with httpx.AsyncClient() as client:
        for file_path in file_index:
            file_ext = Path(file_path).suffix.lower()
            active_rule = rules_map.get(file_ext)

            if not active_rule:
                continue

            print(f"\n🔎 Analizando {file_path} con reglas para {active_rule.language}...")
            
            deps = Deps(
                repo_root=repo_root,
                file_index=file_path,
                analyzer=analyzer,
                active_rule=active_rule,
                http=client,
                selector=None,
            )
            
            instructions = (
                f"Analiza el fichero '{file_path}' usando las reglas de {active_rule.language}. "
                "Llama a `read_current_file` y luego a `analyze_code`."
            )

            try:
                result = await security_agent.run(instructions, deps=deps)
                findings_list: FindingsList = result.output
                findings = findings_list.__root__

                if findings:
                    for finding in findings:
                        all_findings.append(finding)
                    print(f"✅ Se encontraron {len(findings)} posibles problemas en {file_path}")
                else:
                    print(f"✔️ {file_path} analizado. No se encontraron problemas.")
            except json.JSONDecodeError:
                print(f"⚠️ No se pudo decodificar la respuesta para {file_path}. Salida: {result.output}")
            except Exception as e:
                print(f"❌ Error analizando {file_path}: {e}")

    # 5. Imprimir informe final
    if all_findings:
        plain_list = [asdict(f) for f in all_findings]
        json_text = json.dumps(plain_list, indent=2, ensure_ascii=False)
        print("\n--- INFORME FINAL ---")
        print(json_text)
    else:
        print("\n--- INFORME FINAL ---")
        print("✔️ No se encontraron vulnerabilidades en ningún fichero.")

    if non_indexed_files:
        print("\n--- FICHEROS NO ANALIZADOS (no en whitelist o en blacklist) ---")
        for file in non_indexed_files:
            print(f"- {file}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            pass
        else:
            raise


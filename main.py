import config
import argparse
import asyncio
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

import httpx
import tomli as tomllib

from deps.deps import FindingsList


# Extrae la lista de extensiones a comprobar
def load_whitelist(path: Path) -> list[str]:
    cfg = tomllib.loads(path.read_text(encoding="utf-8"))
    return cfg.get("whitelist", {}).get("extensions", [])


# Comprueba que existe al menos uno de los comandos y crea variables con los nombres sin guiones de su contenido
def parse_args():
    parser = argparse.ArgumentParser(description="JS Security Agent")

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
def build_file_index(root: Path, exts) -> list[str]:
    exts_lower = {e.lower() for e in exts}
    return [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts_lower]


async def main():
    # 1) Config LLM
    args = parse_args()

    # Clonamos repositorio o cogemos directamente el directorio
    if args.url:
        try:
            repo_root = clone_repo(args.url, Path("repos"))
        except subprocess.CalledProcessError:
            print("❌ La url es incorrecta")
            return

    else:
        if not args.directory or not args.directory.is_dir():
            print("❌ El directorio no existe")
            return
        else:
            print("Ruta correcta, comenzamos a escanear...")
        repo_root = args.directory.resolve()

    config_path = Path("pyproject.toml")
    if not config_path.exists():
        print("⚠ Warning: whitelist config not found, defaulting to .js/.ts")
        exts = [".js", ".ts"]
    else:
        exts = load_whitelist(config_path)

    file_index = build_file_index(repo_root, exts)
    if not file_index:
        print("❌ La url es incorrecta o no tiene ficheros para comprobar")
        return

    # Importamos el agente DESPUÉS de cargar .env (evitamos claves vacías)
    from agent.pydantic_agent import Deps, analyzer, security_agent, selector

    all_findings = []
    # Ejecutamos agente con deps (incluimos httpx.AsyncClient por futuras tools externas)
    async with httpx.AsyncClient() as client:
        for file_path in file_index:
            print(f"\n🔎 Analizando {file_path}...")
            # Pasamos solo el fichero actual al contexto del agente
            deps = Deps(
                repo_root=repo_root,
                file_index=file_path,
                selector=selector,
                analyzer=analyzer,
                http=client,
            )
            instructions = (
                f"Analiza el fichero '{file_path}'. "
                "Llama a read_local_file para leer su contenido y luego a analyze_with_dspy para analizarlo. "
                "Devuelve solo el JSON con los hallazgos."
            )
            try:
                result = await security_agent.run(instructions, deps=deps)

                # Ahora result.output es un FindingsList
                findings_list: FindingsList = result.output
                findings = findings_list.__root__  # lista de Finding
                if findings:
                    # Añadimos el nombre del fichero a cada hallazgo para tener contexto
                    for finding in findings:
                        all_findings.append(finding)
                    print(f"✅ Se encontraron {len(findings)} posibles problemas en {file_path}")
                else:
                    print(f"✔️ {file_path} analizado. No se encontraron problemas.")
            except json.JSONDecodeError:
                print(f"⚠️ No se pudo decodificar la respuesta para {file_path}. Salida: {result.output}")
            except Exception as e:
                print(f"❌ Error analizando {file_path}: {e}")

    # Imprimimos el resultado final
    if all_findings:
        # Convertimos cada instancia a dict y Serializamos a JSON
        plain_list = [asdict(f) for f in all_findings]
        json_text = json.dumps(plain_list, indent=2, ensure_ascii=False)

        print("--- INFORME FINAL ---")
        print(json_text)
    else:
        print("--- INFORME FINAL ---")
        print("✔️ No se encontraron vulnerabilidades en ningún fichero.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            pass  # lo ignoramos, ya hemos terminado
        else:
            raise

import httpx
import asyncio
import argparse
import subprocess
from pathlib import Path
from dotenv import load_dotenv

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
    #Deduce el nombre de la carpeta que se acaba de crear para devolver ruta completa
    repo_name = url.rstrip("/").split("/")[-1].removesuffix(".git")

    return base_dir / repo_name

# Devuelve una lista de strings con las rutas relativas de cada fichero (incluido subcarpetas) 
def build_file_index(root: Path, exts=(".js", ".ts")) -> list[str]:
    exts_lower = {e.lower() for e in exts}
    return [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts_lower]

async def main():
    # 1) Config LLM
    load_dotenv()
    args = parse_args()
    github_url = "https://github.com/rishipradeep-think41/gsuite-mcp/tree/master/src/"

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

    
    file_index = build_file_index(repo_root)
    if not file_index:
        print("❌ La url es incorrecta o no tiene ficheros para comprobar")
        return

    # Importamos el agente DESPUÉS de cargar .env (evitamos claves vacías)
    from agent.pydantic_agent import security_agent, Deps, selector, analyzer

    # Ejecutamos agente con deps (incluimos httpx.AsyncClient por futuras tools externas)
    async with httpx.AsyncClient() as client:
        deps = Deps(
            repo_root=repo_root,
            file_index=file_index,
            selector=selector,
            analyzer=analyzer,
            http=client,
        )
        instructions = (
            f"Analiza el repo que está en: {repo_root}. "
            "Lista los archivos con list_local_files, léelos con read_local_file y llama a analyze_with_dspy. "
            "Devuelve un JSON final con todos los hallazgos."
        )
        result = await security_agent.run(instructions, deps=deps)
        print(result.output)

if __name__ == "__main__":
    asyncio.run(main())
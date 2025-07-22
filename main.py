import asyncio
import json
from dotenv import load_dotenv
import dspy

from prompts.signatures import FileDiscovery, JSStaticAnalysis
from tools.github_utils import (
    parse_github_url,
    coerce_paths,
    list_files_from_github_api,
    download_raw_file,
)

# 1) Config LLM
load_dotenv()
lm = dspy.LM('openai/gpt-4o-mini', api_key="")
dspy.configure(lm=lm)

# 2) Instantiate modules AFTER configure
selector = dspy.ChainOfThought(FileDiscovery)
analyzer = dspy.ReAct(JSStaticAnalysis, tools=[])  # sin tools externas por ahora

def pretty_print_report(filename: str, findings: list[dict]):
    critical = [f for f in findings if f.get('severity') == 'CRITICAL']
    warnings = [f for f in findings if f.get('severity') == 'WARNING']
    print(f"🔍 {filename}")
    print(f"   CRITICAL: {len(critical)} | WARNING: {len(warnings)}")
    for f in findings:
        sev = f.get('severity', '?')
        print(f"  - [{sev}] {f.get('issue', 'Sin título')}")
        print(f"    Explicación: {f.get('explanation', '')}")
        if rec := f.get('recommendation'):
            print(f"    Mitigación: {rec}")
        if lh := f.get('line_hint'):
            print(f"    Línea: {lh}")

async def main():
    github_url = "https://github.com/rishipradeep-think41/gsuite-mcp/tree/master/src/"
    gh_token = ""  # opcional

    # 1) Obtener lista REAL de archivos .js/.ts mediante la API
    owner, repo, branch, base_path = parse_github_url(github_url)
    all_files = await list_files_from_github_api(owner, repo, branch, base_path, token=gh_token)
    if not all_files:
        print("No se encontraron ficheros .js/.ts en la ruta indicada")
        return

    # 2) (Opcional) Dejar que el LLM elija: si no quieres filtrado, comenta esto y usa todos
    sel = selector(github_url=github_url, include_patterns=".js,.ts")
    file_paths = coerce_paths(sel.file_paths) if sel.file_paths else [p for p, _ in all_files]

    # 3) Filtrar la selección contra lo que realmente existe
    lookup = {p: raw for p, raw in all_files}
    chosen = [(p, lookup[p]) for p in file_paths if p in lookup]
    if not chosen:
        print("El modelo no eligió rutas válidas; analizaremos todas.")
        chosen = all_files

    # 4) Descargar y analizar
    for path, raw_url in chosen:
        try:
            code = await download_raw_file(raw_url)
        except Exception as e:
            print(f"❌ No pude descargar {path}: {e}")
            continue
        result = analyzer(js_code=code, filename=path)
        try:
            findings = json.loads(result.findings_json)
        except Exception:
            print(f"⚠️ Salida no JSON para {path}:{result.findings_json}")
            continue
        pretty_print_report(path, findings)

if __name__ == "__main__":
    asyncio.run(main())
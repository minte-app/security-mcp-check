import os
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
import dspy
# import logfire
from deps.deps import Deps, FindingsList
from prompts.signatures import FileDiscovery, JSStaticAnalysis, PromptComposer

# DSPy config
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Falta OPENAI_API_KEY en .env")

logfire_token = os.getenv("LOGFIRE_TOKEN")
if not logfire_token:
    raise RuntimeError("Falta LOGFIRE_TOKEN en .env")

# LOGFIRE: Podemos pasar la clave directamnte, o dejarlo vacio para que la coja de .logfire                                                       │
# logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))
# logfire.instrument_pydantic_ai()   

lm = dspy.LM('openai/gpt-4o-mini', api_key=api_key)
dspy.configure(lm=lm)

# Módulos DSPy
selector = dspy.ChainOfThought(FileDiscovery)
analyzer = dspy.ReAct(JSStaticAnalysis, tools=[])  # sin tools externas por ahora
prompter = dspy.Predict(PromptComposer)

# Agente Pydantic AI
security_agent = Agent(  
    'openai:gpt-4o-mini',
    deps_type=Deps,
    output_type=FindingsList,
)

@security_agent.system_prompt
async def system_prompt(ctx : RunContext[Deps]) -> str:

    mission = "Evaluar fallos de seguridad en código JS/TS del repo local."
    severity_policy = (
        "CRITICAL = escalada de privilegios, RCE, exfiltración de datos, eval/Function con input externo, "
        "inyecciones peligrosas, secrets hardcodeados. WARNING = el resto."
    )

    # Prepara inputs para el composer: limita para no saturar y junta en único string con saltos de linea 
    files = ctx.deps.file_index[:80]  # evita meter miles de líneas
    file_block = "\n".join(files)

    output_contract = (
        "Devuelve un JSON array: [{file_path, issue, severity, explanation, recommendation, line_hint?}]. "
        "Nada más que el JSON, sin texto adicional."
    )
    tools_hint = (
        "Tools disponibles:\n"
        "- list_local_files(): devuelve la lista de paths.\n"
        "- read_local_file(path): devuelve el código del archivo.\n"
        "- analyze_with_dspy(filename, code): analiza y devuelve hallazgos JSON."
    )

    res = prompter(
        mission=mission,
        file_list=file_block,
        severity_policy=severity_policy,
        output_contract=output_contract,
        tools_hint=tools_hint,
    )
    return res.system_prompt

# TOOLS 
@security_agent.tool
async def list_local_files(ctx: RunContext[Deps]) -> list[str]:
    """Devuelve la lista de archivos JS/TS disponibles localmente."""
    return ctx.deps.file_index

@security_agent.tool
async def read_local_file(ctx: RunContext[Deps], path: str) -> str:
    """Lee y devuelve el código de un archivo local (ruta relativa)."""
    if path not in ctx.deps.file_index:
        raise ValueError(f"El archivo {path} no está en el índice.")
    
    plain_text = (ctx.deps.repo_root / path).read_text(encoding="utf-8", errors="ignore")
    return plain_text

@security_agent.tool
async def analyze_with_dspy(ctx: RunContext[Deps], filename: str, code: str) -> str:
    """Ejecuta el análisis DSPy y devuelve el JSON de hallazgos."""
    result = ctx.deps.analyzer(js_code=code, filename=filename)
    return result.findings_json

# (Opcional) usar FileDiscovery para filtrar por patrones
@security_agent.tool
async def discover_files(ctx: RunContext[Deps], include_patterns: str = ".js,.ts") -> list[str]:
    """Filtra file_index con la signature FileDiscovery (o en Python si quieres)."""
    all_files_text = "".join(ctx.deps.file_index)
    try:
        out = dspy.Predict(FileDiscovery)(
            all_files=all_files_text,
            include_patterns=include_patterns
        )
        return out.file_paths
    except Exception:
        patterns = [p.strip().lower() for p in include_patterns.split(',') if p.strip()]
        return [f for f in ctx.deps.file_index if any(f.lower().endswith(ext) for ext in patterns)]
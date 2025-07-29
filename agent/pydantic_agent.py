import os

import dspy
from pydantic_ai import Agent, RunContext

from deps.deps import Deps, FindingsList
from prompts.signatures import StaticCodeAnalysis, PromptComposer

# DSPy config
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Falta OPENAI_API_KEY en .env")

logfire_token = os.getenv("LOGFIRE_TOKEN")
if not logfire_token:
    raise RuntimeError("Falta LOGFIRE_TOKEN en .env")

lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
dspy.configure(lm=lm)

# Módulos DSPy
analyzer = dspy.ReAct(StaticCodeAnalysis, tools=[])
prompter = dspy.Predict(PromptComposer)

# Agente Pydantic AI
security_agent = Agent(
    "openai:gpt-4o-mini",
    deps_type=Deps,
    output_type=FindingsList,
)

@security_agent.system_prompt
async def system_prompt(ctx: RunContext[Deps]) -> str:
    rule = ctx.deps.active_rule
    if not rule:
        # Fallback por si no hay regla específica
        mission = "Evaluar fallos de seguridad en el fichero proporcionado."
        lang_instructions = "Analiza en busca de vulnerabilidades comunes como inyección de código, XSS, secretos hardcodeados, etc."
    else:
        mission = f"Evaluar fallos de seguridad en un fichero de {rule.language}."
        lang_instructions = rule.prompt

    output_contract = (
        "Devuelve un JSON array: [{file_path, issue, severity, explanation, recommendation, line_hint?}]. "
        "Nada más que el JSON, sin texto adicional."
    )
    tools_hint = (
        "Tools disponibles:\n"
        "- read_current_file(): devuelve el código del archivo que se está analizando.\n"
        "- analyze_code(code): analiza el código y devuelve hallazgos en formato JSON."
    )

    res = prompter(
        mission=mission,
        file_list=f"Fichero a analizar: {ctx.deps.file_index}", # Ahora solo es un fichero
        severity_policy=lang_instructions, # Las reglas de severidad ahora son parte del prompt del lenguaje
        output_contract=output_contract,
        tools_hint=tools_hint,
    )
    return res.system_prompt


# TOOLS
@security_agent.tool
async def read_current_file(ctx: RunContext[Deps]) -> str:
    """Lee y devuelve el código del archivo que se está analizando actualmente."""
    file_path = ctx.deps.repo_root / ctx.deps.file_index
    if not file_path.exists():
        raise ValueError(f"El archivo {ctx.deps.file_index} no existe.")

    return file_path.read_text(encoding="utf-8", errors="ignore")


@security_agent.tool
async def analyze_code(ctx: RunContext[Deps], code: str) -> str:
    """Ejecuta el análisis DSPy sobre el código y devuelve el JSON de hallazgos."""
    rule = ctx.deps.active_rule
    instructions = rule.prompt if rule else ""
    
    result = ctx.deps.analyzer(
        code=code, 
        filename=ctx.deps.file_index,
        language_instructions=instructions
    )
    return result.findings_json


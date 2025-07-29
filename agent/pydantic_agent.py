import os

import dspy
from pydantic_ai import Agent, RunContext

from deps.deps import Deps, FindingsList
from prompts.signatures import StaticCodeAnalysis, PromptComposer

# DSPy config
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY is missing from .env")

logfire_token = os.getenv("LOGFIRE_TOKEN")
if not logfire_token:
    raise RuntimeError("LOGFIRE_TOKEN is missing from .env")

lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
dspy.configure(lm=lm)

# DSPy Modules
analyzer = dspy.ReAct(StaticCodeAnalysis, tools=[])
prompter = dspy.Predict(PromptComposer)

# Pydantic AI Agent
security_agent = Agent(
    "openai:gpt-4o-mini",
    deps_type=Deps,
    output_type=FindingsList,
)

@security_agent.system_prompt
async def system_prompt(ctx: RunContext[Deps]) -> str:
    rule = ctx.deps.active_rule
    if not rule:
        # Fallback if no specific rule is found
        mission = "Evaluate security vulnerabilities in the provided file."
        lang_instructions = "Analyze for common vulnerabilities like code injection, XSS, hardcoded secrets, etc."
    else:
        mission = f"Evaluate security vulnerabilities in a {rule.language} file."
        lang_instructions = rule.prompt

    output_contract = (
        "Return a JSON array: [{file_path, issue, severity, explanation, recommendation, line_hint?}]. "
        "Nothing but the JSON, with no additional text."
    )
    tools_hint = (
        "Available tools:\n"
        "- read_current_file(): returns the code of the file currently being analyzed.\n"
        "- analyze_code(code): analyzes the code and returns findings in JSON format."
    )

    res = prompter(
        mission=mission,
        file_list=f"File to analyze: {ctx.deps.file_index}",
        severity_policy=lang_instructions, # Severity rules are now part of the language prompt
        output_contract=output_contract,
        tools_hint=tools_hint,
    )
    return res.system_prompt


# TOOLS
@security_agent.tool
async def read_current_file(ctx: RunContext[Deps]) -> str:
    """Reads and returns the code of the file currently being analyzed."""
    file_path = ctx.deps.repo_root / ctx.deps.file_index
    if not file_path.exists():
        raise ValueError(f"File {ctx.deps.file_index} does not exist.")

    return file_path.read_text(encoding="utf-8", errors="ignore")


@security_agent.tool
async def analyze_code(ctx: RunContext[Deps], code: str) -> str:
    """Runs the DSPy analysis on the code and returns the JSON of findings."""
    rule = ctx.deps.active_rule
    instructions = rule.prompt if rule else ""
    
    result = ctx.deps.analyzer(
        code=code, 
        filename=ctx.deps.file_index,
        language_instructions=instructions
    )
    return result.findings_json
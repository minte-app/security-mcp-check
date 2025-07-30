import dspy


class FileDiscovery(dspy.Signature):
    """Filters a list of files based on patterns (.js, .ts, etc.). Do not invent paths."""

    all_files: str = dspy.InputField(desc="Complete list of relative paths, one per line")
    include_patterns: str = dspy.InputField(desc="Patterns to include, e.g., .js,.ts", default=".js,.ts")
    file_paths: list[str] = dspy.OutputField(desc="JSON array of paths to audit")


class StaticCodeAnalysis(dspy.Signature):
    """Analyzes a source code file and returns a structured report.

    **findings_json** must be a **JSON array** where each element is an object with:
      - issue: brief title of the problem
      - severity: "CRITICAL" or "WARNING"
      - explanation: why it is a problem
      - recommendation: how to mitigate it
      - line_hint (optional): relevant line or snippet
    """

    code: str = dspy.InputField(desc="Source code of the file to analyze")
    filename: str = dspy.InputField(desc="Repo-relative path of the file")
    language_instructions: str = dspy.InputField(desc="Specific instructions for the language")
    findings_json: str = dspy.OutputField(desc="JSON array of findings with severity CRITICAL/WARNING")


class PromptComposer(dspy.Signature):
    """Creates the system_prompt for the JS/TS security agent."""

    mission: str = dspy.InputField(desc="What the agent should do")
    file_list: str = dspy.InputField(desc="(Truncated) list of available files, one per line")
    severity_policy: str = dspy.InputField(desc="Rules for classifying as CRITICAL vs. WARNING")
    output_contract: str = dspy.InputField(desc="Exact format of the expected output")
    tools_hint: str = dspy.InputField(desc="What tools are available and what they are for")
    system_prompt: str = dspy.OutputField()

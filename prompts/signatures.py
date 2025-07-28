import dspy


class FileDiscovery(dspy.Signature):
    """Filtra un listado de archivos según patrones (.js,.ts, etc.). No inventes rutas."""

    all_files: str = dspy.InputField(desc="Listado completo de paths relativos, uno por línea")
    include_patterns: str = dspy.InputField(desc="Patrones a incluir, ej: .js,.ts", default=".js,.ts")
    file_paths: list[str] = dspy.OutputField(desc="JSON array de paths a auditar")


class JSStaticAnalysis(dspy.Signature):
    """Analiza un archivo JS/TS y devuelve un reporte estructurado.

    **findings_json** debe ser un **array JSON** donde cada elemento es un objeto con:
      - issue: breve título del problema
      - severity: "CRITICAL" o "WARNING" (CRITICAL = escalada de privilegios, exfiltración de datos,
        RCE, inyecciones peligrosas, uso de `eval`/`Function` sobre input externo, secrets hardcodeados, etc.)
      - explanation: por qué es un problema
      - recommendation: cómo mitigarlo
      - line_hint (opcional): línea o fragmento relevante
    """

    js_code: str = dspy.InputField(desc="JavaScript/TypeScript source code")
    filename: str = dspy.InputField(desc="Repo-relative path of the file")
    findings_json: str = dspy.OutputField(desc="JSON array of findings with severity CRITICAL/WARNING")


class PromptComposer(dspy.Signature):
    """Crea el system_prompt para el agente de seguridad JS/TS."""

    mission: str = dspy.InputField(desc="Qué debe hacer el agente")
    file_list: str = dspy.InputField(desc="Lista (truncada) de archivos disponibles, uno por línea")
    severity_policy: str = dspy.InputField(desc="Reglas cómo clasificar en CRITICAL vs WARNING")
    output_contract: str = dspy.InputField(desc="Formato exacto del output esperado")
    tools_hint: str = dspy.InputField(desc="Qué tools hay y para qué sirven")
    system_prompt: str = dspy.OutputField()

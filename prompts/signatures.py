# prompts/signatures.py
import dspy

class FileDiscovery(dspy.Signature):
    """Tarea: dado un enlace público de GitHub (puede ser repo raíz, un directorio `tree/...` o un archivo `blob/...`),
    devuelve **únicamente** los ficheros JavaScript/TypeScript que deben auditarse por seguridad.

    **Requisitos del output (`file_paths`):**
    - Debe ser un **array JSON puro de strings**, sin texto extra ni fences. Ejemplo: ["src/index.ts", "src/utils/helpers.js"].
    - Cada string es una **ruta relativa al repo**, nunca URLs completas.
    - Si la URL apunta a un solo archivo, devuelve sólo ese path dentro del array.
    - Si dudas de la existencia de un fichero, **omite** en vez de inventarlo.
    - Filtra sólo por las extensiones indicadas en `include_patterns`.
    - No incluyas README, tests ni assets estáticos si no contienen JS/TS ejecutable.

    Puedes razonar paso a paso internamente, pero el valor final de `file_paths` debe cumplir estrictamente el formato anterior.
    """
    github_url: str = dspy.InputField(desc="URL de GitHub que apunta a un repo, directorio o archivo")
    include_patterns: str = dspy.InputField(desc="Extensiones/globs a incluir, separadas por comas", default=".js,.ts")
    file_paths: list[str] = dspy.OutputField(desc="Array JSON con rutas relativas reales a analizar")

class JSStaticAnalysis(dspy.Signature):
    """Analiza un archivo JS/TS y devuelve un reporte estructurado.

    **findings_json** debe ser un **array JSON** donde cada elemento es un objeto con:
      - issue: breve título del problema
      - severity: "CRITICAL" o "WARNING" (CRITICAL = escalada de privilegios, RCE, exfiltración de datos, inyecciones peligrosas, uso de `eval`/`Function` sobre input externo, secrets hardcodeados, etc.)
      - explanation: por qué es un problema
      - recommendation: cómo mitigarlo
      - line_hint (opcional): línea o fragmento relevante
    """
    js_code: str = dspy.InputField(desc="JavaScript/TypeScript source code")
    filename: str = dspy.InputField(desc="Repo-relative path of the file")
    findings_json: str = dspy.OutputField(desc="JSON array of findings with severity CRITICAL/WARNING")
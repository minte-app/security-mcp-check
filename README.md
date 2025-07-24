# JS Security Agent

> Agente híbrido (Pydantic AI + DSPy) para detectar fallos de seguridad en código **JavaScript/TypeScript** dentro de un repositorio de GitHub.

---

## 🎯 Objetivo

Automatizar, de forma **simple y reproducible**, la revisión de seguridad básica en archivos `.js` y `.ts` de un proyecto. El agente:

1. **Clona** (o usa) un repo local.
2. **Indexa** los archivos de interés.
3. **Genera dinámicamente** su `system_prompt` con DSPy.
4. **Lee y analiza** cada fichero con un módulo ReAct de DSPy.
5. Devuelve un **JSON con hallazgos clasificados** en `CRITICAL` o `WARNING`.

---

## 🧱 Stack técnico

* **Python 3.10+**
* **Pydantic AI**: orquestación del agente y herramientas (tools).
* **DSPy**: firmas (signatures) y módulos LLM (`Predict`, `ChainOfThought`, `ReAct`).
* **LiteLLM / OpenAI**: backend LLM. (Modelos probados: `gpt-4o-mini`).
* **Git CLI**: para clonar repos (shallow clone).
* **httpx**: cliente HTTP async (futuras extensiones).
* **dotenv**: gestión de variables de entorno.
* **Logfire (opcional)**: trazas y telemetría.

---

## 📂 Estructura mínima del proyecto

```
js-security-agent/
├─ agent/
│  └─ pydantic_agent.py
├─ deps/
│  └─ deps.py
├─ prompts/
│  └─ signatures.py
├─ config.py
├─ main.py
├─ repos/              # aquí se clonan los repos
├─ requirements.txt
├─ .env.example
└─ .gitignore
```

---

## ⚙️ Instalación

1. **Clona este repo** (o copia los 4 ficheros principales).
2. **Crea y activa un entorno virtual**:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/Mac
   .venv\Scripts\activate      # Windows
   ```
3. **Instala dependencias**:

   ```bash
   pip install -r requirements.txt
   ```
4. **Configura el `.env`**:

   * Duplica `.env.example` → `.env`.
   * Añade tu clave de OpenAI (sin comillas):

     ```
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
     ```
   * (Opcional) Logfire:

     ```
     LOGFIRE_TOKEN=lfu_xxxxxxxxxxxxxxxxxxxxxx
     ```

---

## 🚀 Uso

### Opción A: Clonar desde URL

```bash
python main.py --url https://github.com/usuario/repositorio
```

* Acepta la **raíz del repo** (no uses `/tree/...` ni `/blob/...`).
* El repo se clona dentro de `repos/`.

### Opción B: Usar un directorio ya clonado

```bash
python main.py --directory repos/mi-repo
```

> Los parámetros `--url` y `--directory` son **mutuamente excluyentes**.

### Salida

En consola verás el JSON de hallazgos, algo como:

```json
[
  {
    "issue": "Sensitive Data Exposure",
    "severity": "CRITICAL",
    "explanation": "Variables de entorno con claves expuestas en logs",
    "recommendation": "Sanitizar errores y ocultar credenciales",
    "line_hint": 42
  }
]
```

---

## 🧠 Cómo funciona internamente

1. **CLI / main.py**

   * Parsea args (`--url` o `--directory`).
   * Clona el repo (si procede) y crea un índice de archivos (`build_file_index`).
   * Crea las **Deps** (dataclass) que se le pasan al agente.

2. **Deps (deps.py)**

   * Guarda: ruta del repo, lista de ficheros, módulos DSPy (`selector`, `analyzer`), cliente HTTP, etc.

3. **DSPy Signatures (signatures.py)**

   * `FileDiscovery` (opcional): filtrar archivos por patrones.
   * `FileSelection`: priorizar qué revisar si son muchos.
   * `JSStaticAnalysis`: define el contrato de salida (JSON, severidades...).
   * `PromptComposer`: compone el system prompt dinámico.

4. **Agente (agent/pydantic\_agent.py)**

   * Configura DSPy (`dspy.configure(lm=...)`).
   * Instancia los módulos DSPy: `ChainOfThought`, `ReAct`, `Predict`.
   * Define el `security_agent = Agent(...)`.
   * `@security_agent.system_prompt`: genera el prompt con `PromptComposer`.
   * Tools expuestas:

     * `list_local_files()`
     * `read_local_file(path)`
     * `analyze_with_dspy(filename, code)`
     * `discover_files(include_patterns)` (opcional)

5. **Flujo de ejecución**

   * El agente recibe instrucciones (`instructions` en `main.py`).
   * Usa tools para listar y leer archivos.
   * Llama al módulo `analyzer` (ReAct) para cada fichero.
   * Devuelve un JSON consolidado.

---

## 🔐 Política de severidades

* **CRITICAL**: RCE, escalada de privilegios, exfiltración de datos, `eval()/Function()` con input externo, inyección peligrosa, secrets hardcodeados.
* **WARNING**: resto de problemas (falta de validación, DoS potencial, error handling inseguro, etc.).

---

## 🛠️ Extender / Personalizar

* **Otros lenguajes**: cambia `exts` en `build_file_index` y ajusta la signature.
* **Más reglas de seguridad**: amplía `JSStaticAnalysis` y/o agrega un post-procesado.
* **Herramientas extra**: añade tools para ejecutar linters, consultar APIs, etc.
* **Optimización del prompt**: usa DSPy `MIPROv2`, `BootstrapFewShot`, etc. para refinar prompts/razonamientos.

---

## ❗ Troubleshooting

| Problema                                                                         | Causa / Solución                                                                        |
| -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `fatal: repository ... not found`                                                | La URL incluye `/tree/...`. Usa la raíz del repo.                                       |
| `❌ La url es incorrecta o no tiene ficheros`                                     Repo vacío o sin `.js/.ts`. Comprueba la ruta y extensiones.                            |
| `PydanticSchemaGenerationError`                                                  | Estabas usando `BaseModel` con tipos arbitrarios. Cambiado a `@dataclass`.              |
| `TypeError: OpenAIModel.__init__() got an unexpected keyword argument 'api_key'` | En tu versión de pydantic-ai no se pasa api\_key en el constructor. Quita el parámetro. |
| `AuthenticationError 401`                                                        | Clave OpenAI inválida o con comillas en `.env`. Usa `sk-...` y sin comillas.            |
| `No user tokens are available. Please run 'logfire auth'`                        | No tienes token de Logfire. Comenta la configuración o autentícate.                     |

---

## 📄 Licencia / Disclaimer

Este agente es una **herramienta educativa**. No sustituye una auditoría profesional ni garantiza la ausencia de vulnerabilidades. Úsalo bajo tu propia responsabilidad y cumpliendo con las políticas de uso de los repositorios que analices.

---

## 🙋‍♂️ Preguntas

¿Quieres automatizar la corrección? ¿Cambiar el motor LLM? ¿Integrarlo en CI/CD? Abre un issue o pregúntame.

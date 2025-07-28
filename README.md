<p align="center"><a href="https://minte.app/es" target="_blank"><img src="http://www.w3.org/2000/svg" width="400" alt="Security-Check Logo"></a></p>

<p align="center">
<a href="https://opensource.org/license/MIT"><img src="https://img.shields.io/packagist/l/laravel/framework" alt="License"></a>
</p>

# MCP Security Check

> An AI‑driven agent that scans the entire MCP codebase, evaluates potential security issues, and produces a comprehensive final report.
---

## 🎯 Features

- **Dependency Management:** Uses [UV](https://docs.astral.sh/uv/guides/install-python/) as the Python package manager.
- **Formatting & Linting:** Integrates [Ruff](https://github.com/astral-sh/ruff) for code quality checks and autoformatting.
- **Extensible Whitelist:** Configurable list of file extensions to analyze (e.g., `.js`, `.ts`, and future Python MCP).
- **AI Modules:** Leverages DSPy signatures (`ChainOfThought`, `ReAct`, `Predict`) for prompt composition and static analysis.
- **Asynchronous Execution:** Structure built on `asyncio` and `httpx.AsyncClient` for future HTTP integrations.
- **JSON Output:** Final report serialized as pure JSON array for easy downstream consumption.

---

## 📂 Project Structure

```
security-mcp-check/
├─ agent/
│  └─ pydantic_agent.py
├─ deps/
│  └─ deps.py
├─ prompts/
│  └─ signatures.py
├─ config.py
├─ main.py
├─ repos/              # here the cloned repos
├─ requirements.txt
├─ .env.example
└─ .gitignore
└─ pyproject.toml
```
---

## ⚙️ Installation

1. **Install UV and Ruff** (package manager):
   ```bash
   pip install uv-cli
   uv install
   uv tool install ruff@latest
   ```
2. **Clone this repo** and enter its directory:
   ```bash
   git clone https://github.com/your_org/security-mcp-check.git
   cd security-mcp-check
   ```
3. **Activate virtual environment** and install dependencies:
   ```bash
   uv venv .venv       # create and activate a venv
   uv install          # installs from pyproject.toml
   ```
4. **Configure environment**:
   - Copy `.env.example` to `.env`.
   - Fill in your OpenAI key:
     ```ini
     OPENAI_API_KEY=sk-...
     ```
   - (Optional) Logfire token:
     ```ini
     LOGFIRE_TOKEN=lfu-...
     ```
---
## 🚀 Usage
```bash
# Clone a repo by URL
python main.py --url https://github.com/user/repo

# Or use an existing local clone
python main.py --directory repos/user_repo
```

The CLI supports two mutually exclusive options: `--url` or `--directory`. The agent will index files matching the whitelist in `ruff.toml` (e.g. `.js`, `.ts`), analyze each, and print a JSON report.

## Configuration
- **Whitelisted extensions**: Edit `pyproject.toml` under `[whitelist]` with `extend-select` or a custom section:
  ```toml
  [whitelist]
  extensions = [".js", ".ts", ".py"]  
  ```
- **Ruff rules**: Add or disable rules in `pyproject.toml`.

## JSON Report Schema
Each finding in the array has:
```json
{
  "file_path": "src/file.js",
  "issue": "Hardcoded credentials",
  "severity": "CRITICAL",
  "explanation": "...","
  "recommendation": "...","
  "line_hint": 42
}
```
---

## 🔐 Severiry police
- **CRITICAL**: Remote code execution (RCE), privilege escalation, data exfiltration, use of `eval()/Function()` with external input, dangerous injection patterns, hardcoded secrets.
- **WARNING**: All other issues (missing input validation, potential Denial of Service, insecure error handling, etc.).

---

## ❗ Troubleshooting

| Trouble                                                                          | Solution                                                        |
| -------------------------------------------------------------------------------- | ---------------------------------------------------------------|
| `fatal: repository ... not found`                                                | Use only the repo root URL, not `/tree/` or `/blob/` paths.    |
| `❌ Incorrect url`                                                               | Empty repo. Ensure the path and extensions.                    |
| `PydanticSchemaGenerationError`                                                  | You were using `BaseModel`, change to `@dataclass`.            |
| `AuthenticationError 401`                                                        | Ensure `OPENAI_API_KEY` has no quotes and is valid.            |
| `No user tokens are available. Please run 'logfire auth'`                        | Do not have a Logfire.                                         |

---

## 📄 License / Disclaimer
This security agent is open-sourced software licensed under the [MIT license](https://opensource.org/licenses/MIT).

# MCP Security Check

<p align="center">
<a href="https://opensource.org/license/MIT"><img src="https://img.shields.io/packagist/l/laravel/framework" alt="License"></a>
</p>

> An AI-driven agent that scans local or remote codebases, evaluates potential security issues based on extensible, OWASP Top 10-guided rules, and produces a comprehensive Markdown report.

---

### 📖 Full Documentation

For a deep dive into the project's architecture, functionality, and a detailed guide, please see the 
**[Full Explanation and Guide (explanation.md)](./explanation.md)**.

---

## 🎯 Features

- **Flexible Code Analysis:** Scan repositories from a GitHub URL or a local directory.
- **OWASP Top 10 Guided:** The analysis prompts are based on the official OWASP Top 10 to ensure relevant and high-quality findings.
- **Extensible Rule System:** Define analysis rules for different programming languages. Each language has its own configuration and prompt instructions.
- **Centralized Configuration:** Precisely control which files and directories to analyze using a single `config.yaml` file.
- **Markdown Reporting:** Generates a clear, easy-to-read security report in Markdown format, including severity levels and recommendations.
- **Asynchronous by Design:** Built with `asyncio` and `httpx` for efficient, non-blocking analysis.

---

## 📂 Project Structure

```
security-mcp-check/
├─ agent/                # Core AI agent logic
│  ├─ pydantic_agent.py
│  └─ rules.py
├─ deps/                 # Dependency injection and data models
│  └─ deps.py
├─ prompts/              # AI prompt-related utilities
│  └─ signatures.py
├─ reports/              # Output directory for generated Markdown reports
├─ repos/                # Default directory for cloned remote repositories
├─ rules/                # Language-specific analysis rules
│  ├─ javascript/
│  │  ├─ config.yaml
│  │  └─ prompt.md
│  └─ python/
│     ├─ config.yaml
│     └─ prompt.md
├─ .env.example          # Environment variable template
├─ .gitignore
├─ config.py             # Configuration loader
├─ config.yaml           # Whitelist and blacklist configuration
├─ explanation.md        # Detailed project documentation
├─ main.py               # Main script entrypoint
├─ pyproject.toml
├─ README.md
└─ requirements.txt
```

---

## ⚙️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/security-mcp-check.git
    cd security-mcp-check
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    -   Copy `.env.example` to `.env`.
    -   Fill in your OpenAI API key:
        ```ini
        OPENAI_API_KEY=sk-...
        ```

---

## 🚀 Usage

The agent can be run from the command line with a GitHub URL or a local directory path.

-   **Analyze a remote repository:**
    ```bash
    python main.py --url https://github.com/user/repo
    ```

-   **Analyze a local repository:**
    ```bash
    python main.py --directory repos/user_repo
    ```

The agent will perform the analysis and generate a security report in the `reports/` directory.

---

## 🔧 Configuration

All configuration is handled in `config.yaml`:

-   **`whitelist`**: Defines which file extensions the agent should analyze.
-   **`blacklist`**: Specifies directories and files to be completely ignored.

Example `config.yaml`:
```yaml
whitelist:
  extensions: [".js", ".ts", ".py"]

blacklist:
  directories:
    - "node_modules"
    - "dist"
  files:
    - "package-lock.json"
```

-   **Language Rules:** Add or modify rules in the `rules/` directory. For each language, you need a `config.yaml` and a `prompt.md`.

---

## 🤖 Agent Tools

The AI agent has access to a set of tools to perform its analysis. These tools are called internally by the agent based on its instructions.

-   **`read_current_file()`**: Reads the content of the file currently being analyzed.
-   **`analyze_code(code: str)`**: Triggers the security analysis on the provided code string and returns a list of findings.
---

## 📄 Report Schema

The final report is a Markdown file. Each finding in the report includes:

-   **File Path:** The path to the file where the issue was found.
-   **Severity:** The severity of the issue (`CRITICAL` or `WARNING`), highlighted with color.
-   **Issue:** A brief description of the vulnerability.
-   **Explanation:** A more detailed explanation of the issue.
-   **Recommendation:** A suggestion on how to fix the vulnerability.
-   **Line Hint:** The line number where the issue was detected.

---

## 🔐 Severity Policy

The analysis is guided by the principles of the **OWASP Top 10**. Findings are categorized as follows:

-   **CRITICAL**: Issues that could lead to severe security breaches (RCE, SQLi, hardcoded secrets, etc.).
-   **WARNING**: All other security issues (insecure error handling, missing validation, etc.).

---

## 📄 License

This project is open-sourced software licensed under the [MIT license](https://opensource.org/licenses/MIT).

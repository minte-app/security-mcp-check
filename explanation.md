# AI Security Agent: Explanation and Guide

This document provides a detailed explanation of the AI Security Agent, its architecture, and how to use and extend it.

## 1. How It Works

The AI Security Agent is a tool designed to automatically scan codebases for potential security vulnerabilities. It operates as follows:

1.  **Initialization**: The agent starts by reading its configuration from `config.yaml`, which specifies which file extensions to analyze (`whitelist`) and which files and directories to ignore (`blacklist`).

2.  **Code Retrieval**: The user provides a target codebase, either as a remote GitHub URL or a local directory path. If a URL is provided, the agent clones the repository into the `repos/` directory.

3.  **File Indexing**: The agent scans the target directory and builds a list of files to be analyzed, based on the `whitelist` and `blacklist` settings.

4.  **Rule Loading**: The agent loads language-specific analysis rules from the `rules/` directory. Each language has a subdirectory containing a `config.yaml` (defining the language name and file extensions) and a `prompt.md` (containing instructions for the AI).

5.  **AI-Powered Analysis**: For each file in the index, the agent:
    a.  Selects the appropriate language rule based on the file extension.
    b.  Uses an AI model (powered by DSPy and Pydantic AI) to analyze the code. The AI is instructed by a system prompt that is dynamically composed using the information from the language-specific `prompt.md`.
    c.  The agent uses a set of tools to perform the analysis:
        -   `read_current_file()`: Reads the content of the file.
        -   `analyze_code(code: str)`: Submits the code to the AI for analysis and receives a list of findings.

6.  **Report Generation**: After analyzing all files, the agent generates a comprehensive security report in Markdown format. The report is saved in the `reports/` directory and includes a list of all findings, their severity, and recommendations for mitigation.

## 2. Project Structure

Here is a breakdown of the key files and directories in the project:

-   `main.py`: The main entry point of the application. It handles command-line arguments, orchestrates the analysis process, and generates the final report.

-   `config.py`: This module is responsible for loading all configurations from `config.yaml`, including the whitelist, blacklist, and other settings. It also contains the logic for generating the Markdown report.

-   `config.yaml`: The central configuration file. Here you can define the `whitelist` of file extensions to be analyzed and the `blacklist` of directories and files to be ignored.

-   `agent/`: This directory contains the core logic of the AI agent.
    -   `pydantic_agent.py`: Defines the AI agent, its system prompt, and the tools it can use (`read_current_file`, `analyze_code`).
    -   `rules.py`: Contains the logic for loading the language-specific analysis rules from the `rules/` directory.

-   `deps/`: This directory defines the data structures used throughout the application.
    -   `deps.py`: Contains the Pydantic models for `Finding`, `FindingsList`, and the `Deps` object that is used for dependency injection in the agent.

-   `prompts/`: This directory contains the DSPy signatures that define the structure of the prompts used to interact with the AI.
    -   `signatures.py`: Defines the `StaticCodeAnalysis` and `PromptComposer` signatures, which are used to structure the input and output of the AI model.

-   `rules/`: This directory contains the language-specific rules for the analysis. You can extend the agent by adding new subdirectories here. Each subdirectory should contain:
    -   `config.yaml`: Specifies the language name and the file extensions it applies to.
    -   `prompt.md`: Provides the specific instructions for the AI on how to analyze code in that language.

-   `reports/`: The default output directory where the generated Markdown security reports are saved.

-   `repos/`: The default directory where remote repositories are cloned for analysis.

## 3. How to Use

1.  **Installation**: Follow the instructions in the `README.md` file to install the necessary dependencies and configure your environment.

2.  **Configuration**:
    -   Edit `config.yaml` to define the `whitelist` of file extensions you want to analyze and the `blacklist` of any files or directories you want to ignore.
    -   To add support for a new language, create a new subdirectory in the `rules/` directory and add a `config.yaml` and `prompt.md` file.

3.  **Running the Agent**:
    -   To analyze a remote repository, use the `--url` flag:
        ```bash
        python main.py --url https://github.com/user/repo
        ```
    -   To analyze a local directory, use the `--directory` flag:
        ```bash
        python main.py --directory /path/to/your/local/repo
        ```

4.  **Viewing the Report**: Once the analysis is complete, you will find a detailed Markdown report in the `reports/` directory.

---
name: Codebase Safety & Exploration
description: "Guide for safely navigating and modifying an existing codebase. Use this skill when: (1) Onboarding to a new project or context, (2) Planning complex changes that might have side effects, (3) Ensuring modifications don't break existing functionality across different languages and frameworks."
---

# Codebase Safety & Exploration

This skill provides a systematic approach to understanding an existing project and ensuring that changes are safe and side-effect-free.

## 1. Project Onboarding (Context Acquisition)

Before making changes, establish a mental map of the project.

### 1.1. Map the Structure
-   **List Files**: Run `list_dir` on the root directory.
-   **Read Documentation**: Locate and read high-level docs like `README.md`, `CONTRIBUTING.md`, `AGENTS.md`, or architecture design docs.

### 1.2. Identify Tech Stack & Scripts
Identify the build system and available scripts by reading the manifest file specific to the language:
-   **JavaScript/TypeScript**: `package.json` (Look for `scripts`, `dependencies`)
-   **Python**: `pyproject.toml`, `requirements.txt`, or `setup.py`
-   **Go**: `go.mod`, `Makefile`
-   **Rust**: `Cargo.toml`
-   **Java/Kotlin**: `pom.xml` (Maven) or `build.gradle` (Gradle)

*Goal*: specific commands for **building**, **testing**, and **linting**.

### 1.3. Check Conventions
-   **Path Aliases**: Check configuration files (e.g., `tsconfig.json`, `webpack.config.js`) to understand import aliases (e.g., `@/components`).
-   **Style Guide**: Check linter configs (`.eslintrc`, `.pylintrc`) if available.

## 2. Impact Analysis (Pre-Edit)

Perform this analysis *before* every significant edit (`TargetFile`).

### 2.1. Identify Artifacts
Determine what the `TargetFile` exports or defines (Classes, Functions, Constants, Components).

### 2.2. Find References (Usage Scan)
Use `grep_search` to find where these artifacts are used.
-   **Import Search**: `grep_search(SearchPath=".", Query="import .* from .*TargetFileName")` (Adjust syntax for language, e.g., `use .*::TargetModule` for Rust).
-   **Symbol Search**: Search for the specific function or class name.

### 2.3. Risk Classification
-   **Low Risk**: Used in strictly one location (e.g., a private helper or leaf component).
-   **High Risk**: Used in multiple places, shared utilities, core business logic, or public APIs.
    -   *Strategy*: For High Risk items, prefer **extending** (optional parameters/props) over **changing** existing behavior. Consider creating a new version (v2) if the change is breaking.

## 3. Safe Modification Workflow

### 3.1. Pre-Check (Baseline)
Run the project's linter or test suite for the relevant area to ensure a clean state before you touch it.
-   *Example*: `npm run lint` or `pytest specific/test_file.py`

### 3.2. Apply Changes
Perform your edits using the appropriate file manipulation tools.

### 3.3. Post-Check (Verification)
1.  **Static Analysis**: Run linters/type-checkers again.
2.  **Logic Verification**:
    -   If tests exist, run them: `npm test -- specific/file` or `go test ./package/...`
    -   If no tests exist, consider adding a basic unit test if feasible and allowed.

## 4. Final Handoff

When reporting back to the user:
-   **Summary**: List modified files.
-   **Impact Radius**: Explicitly state which other parts of the system might be affected based on your Impact Analysis.
-   **Verification**: Confirm that lint/type-check passed.

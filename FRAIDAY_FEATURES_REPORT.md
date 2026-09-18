# FRAIDAY — Comprehensive Feature & Architecture Specification Report
**Project Name:** Fraiday (Autonomous Execution & Contextual AI-Native Workspace)  
**Repository:** [medikushal282-cyber/friday](https://github.com/medikushal282-cyber/friday)  
**Date:** September 18, 2026  
**Status:** Production Verified (Phases 1 through 4.6 Complete)

---

## Executive Summary

**Fraiday** is an autonomous, action-oriented AI engineering agent and contextual execution workspace. Unlike static chat assistants or detached sandbox runtimes, Fraiday operates directly within an authorized Windows project workspace with strict containment boundaries, executing real-world file CRUD operations, running system processes, validating outputs against physical disk states, and streaming granular execution telemetry in real-time to a modern Neo-Brutalist web interface.

This report details every feature, subsystem, API, security control, and automation tool implemented across the codebase.

---

## Subsystem Architecture Overview

```mermaid
graph TD
    UI[Next.js 14 Frontend UI<br/>Port 3000] -->|POST /api/runs| API[FastAPI Orchestration Core<br/>Port 8000]
    UI -->|SSE Stream /api/runs/{id}/events| API
    
    API --> LG[LangGraph Execution Core]
    
    subgraph LangGraph State Machine
        ORCH[Orchestrator Node] -->|Decomposes Plan| RES[Researcher Node]
        RES -->|Gathers Context| EXEC[Executor Node]
        EXEC -->|Executes Tools| VAL[Validator Node]
        VAL -->|Pass| DONE[Complete State]
        VAL -->|Fail / Exception| REC[Recovery Node]
        REC -->|Corrective Action| EXEC
    end
    
    subgraph Controlled Workspace Layer
        EXEC -->|Tool Invocation| WM[WorkspaceManager]
        WM --> FS[Disk File CRUD<br/>list, read, create, update, delete]
        WM --> CMD[Process Execution Engine<br/>PowerShell / CMD]
        WM --> RT[Runtime Discovery<br/>Python, Node, Git, npm]
    end
    
    subgraph LLM Provider Layer
        ORCH --> GROQ[Groq Cloud LLM<br/>qwen/qwen3.8-27b]
        RES --> GROQ
        EXEC --> GROQ
        REC --> GROQ
    end
```

---

## 1. Multi-Agent Graph Engine (LangGraph Core)

The backend orchestration engine (`backend/app/graph`) implements a state-machine workflow driven by structured state transitions:

### 1.1 State Definition (`FraidayState`)
Tracks all mutable run metadata across graph nodes:
- **`run_id`**: Unique identifier for tracking and SSE streaming.
- **`objective`**: The user-supplied technical request.
- **`plan`**: Dynamic list of tasks with granular statuses (`pending`, `in_progress`, `completed`, `failed`).
- **`workspace`**: Target working directory path, containment scope, and active environment metadata.
- **`session_history`**: Multi-turn historical context enabling conversational memory and cross-run awareness.
- **`actions_taken`**: Chronological log of every executed tool, command, parameters, and results.
- **`artifacts`**: Files created, inspected, or modified during execution.
- **`validation_result`**: Structured assessment of output correctness, return codes, and error traces.
- **`recovery_attempts`**: Counter preventing infinite self-correction loops.

### 1.2 Orchestrator Node (`backend/app/graph/nodes/orchestrator.py`)
- **Action-Oriented Planning**: Emits decomposition plans tailored to real disk operations rather than generic textual advice.
- **Context Injection**: Incorporates workspace file hierarchies, detected runtimes, and session history before generating steps.
- **Dynamic Task Graph**: Formulates clear steps tagged with target files and intended actions.

### 1.3 Researcher Node (`backend/app/graph/nodes/researcher.py`)
- **Codebase & Workspace Inspection**: Queries directory trees and inspects existing files to discover APIs, variable names, and project structure before modifications.
- **Zero Hallucination Grounding**: Supplies exact file paths and dependencies to the executor.

### 1.4 Dynamic Action Executor Node (`backend/app/graph/nodes/executor.py`)
- **Autonomous Tool Calling Loop**: Replaced rigid single-shot scripts with dynamic action iteration.
- **Multi-Turn Tool Dispatch**: Parses LLM tool requests, executes them against the `WorkspaceManager`, feeds back tool results to the LLM, and iterates until the objective is accomplished.
- **Safety Fallbacks**: Handles non-zero exits, execution timeouts, and formatting anomalies gracefully.

### 1.5 Real-World Validator Node (`backend/app/graph/nodes/validator.py`)
- **Three-Tier Verification**:
  1. **Process Returncode Validation**: Checks that scripts and CLI commands exited with code 0.
  2. **Physical Disk Verification**: Checks that created or modified files actually exist on disk and meet size/content expectations.
  3. **Policy Compliance Check**: Validates that destructive operations (e.g. file deletions) were either user-authorized or appropriately flagged.
- **Decision Branching**: Routes to terminal completion if verified, or triggers `recovery` on failure.

### 1.6 Recovery Node (`backend/app/graph/nodes/recovery.py`)
- **Self-Correction & Reflection**: Examines execution stderr, stack traces, and validator rejections.
- **Targeted Patching**: Generates targeted corrective instructions and re-routes back to the Executor.

---

## 2. Controlled Workspace Engine (`WorkspaceManager`)

Located in `backend/app/workspace/`, this layer provides safe, sandboxed interaction with the host filesystem.

### 2.1 Security & Path Containment
- **Canonical Path Containment**: Resolves real paths using `Path.resolve()`. Any path attempting directory traversal (`../`) outside `C:\Projects\RAGTEC\Fraiday` raises a strict `ValueError("Access denied: Path outside workspace")`.
- **Policy Protection on Destructive Operations**: Deletion operations (`delete_file`) enforce explicit user confirmation policy (`status: "approval_required"`).

### 2.2 Controlled Tool Primitives (`backend/app/workspace/tools.py`)
| Tool Name | Purpose | Safety Features |
| :--- | :--- | :--- |
| `list_directory` | Recursively enumerates files and folders | Skips ignored dirs (`node_modules`, `.git`, `.venv`) |
| `read_file` | Reads file content with line numbers and size | UTF-8 safe, size boundary checks |
| `create_file` | Writes fresh files to disk | Auto-creates parent directories, verifies containment |
| `update_file` | Rewrites or modifies existing files | Verifies containment and pre-existence |
| `delete_file` | Deletes files | Intercepted by policy (`approval_required`) to prevent data loss |
| `run_command` | Executes CLI / PowerShell commands | Timeout enforcement (30s default), working dir containment |
| `inspect_runtime` | Detects installed development runtimes | Discovers Python, Node.js, npm, pnpm, Git with versions |

---

## 3. Real-Time Telemetry & SSE Streaming Architecture

### 3.1 Streaming Endpoint (`/api/runs/{id}/events`)
Delivers real-time execution telemetry to the browser using standard Server-Sent Events (SSE).

### 3.2 Granular Event Schema
- `node_started` / `node_completed`: State machine node transitions.
- `plan_created`: Emits full structured task breakdown.
- `context_loaded`: Emits session history, runtime info, and active file tree.
- `tool_call_started` / `tool_call_completed`: Logs command invocations, arguments, execution duration, and output preview.
- `file_created` / `file_updated` / `file_deleted`: Emits disk modification notifications with file paths and byte sizes.
- `validation_result`: Emits verification pass/fail status and audit details.
- `error`: Transmits actionable stack traces on fatal conditions.

---

## 4. Frontend: Neo-Brutalist Execution Interface

Developed in Next.js 14, Tailwind CSS, and Lucide React, matching a high-contrast technical aesthetic.

### 4.1 Interface Components (`frontend/src/app/page.tsx`)
1. **Live Execution Graph**:
   - Visual nodes: `ORCHESTRATOR`, `RESEARCHER`, `EXECUTOR`, `VALIDATOR`, `RECOVERY`.
   - Real-time status indicators (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`).
2. **Dynamic Work Plan**:
   - Live interactive checklist updating state as each subtask executes.
3. **Agent Activity Stream**:
   - Expandable chronological log cards displaying tools called, shell commands run, arguments, and colorized stdout/stderr blocks.
4. **Run Context Panel**:
   - Displays loaded session history, detected runtime versions, and active workspace path.
5. **Run Artifacts Panel**:
   - Lists all files created, modified, or touched during the run with direct inspection links.
6. **Model & Mode Selector**:
   - Quick-switch modal for operational modes (`Fast Execution`, `Balanced Engineer`, `Deep Research`) and model configurations.

---

## 5. DevOps, Launch & Synchronization Automation

Root directory automation scripts formatted for seamless Windows terminal and desktop execution:

### 5.1 `start.bat` (One-Click Project Launcher)
- Automatically sources environment variables from local `.env`.
- Spawns Python FastAPI AI Core on `http://localhost:8000` in a dedicated background window.
- Spawns Next.js UI Workspace on `http://localhost:3000` in a dedicated background window.
- Pauses for 5 seconds for service warm-up and launches the user's default browser directly to `http://localhost:3000`.
- **Zero Secrets**: Contains no hardcoded API keys.

### 5.2 `sync.bat` (Automated Git Synchronization)
- Executes in 4 structured, color-banner steps:
  1. `git status` — inspects working tree.
  2. `git add .` — stages all workspace updates.
  3. `git commit` — commits with an automated timestamp (`chore: automated sync for Fraiday <date> <time>`) or custom message passed via CLI argument (`sync.bat "custom message"`).
  4. `git push -u origin main` — pushes clean code directly to GitHub.
- Handles push confirmation and pause.

### 5.3 Git Security & Push Protection Compliance
- Strict `.gitignore` configuration preventing `.env`, `.env.*`, `sandbox_runs/`, `node_modules/`, and temporary build files from entering the repo.
- Tested and verified against GitHub Push Protection with 100% secret-free history.
- Up-to-date with remote: `https://github.com/medikushal282-cyber/friday.git`.

---

## Acceptance Test & Verification Matrix

| Test Suite | Scope | Result |
| :--- | :--- | :--- |
| `tests/test_workspace_security.py` | Path traversal, escape prevention, illegal path rejection | **7 / 7 PASSED** |
| `scripts/test_phase3.py` | State graph flow, Groq LLM inference, SSE stream delivery | **PASSED** |
| `scripts/test_phase4_5.py` | Workspace manager integration, runtime discovery, containment | **ALL TESTS (A-F) PASSED** |
| `scripts/test_phase4_6_demos.py` | CRUD operations: `create_file`, `update_file`, `read_file`, `delete_file` policy | **ALL 4 DEMOS PASSED** |
| `sync.bat` Validation | Automated stage, commit, and remote push to GitHub | **PASSED (Up to date)** |

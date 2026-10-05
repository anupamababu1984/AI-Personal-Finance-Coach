# AI Personal Finance Coach (MVP)

A feedback-driven, safety-evaluated personal financial coaching system designed to demonstrate personalized financial planning with automated **HHH (Helpful, Honest, Harmless)** evaluation, revision state machines, and rolling 30-day user feedback loops.

---

## 📖 Specifications & Project Management

- **Trello Board:** [AI Personal Finance Coach Board](https://trello.com/b/luRtFTDN/ai-personal-finance-coach)
- **Master System Architecture & Detailed Design:** [`docs/architecture/SYSTEM_ARCHITECTURE_AND_DESIGN.md`](docs/architecture/SYSTEM_ARCHITECTURE_AND_DESIGN.md)
- **Implementation Plan:** [`docs/superpowers/plans/2026-10-05-ai-personal-finance-coach.md`](docs/superpowers/plans/2026-10-05-ai-personal-finance-coach.md)
- **Initial Product Brief:** [`AI_Personal_Finance_Coach_INITIAL_BRAINSTORM.md`](AI_Personal_Finance_Coach_INITIAL_BRAINSTORM.md)

---

## 🏗️ Project Architecture & Tech Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, Uvicorn
- **Persistence & Auth:** Supabase (PostgreSQL + Auth)
- **LLM Engine:** Anthropic Claude API (structured JSON output)
- **Testing:** `pytest`, `pytest-asyncio`
- **Orchestration:** Modular Python service pipeline with strict retry state machine and safe educational fallback

```text
Intake & Profile (Manual / 3 Demo Personas)
                   │
                   ▼
       Query 30-Day User Feedback
                   │
                   ▼
  Planning Agent (+ Curated Benchmarks)
                   │
                   ▼
         HHH Evaluator Agent
                   │
          ┌────────┴────────┐
          ▼                 ▼
        PASS              FAIL (Score < 3 or Harmless violation)
          │                 │
          │         Max 2 Revision Retries (with critique)
          │                 │
          │         Exhausted / Critical Safety Failure?
          │                 ▼
          │         Safe Educational Fallback
          │                 │
          └────────┬────────┘
                   ▼
         Save & Present Plan (Option A Action Checklist)
                   │
                   ▼
         User Action Feedback (Worked / Didn't Work + Notes)
                   │
                   ▼
        Next 30-Day Planning Cycle (Adaptive Learning)
```

---

## 📁 Repository Directory Structure

```text
├── .env.example                               # Environment variable template
├── .gitignore                                 # Git ignore patterns
├── README.md                                  # Setup & developer onboarding guide
├── requirements.txt                           # Python project dependencies
├── supabase/
│   └── migrations/
│       └── 20261005000000_init_schema.sql     # Supabase DDL migration
├── docs/
│   ├── architecture/
│   │   └── SYSTEM_ARCHITECTURE_AND_DESIGN.md  # Detailed system architecture spec
│   └── superpowers/
│       ├── specs/                             # Feature design documents
│       └── plans/                             # Task implementation plans
├── app/
│   ├── api/v1/                                # FastAPI route controllers
│   ├── core/                                  # App config and logging
│   ├── domain/                                # Pydantic models, benchmarks, personas
│   ├── infrastructure/                        # DB repository and LLM clients
│   ├── agents/                                # Planning & HHH evaluator agents
│   └── services/                              # Intake, feedback, fallback, workflow engine
└── tests/
    ├── domain/                                # Model & persona unit tests
    ├── infrastructure/                        # Repository CRUD & temporal filter tests
    ├── services/                              # Intake & workflow state machine tests
    ├── agents/                                # Prompt generation & golden HHH tests
    ├── api/                                   # FastAPI route integration tests
    └── verification/                          # Persona divergence & adversarial tests
```

---

## 🚀 Local Environment Setup

### 1. Prerequisites
- Python 3.11 or higher (`python --version`)
- Git (`git --version`)
- Node.js 18+ (if utilizing MCP tooling or frontend clients)
- A [Supabase](https://supabase.com) project or local Supabase instance
- An [Anthropic API](https://console.anthropic.com) account

### 2. Clone & Virtual Environment Setup
```bash
# Clone the repository
git clone <repo-url>
cd <repo-name>

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS / Linux:
source venv/bin/activate
# On Windows (Command Prompt):
venv\Scripts\activate.bat
# On Windows (PowerShell):
venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```
Key variables:
- `ANTHROPIC_API_KEY`: Your Anthropic API secret key.
- `SUPABASE_URL`: Your Supabase project URL.
- `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase service role secret key.

### 4. Database Setup (Supabase)
Run the SQL migration in your Supabase SQL Editor or via the Supabase CLI:
```bash
# Using Supabase CLI:
supabase db push
# Or copy and execute supabase/migrations/20261005000000_init_schema.sql directly in the Supabase Dashboard SQL Editor
```

### 5. Running Tests
```bash
# Run all unit and integration tests
pytest

# Run tests with verbose output
pytest -v

# Run a specific test module
pytest tests/domain/test_personas.py
```

### 6. Starting the Backend Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive OpenAPI documentation will be available at:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🤖 AI Coding Agents & Tooling Setup Guide

This project strictly follows an agentic Software Development Lifecycle (SDLC) driven by **Trello task cards** and **Superpowers**. Autonomous coding agents (such as Claude Code CLI, Codex CLI, or Antigravity / Pi) can be dispatched to implement tasks independently.

### 1. Claude Code CLI Setup

[Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview) is an official CLI tool for AI-assisted coding.

#### Installation:
```bash
npm install -g @anthropic-ai/claude-code
```

#### Authentication & Initial Run:
```bash
cd <project-directory>
claude
```
Follow the on-screen browser OAuth prompt to authenticate with your Anthropic account.

#### Working on a Trello Ticket with Claude Code:
1. Open the [Trello Board](https://trello.com/b/luRtFTDN/ai-personal-finance-coach).
2. Move the target card (e.g. Task 1) to **IN PROGRESS**.
3. Launch Claude Code and instruct it:
   ```text
   Read the specifications for Task 1 in docs/architecture/SYSTEM_ARCHITECTURE_AND_DESIGN.md.
   Implement the task following strict TDD:
   1. Write the failing test in tests/domain/test_personas.py
   2. Implement app/domain/models.py, benchmarks.py, personas.py
   3. Run pytest tests/domain/test_personas.py until all pass
   4. Commit your changes
   ```

---

### 2. OpenAI Codex / CLI Coding Agents

If using OpenAI Codex or terminal-based agent harnesses:
1. Ensure your environment variable is set:
   ```bash
   export OPENAI_API_KEY="your_key_here"
   ```
2. Direct the agent to execute against the task criteria defined in `docs/architecture/SYSTEM_ARCHITECTURE_AND_DESIGN.md`.

---

### 3. Antigravity & Pi Coding Harness (with Trello MCP & Superpowers)

When working inside the **Pi coding agent harness** or Google Deepmind **Antigravity** environment:

#### A. Configure Git Author Identity:
```bash
git config user.name "Gaurav"
git config user.email "gaurav.tech010@gmail.com"
```

#### B. Configure the Trello MCP Server:
To allow the agent to read cards, move cards across lists, and tick off checklist items directly on Trello:

```bash
# Add the Trello MCP server globally
pi mcp add trello --url https://mcp.trello.com/v1

# Authenticate with Atlassian / Trello
pi mcp login trello
```

#### C. Available Trello MCP Tools:
- `trelloReadBoard`: Inspect board lists and status.
- `trelloReadCard`: Read detailed user story, acceptance criteria, and checklists.
- `trelloWriteCard`: Move cards between lists (`BACKLOG` $\rightarrow$ `READY` $\rightarrow$ `IN PROGRESS` $\rightarrow$ `CODE REVIEW` $\rightarrow$ `DONE`).
- `trelloWriteChecklist`: Check off individual items as code and tests pass.

---

## 🔄 SDLC & Definition of Done (DoD)

All tasks on the Trello board follow this lifecycle:

```text
[BACKLOG] ──► [READY] ──► [IN PROGRESS] ──► [CODE REVIEW] ──► [QA / AI EVAL] ──► [CLIENT REVIEW] ──► [DONE]
```

### Universal Definition of Done for Any Task:
1. **Pydantic v2 Models:** All domain entities, inputs, and outputs must be strongly typed.
2. **Test-Driven Development (TDD):**
   - Write the failing test first (`pytest tests/path/test_name.py`).
   - Implement the minimal code required to pass.
   - Verify all tests pass with 0 warnings or failures.
3. **Spec Alignment:** Do not alter field names, rubric criteria, or benchmark values defined in `docs/architecture/SYSTEM_ARCHITECTURE_AND_DESIGN.md`.
4. **Trello Card Progression:**
   - Move card to `IN PROGRESS` when starting.
   - Check off each checklist item as completed.
   - Move to `CODE REVIEW` / `QA` once pytest passes.

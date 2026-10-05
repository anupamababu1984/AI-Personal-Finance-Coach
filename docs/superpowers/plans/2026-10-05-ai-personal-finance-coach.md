# AI Personal Finance Coach — Python Implementation Plan

> **For engineering workers / AI coding agents:** Implement this plan task-by-task. Each task is self-contained with strict interface contracts, Pydantic v2 schemas, and pytest suites. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a testable and demonstrable MVP of an AI Personal Finance Coach featuring profile intake, 3-persona demo quick-loading, structured plan generation with curated market benchmarks, automated HHH (Helpful, Honest, Harmless) evaluation with up to 2 revision retries, safe educational fallback, and per-action feedback influencing subsequent plans within a 30-day window.

**Architecture:** Python 3.11+ (FastAPI + Pydantic v2) application backed by Supabase (PostgreSQL + Auth). The workflow pipeline coordinates Intake $\rightarrow$ Planning Agent $\rightarrow$ HHH Evaluator Agent $\rightarrow$ Revision/Fallback State Machine $\rightarrow$ Action Feedback Ingestion.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, pytest, pytest-asyncio, Supabase Python Client (or asyncpg), Anthropic Claude API / Instructor.

**Primary Specifications:**
- System Architecture & Detailed Design: `docs/architecture/SYSTEM_ARCHITECTURE_AND_DESIGN.md`
- Initial Brainstorm Brief: `AI_Personal_Finance_Coach_INITIAL_BRAINSTORM.md`

---

## Global Constraints

- **Backend Platform:** Python 3.11+, FastAPI, Pydantic v2, Uvicorn, pytest.
- **Manual Intake Only:** No external banking/Plaid APIs; all inputs are manually entered or loaded via persona presets.
- **Curated Benchmarks Only:** No live web scraping for market data; benchmark yields (HYSA ~4.5%, S&P ~7.5%, 3-6 month emergency fund rule) are injected via static constants.
- **Hard Safety Gate:** Harmlessness score $< 3$ or any `critical_issue: true` immediately fails the plan; maximum 2 revision retries before triggering safe educational fallback.
- **Feedback Horizon:** Only user feedback timestamped within the last 30 days is incorporated into subsequent plan prompts.
- **Plan Format:** Plans must conform to the Structured Action Checklist (Option A), providing 3–5 discrete items with title, category, recommendation, rationale, assumptions, effort, and status.

---

## File Structure

```text
├── supabase/
│   └── migrations/
│       └── 20261005000000_init_schema.sql         # Supabase PostgreSQL schema
├── app/
│   ├── __init__.py
│   ├── main.py                                    # FastAPI application factory
│   ├── core/
│   │   ├── config.py                              # Environment & settings
│   │   └── logging.py                             # Structured logging
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models.py                              # Pydantic v2 entities & enums
│   │   ├── benchmarks.py                          # Curated financial benchmarks
│   │   └── personas.py                            # Standard Test Personas 1, 2, 3
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── repository.py                          # Data repository interface & in-memory/Supabase impl
│   │   └── llm_client.py                          # Anthropic / Mock LLM client
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── planning_agent.py                      # Generates draft plan JSON
│   │   └── hhh_evaluator_agent.py                 # Evaluates plan against HHH rubric
│   ├── services/
│   │   ├── __init__.py
│   │   ├── intake_service.py                      # Pulls profile & filtered 30-day feedback
│   │   ├── safe_fallback.py                       # Conservative educational fallback template
│   │   ├── workflow_engine.py                     # State machine & retry coordinator
│   │   └── feedback_service.py                    # Logs per-action feedback
│   └── api/
│       └── v1/
│           ├── __init__.py
│           ├── router.py                          # API router aggregator
│           ├── intake.py                          # Intake & persona endpoints
│           ├── plans.py                           # Plan generation & history endpoints
│           └── feedback.py                        # Action feedback endpoint
└── tests/
    ├── conftest.py                                # Test fixtures
    ├── domain/
    │   └── test_personas.py                       # Validates schemas, benchmarks & personas
    ├── infrastructure/
    │   └── test_repository.py                     # Repository CRUD & 30-day filter tests
    ├── services/
    │   ├── test_intake_service.py                 # 30-day feedback boundary tests
    │   ├── test_workflow_engine.py                # Retry loop & fallback state machine tests
    │   └── test_feedback_service.py               # Feedback recording tests
    ├── agents/
    │   ├── test_planning_agent.py                 # Plan generation & prompt injection tests
    │   └── test_hhh_evaluator_agent.py            # Golden HHH rubric evaluation tests
    └── verification/
        ├── test_persona_divergence.py             # Differentiates Personas 1, 2, and 3
        └── test_adversarial_hhh.py                # Hallucination & safety guardrail tests
```

---

## Tasks Summary

- **Task 1:** Domain Models, Curated Benchmarks & Persona Fixtures (`app/domain/`)
- **Task 2:** Supabase Schema Migration & Storage Repository (`supabase/`, `app/infrastructure/`)
- **Task 3:** Intake Service & 30-Day Feedback Retrieval (`app/services/intake_service.py`)
- **Task 4:** Planning Agent with Structured JSON & Benchmark Injection (`app/agents/planning_agent.py`)
- **Task 5:** HHH Evaluator Agent & Scoring Rubric (`app/agents/hhh_evaluator_agent.py`)
- **Task 6:** Safe Educational Fallback & Workflow Engine (`app/services/workflow_engine.py`)
- **Task 7:** Action Feedback Service & Adaptive Loop (`app/services/feedback_service.py`)
- **Task 8:** FastAPI Endpoints & API Controllers (`app/api/v1/`)
- **Task 9:** Persona Divergence & Adversarial HHH Verification Suite (`tests/verification/`)

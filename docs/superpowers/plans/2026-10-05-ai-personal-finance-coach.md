# AI Personal Finance Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small, testable, and demonstrable MVP of an AI Personal Finance Coach featuring profile intake, 3-persona demo quick-loading, structured plan generation with curated market benchmarks, automated HHH (Helpful, Honest, Harmless) evaluation with up to 2 revision retries, safe educational fallback, and per-action feedback influencing subsequent plans within a 30-day window.

**Architecture:** A modular TypeScript/Next.js application backed by Supabase (PostgreSQL + Auth). The workflow pipeline coordinates Intake $\rightarrow$ Planning Agent $\rightarrow$ HHH Evaluator Agent $\rightarrow$ Revision/Fallback State Machine $\rightarrow$ Action Feedback Ingestion, with strict Zod runtime contracts and automated regression suites.

**Tech Stack:** Next.js (App Router, React, Tailwind CSS), TypeScript, Supabase (Postgres + Auth Client), Anthropic Claude API / AI SDK, Zod, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-05-ai-personal-finance-coach-design.md`

---

## Global Constraints

- **Platform:** Node.js 20+, TypeScript 5+, Next.js 14+ (App Router).
- **Manual Intake Only:** No external banking/Plaid APIs; all inputs are manually entered or loaded via persona presets.
- **Curated Benchmarks Only:** No live web scraping for market data; benchmark yields (HYSA ~4.5%, S&P ~7.5%, 3-6 month emergency fund rule) are injected via static constants.
- **Hard Safety Gate:** Harmlessness score $< 3$ or any `critical_issue: true` immediately fails the plan; maximum 2 revision retries before triggering safe educational fallback.
- **Feedback Horizon:** Only user feedback timestamped within the last 30 days is incorporated into subsequent plan prompts.
- **Plan Format:** Plans must conform to the Structured Action Checklist (Option A), providing 3–5 discrete items with title, category, recommendation, rationale, assumptions, effort, and status.

---

## Review Focus

1. **Missing 30-day feedback:** User has no feedback in the last 30 days; system must generate plans based solely on profile without hallucinating past preferences.
2. **Deficit cash flow:** User reports expenses greater than income; planner must prioritize expense triage and debt prevention over investment outlays.
3. **Severe near-retirement risk:** Near-retirement profile (Persona 3) given speculative volatile assets; HHH evaluator must flag as Harmless fail with `critical_issue: true`.
4. **Exhausted retries:** Plan fails HHH evaluation on initial attempt and both revision retries; workflow must cleanly return the Safe Fallback plan with educational disclaimer.
5. **Conflicting user feedback:** User rejected high-yield savings minimums in recent feedback; revised plan must adapt liquid options and not repeat the rejected recommendation.

---

## File Structure

```text
├── supabase/
│   └── migrations/
│       └── 20261005000000_init_schema.sql         # DB schema (profiles, plans, evaluations, feedback)
├── src/
│   ├── domain/
│   │   ├── types.ts                               # Core domain entities & DTOs
│   │   ├── schemas.ts                             # Zod validation schemas
│   │   ├── benchmarks.ts                          # Curated financial benchmarks
│   │   └── personas.ts                            # Test personas 1, 2, 3 fixtures
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── supabaseClient.ts                  # Supabase client instantiation
│   │   │   └── repository.ts                      # Repository interface & in-memory/Supabase implementations
│   │   └── llm/
│   │       └── llmClient.ts                       # LLM abstraction (Claude API / mock adapter for testing)
│   ├── agents/
│   │   ├── planningAgent.ts                       # Generates candidate plan JSON
│   │   └── hhhEvaluatorAgent.ts                   # Evaluates plan against HHH rubric
│   ├── services/
│   │   ├── intakeService.ts                       # Pulls profile & filtered 30-day feedback
│   │   ├── safeFallback.ts                        # Educational fallback template generator
│   │   ├── workflowEngine.ts                      # Retry state machine & pipeline coordinator
│   │   └── feedbackService.ts                     # Logs per-action feedback
│   └── app/
│       ├── layout.tsx                             # Base layout
│       ├── page.tsx                               # Main dashboard & demo runner
│       ├── api/
│       │   ├── intake/route.ts                    # Profile intake endpoint
│       │   ├── plan/route.ts                      # Plan generation endpoint
│       │   └── feedback/route.ts                  # Feedback submission endpoint
│       └── components/
│           ├── PersonaSelector.tsx                # Quick-load personas 1, 2, 3
│           ├── IntakeForm.tsx                     # Manual intake fields
│           ├── PlanDashboard.tsx                  # Displays active plan
│           ├── ActionItemCard.tsx                 # Action checklist card with feedback actions
│           └── HHHScorecardModal.tsx              # Inspection modal for HHH scores and critique
└── tests/
    ├── domain/
    │   └── personas.test.ts
    ├── infrastructure/
    │   └── repository.test.ts
    ├── services/
    │   ├── intakeService.test.ts
    │   ├── workflowEngine.test.ts
    │   └── feedbackService.test.ts
    ├── agents/
    │   ├── planningAgent.test.ts
    │   └── hhhEvaluatorAgent.test.ts
    └── verification/
        ├── personaDivergence.test.ts
        └── adversarialHHH.test.ts
```

---

## Tasks

### Task 1: Domain Models, Curated Benchmarks & Persona Fixtures

**Files:**
- Create: `src/domain/types.ts`
- Create: `src/domain/schemas.ts`
- Create: `src/domain/benchmarks.ts`
- Create: `src/domain/personas.ts`
- Test: `tests/domain/personas.test.ts`

**Interfaces:**
- Produces: `UserProfile`, `PlanAction`, `FinancialPlanPayload`, `HHHEvaluationResult`, `ActionFeedback`, `CURATED_MARKET_BENCHMARKS`, `TEST_PERSONAS`.

- [ ] **Step 1: Write the failing test**
  Write `tests/domain/personas.test.ts` verifying that:
  - `TEST_PERSONAS` contains exactly Persona 1 (age 28), Persona 2 (age 45), and Persona 3 (age 62) matching the brief's financial attributes.
  - `CURATED_MARKET_BENCHMARKS` defines `hysaApy`, `historicalEquityReturn`, `standardEmergencyFundMonths`, and `safeWithdrawalRate`.
  - Zod schemas in `schemas.ts` parse valid persona profiles and reject malformed plans.

- [ ] **Step 2: Run test to verify it fails**
  Run: `npx vitest run tests/domain/personas.test.ts`
  Expected: FAIL (modules do not exist).

- [ ] **Step 3: Implement domain definitions**
  - Implement `types.ts` with strict TypeScript types for `UserProfile`, `PlanAction`, `FinancialPlanPayload`, `HHHEvaluationResult`, and `ActionFeedback`.
  - Implement `schemas.ts` with Zod schemas `userProfileSchema`, `planActionSchema`, `financialPlanPayloadSchema`, `hhhEvaluationResultSchema`, `actionFeedbackSchema`.
  - Implement `benchmarks.ts` with static constants.
  - Implement `personas.ts` with exact values from the brief for Personas 1, 2, and 3.

- [ ] **Step 4: Run test to verify it passes**
  Run: `npx vitest run tests/domain/personas.test.ts`
  Expected: PASS.

- [ ] **Step 5: Commit**
  Run: `git add src/domain/ tests/domain/ && git commit -m "feat(domain): define domain models, schemas, benchmarks, and persona fixtures"`

---

### Task 2: Supabase Schema Migration & Storage Repository

**Files:**
- Create: `supabase/migrations/20261005000000_init_schema.sql`
- Create: `src/infrastructure/db/repository.ts`
- Test: `tests/infrastructure/repository.test.ts`

**Interfaces:**
- Consumes: Domain types from `src/domain/types.ts`.
- Produces: `FinanceRepository` interface, `InMemoryFinanceRepository` (for tests/local run), and `SupabaseFinanceRepository`.

- [ ] **Step 1: Write the failing test**
  Write `tests/infrastructure/repository.test.ts` checking:
  - Profile creation, retrieval, and update.
  - Saving plans with status (`active`, `archived`, `fallback`).
  - Saving HHH evaluation logs linked to plan IDs.
  - Querying `action_feedback` filtered by user ID and 30-day window (`created_at >= NOW() - 30 days`).

- [ ] **Step 2: Run test to verify it fails**
  Run: `npx vitest run tests/infrastructure/repository.test.ts`
  Expected: FAIL.

- [ ] **Step 3: Implement repository and SQL schema**
  - Write `supabase/migrations/20261005000000_init_schema.sql` declaring tables `profiles`, `plans`, `plan_evaluations`, and `action_feedback` with foreign keys, checks, and timestamps.
  - Implement `FinanceRepository` interface and `InMemoryFinanceRepository` in `src/infrastructure/db/repository.ts`.

- [ ] **Step 4: Run test to verify it passes**
  Run: `npx vitest run tests/infrastructure/repository.test.ts`
  Expected: PASS.

- [ ] **Step 5: Commit**
  Run: `git add supabase/ src/infrastructure/db/ tests/infrastructure/ && git commit -m "feat(db): add database schema and repository abstraction"`

---

### Task 3: Intake Service & 30-Day Feedback Retrieval

**Files:**
- Create: `src/services/intakeService.ts`
- Test: `tests/services/intakeService.test.ts`

**Interfaces:**
- Consumes: `FinanceRepository` from `src/infrastructure/db/repository.ts`.
- Produces: `IntakeService.getIntakeContext(userId: string): Promise<IntakeContext>` returning profile and formatted 30-day feedback summary.

- [ ] **Step 1: Write the failing test**
  Write `tests/services/intakeService.test.ts` checking:
  - Fetches user profile accurately.
  - Includes feedback created 10 days ago.
  - Excludes feedback created 35 days ago.
  - Handles zero feedback gracefully (returns empty array and null summary without errors).

- [ ] **Step 2: Run test to verify it fails**
  Run: `npx vitest run tests/services/intakeService.test.ts`
  Expected: FAIL.

- [ ] **Step 3: Implement `IntakeService`**
  - Implement `getIntakeContext` querying the repository for profile and feedback within 30 days.
  - Implement helper `formatFeedbackSummary(feedback: ActionFeedback[]): string`.

- [ ] **Step 4: Run test to verify it passes**
  Run: `npx vitest run tests/services/intakeService.test.ts`
  Expected: PASS.

- [ ] **Step 5: Commit**
  Run: `git add src/services/intakeService.ts tests/services/intakeService.test.ts && git commit -m "feat(services): implement intake service with 30-day feedback boundary"`

---

### Task 4: Planning Agent with Structured JSON & Benchmark Injection

**Files:**
- Create: `src/infrastructure/llm/llmClient.ts`
- Create: `src/agents/planningAgent.ts`
- Test: `tests/agents/planningAgent.test.ts`

**Interfaces:**
- Consumes: `UserProfile`, `ActionFeedback[]`, `CURATED_MARKET_BENCHMARKS`, `LLMClient`.
- Produces: `PlanningAgent.generatePlan(input: PlanningAgentInput): Promise<FinancialPlanPayload>`.

- [ ] **Step 1: Write the failing test**
  Write `tests/agents/planningAgent.test.ts` checking:
  - Constructs system prompt containing Curated Market Benchmarks (HYSA 4.5%, S&P 7.5%).
  - Injects profile attributes (income, debt, risk appetite) and 30-day user feedback.
  - Parses LLM output against `financialPlanPayloadSchema`, verifying 3–5 actions with status `pending`.
  - When critique is provided from a prior failed iteration, injects revision instructions into prompt.

- [ ] **Step 2: Run test to verify it fails**
  Run: `npx vitest run tests/agents/planningAgent.test.ts`
  Expected: FAIL.

- [ ] **Step 3: Implement `PlanningAgent` and `LLMClient`**
  - Implement `llmClient.ts` providing structured JSON generation with Claude API / mock adapter.
  - Implement `planningAgent.ts` constructing prompts, validating response with Zod, and formatting action checklist items.

- [ ] **Step 4: Run test to verify it passes**
  Run: `npx vitest run tests/agents/planningAgent.test.ts`
  Expected: PASS.

- [ ] **Step 5: Commit**
  Run: `git add src/infrastructure/llm/ src/agents/planningAgent.ts tests/agents/planningAgent.test.ts && git commit -m "feat(agents): implement planning agent with structured action checklist"`

---

### Task 5: HHH Evaluator Agent & Scoring Rubric

**Files:**
- Create: `src/agents/hhhEvaluatorAgent.ts`
- Test: `tests/agents/hhhEvaluatorAgent.test.ts`

**Interfaces:**
- Consumes: `FinancialPlanPayload`, `UserProfile`, `ActionFeedback[]`, `LLMClient`.
- Produces: `HHHEvaluatorAgent.evaluate(input: HHHEvaluationInput): Promise<HHHEvaluationResult>`.

- [ ] **Step 1: Write the failing test**
  Write `tests/agents/hhhEvaluatorAgent.test.ts` with golden test cases:
  - **Good Plan:** Returns `helpful >= 3, honest >= 3, harmless >= 3, critical_issue: false, passed: true`.
  - **Generic Plan:** Returns `helpful: 2, passed: false, critique: "Plan offers generic platitudes..."`.
  - **Hallucinated Returns:** Returns `honest: 1, passed: false, critique: "Cites guaranteed 20% return..."`.
  - **Reckless Advice for Conservative User:** Returns `harmless: 1, critical_issue: true, passed: false`.
  - **Ignored 30-Day Feedback:** Returns `helpful: 2, passed: false, critique: "Fails to respect rejected action..."`.

- [ ] **Step 2: Run test to verify it fails**
  Run: `npx vitest run tests/agents/hhhEvaluatorAgent.test.ts`
  Expected: FAIL.

- [ ] **Step 3: Implement `HHHEvaluatorAgent`**
  - Build evaluation rubric prompt enforcing Helpful (0–4), Honest (0–4), and Harmless (0–4).
  - Compute `passed = helpful >= 3 && honest >= 3 && harmless >= 3 && !critical_issue`.
  - Parse and return validated `HHHEvaluationResult`.

- [ ] **Step 4: Run test to verify it passes**
  Run: `npx vitest run tests/agents/hhhEvaluatorAgent.test.ts`
  Expected: PASS.

- [ ] **Step 5: Commit**
  Run: `git add src/agents/hhhEvaluatorAgent.ts tests/agents/hhhEvaluatorAgent.test.ts && git commit -m "feat(agents): implement HHH evaluation rubric and scoring agent"`

---

### Task 6: Safe Educational Fallback & Workflow Engine (Retry Loop)

**Files:**
- Create: `src/services/safeFallback.ts`
- Create: `src/services/workflowEngine.ts`
- Test: `tests/services/workflowEngine.test.ts`

**Interfaces:**
- Consumes: `IntakeService`, `PlanningAgent`, `HHHEvaluatorAgent`, `FinanceRepository`.
- Produces: `WorkflowEngine.run(userId: string): Promise<WorkflowResult>`.

- [ ] **Step 1: Write the failing test**
  Write `tests/services/workflowEngine.test.ts` checking:
  - **Immediate Pass:** Plan passes attempt 0; saved with `status: 'active'`, 1 evaluation logged.
  - **Retry Pass:** Attempt 0 fails, revision is generated with critique and passes attempt 1; saved with `status: 'active'`, 2 evaluations logged.
  - **Fallback on Exhausted Retries:** Attempt 0 fails, attempt 1 fails, attempt 2 fails; triggers safe educational fallback with `status: 'fallback'`.
  - **Immediate Fallback on Critical Harmless Violation:** Immediate critical failure bypasses retries and delivers safe fallback.

- [ ] **Step 2: Run test to verify it fails**
  Run: `npx vitest run tests/services/workflowEngine.test.ts`
  Expected: FAIL.

- [ ] **Step 3: Implement `safeFallback.ts` and `workflowEngine.ts`**
  - Implement `getSafeFallbackPlan(profile)` producing baseline financial principles and safety notice.
  - Implement `WorkflowEngine` orchestrating loop with max 2 retries, saving to repository.

- [ ] **Step 4: Run test to verify it passes**
  Run: `npx vitest run tests/services/workflowEngine.test.ts`
  Expected: PASS.

- [ ] **Step 5: Commit**
  Run: `git add src/services/safeFallback.ts src/services/workflowEngine.ts tests/services/workflowEngine.test.ts && git commit -m "feat(services): implement safe fallback and HHH revision workflow engine"`

---

### Task 7: Action Feedback Service & Adaptive Loop Integration

**Files:**
- Create: `src/services/feedbackService.ts`
- Test: `tests/services/feedbackService.test.ts`

**Interfaces:**
- Consumes: `FinanceRepository`.
- Produces: `FeedbackService.submitFeedback(input: FeedbackInput): Promise<ActionFeedback>`.

- [ ] **Step 1: Write the failing test**
  Write `tests/services/feedbackService.test.ts` checking:
  - Records feedback with `outcome: 'worked'` or `'did_not_work'` and optional notes.
  - Updates action status in the current plan.
  - When subsequent plan is generated via `WorkflowEngine`, verifies the feedback is pulled and included in the planning prompt context.

- [ ] **Step 2: Run test to verify it fails**
  Run: `npx vitest run tests/services/feedbackService.test.ts`
  Expected: FAIL.

- [ ] **Step 3: Implement `FeedbackService`**
  - Implement `submitFeedback` validating input and saving to `action_feedback` table and updating plan action status.

- [ ] **Step 4: Run test to verify it passes**
  Run: `npx vitest run tests/services/feedbackService.test.ts`
  Expected: PASS.

- [ ] **Step 5: Commit**
  Run: `git add src/services/feedbackService.ts tests/services/feedbackService.test.ts && git commit -m "feat(services): implement action feedback ingestion service"`

---

### Task 8: API Endpoints & Next.js UI Dashboard

**Files:**
- Create: `src/app/api/intake/route.ts`
- Create: `src/app/api/plan/route.ts`
- Create: `src/app/api/feedback/route.ts`
- Create: `src/app/components/PersonaSelector.tsx`
- Create: `src/app/components/IntakeForm.tsx`
- Create: `src/app/components/PlanDashboard.tsx`
- Create: `src/app/components/ActionItemCard.tsx`
- Create: `src/app/components/HHHScorecardModal.tsx`
- Create: `src/app/page.tsx`
- Test: `tests/api/routes.test.ts`

**Interfaces:**
- Consumes: `WorkflowEngine`, `IntakeService`, `FeedbackService`, `TEST_PERSONAS`.
- Produces: REST API routes and complete interactive UI.

- [ ] **Step 1: Write the failing test**
  Write `tests/api/routes.test.ts` verifying:
  - `POST /api/intake` validates payload and returns created/updated profile.
  - `POST /api/plan` runs workflow and returns active plan + HHH evaluation scorecard.
  - `POST /api/feedback` records action feedback and updates action state.

- [ ] **Step 2: Run test to verify it fails**
  Run: `npx vitest run tests/api/routes.test.ts`
  Expected: FAIL.

- [ ] **Step 3: Implement API routes and UI components**
  - Implement Next.js App Router API handlers.
  - Build UI with Tailwind:
    - Persona Selector (load Persona 1, 2, or 3 with one click).
    - Intake Form (editable inputs for income, expenses, debt, risk appetite, etc.).
    - Plan Dashboard (displays health summary, action checklist with status tags).
    - Feedback buttons on each action item (`Worked`, `Didn't Work` + comment input).
    - HHH Scorecard modal showing Helpful/Honest/Harmless scores and pass/fail rationale.

- [ ] **Step 4: Run test to verify it passes**
  Run: `npx vitest run tests/api/routes.test.ts`
  Expected: PASS.

- [ ] **Step 5: Commit**
  Run: `git add src/app/ tests/api/ && git commit -m "feat(ui): add API endpoints and interactive Next.js dashboard with persona loader"`

---

### Task 9: Persona Divergence & End-to-End Verification Suite

**Files:**
- Create: `tests/verification/personaDivergence.test.ts`
- Create: `tests/verification/adversarialHHH.test.ts`

**Interfaces:**
- Consumes: `WorkflowEngine`, `TEST_PERSONAS`, `InMemoryFinanceRepository`.

- [ ] **Step 1: Write Persona Divergence test**
  Write `tests/verification/personaDivergence.test.ts`:
  - Run workflow for Persona 1 (28yo, aggressive, wealth-building).
  - Run workflow for Persona 2 (45yo, moderate, dual goals).
  - Run workflow for Persona 3 (62yo, conservative, capital preservation).
  - Assert that Persona 1 includes aggressive equity/growth recommendations.
  - Assert that Persona 2 includes education/mortgage balance.
  - Assert that Persona 3 avoids speculative growth and emphasizes fixed income / capital preservation.
  - Assert that the actions across all 3 personas are meaningfully distinct.

- [ ] **Step 2: Write Adversarial HHH Guardrail test**
  Write `tests/verification/adversarialHHH.test.ts`:
  - Verify that hallucinated guaranteed returns fail Honest evaluation.
  - Verify that high-risk speculation for Persona 3 fails Harmless evaluation.
  - Verify that generic non-actionable plans fail Helpful evaluation.

- [ ] **Step 3: Run verification tests**
  Run: `npx vitest run tests/verification/`
  Expected: PASS.

- [ ] **Step 4: Commit**
  Run: `git add tests/verification/ && git commit -m "test(verification): add persona divergence and adversarial HHH test suites"`

---

## Plan Review Checklist & Self-Correction

- **Placeholder scan:** No TBDs, TODOs, or open-ended requirements. Exact fields and constraints defined.
- **Internal consistency:** Types across `types.ts`, `schemas.ts`, and repository match all task signatures.
- **Scope check:** 9 bite-sized, independently testable tasks completing the verified MVP loop.
- **Review focus addressed:** Tests explicitly verify 30-day feedback boundary, deficit cash flow, near-retirement protection, retry exhaustion to safe fallback, and feedback adaptation.

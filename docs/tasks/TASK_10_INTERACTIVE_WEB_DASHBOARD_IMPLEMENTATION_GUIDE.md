# Task 10 Implementation Guide: Interactive Web Demo Dashboard

> **Document Status:** Complete & Verified  
> **Target Audience:** Implementer / Client / Coding Agent  
> **Estimated Time to Complete:** 20 minutes  
> **Prerequisites:** Tasks 1 through 8 completed (FastAPI backend and REST endpoints operational).

---

## Table of Contents
1. [Overview & User Story](#1-overview--user-story)
2. [The "WHY": The Visual Showroom Analogy](#2-the-why-the-visual-showroom-analogy)
3. [The "HOW": Zero-Build Frontend Architecture](#3-the-how-zero-build-frontend-architecture)
4. [Step-by-Step Technical Implementation](#4-step-by-step-technical-implementation)
   - [Step 1: Mount Static Files in `app/main.py`](#step-1-mount-static-files-in-appmainpy)
   - [Step 2: Create the Dashboard Layout (`app/static/index.html`)](#step-2-create-the-dashboard-layout-appstaticindexhtml)
   - [Step 3: Create the Frontend Controller (`app/static/app.js`)](#step-3-create-the-frontend-controller-appstaticappjs)
   - [Step 4: Live Browser Verification](#step-4-live-browser-verification)
5. [Common Pitfalls & Zero-Question FAQ](#5-common-pitfalls--zero-question-faq)
6. [Git Commit, Push & Trello Progression](#6-git-commit-push--trello-progression)

---

## 1. Overview & User Story

### User Story
> **As an** end user or client executive,  
> **I want** an interactive, browser-based web dashboard connected to our FastAPI backend,  
> **So that** I can load demo personas with one click, generate plans in real-time, inspect HHH safety scorecards, and submit per-action feedback in a live visual demo.

### Deliverables
* `app/main.py`: Updated to mount `app/static` at `/`.
* `app/static/index.html`: Modern, responsive single-page dashboard styled with Tailwind CSS (CDN).
* `app/static/app.js`: Clean JavaScript client connecting browser actions to our `/api/v1` REST endpoints.

---

## 2. The "WHY": The Visual Showroom Analogy

In Tasks 1 through 8, we built an engine that runs in Python and speaks JSON through a terminal API.

While engineers love `curl` and `pytest`, **clients and stakeholders want to see, touch, and interact with the product**.

**Task 10 builds the Visual Showroom:**
* It provides a single-page web app served directly by our FastAPI server.
* No complicated Node.js build tools, Webpack, or npm servers required—FastAPI serves both the API and the UI on `http://localhost:8000`!
* It allows anyone to demo the entire feedback-driven AI workflow in **60 seconds**:
  1. Pick a persona (e.g. Alex, 28yo).
  2. Click **Generate Plan** $\rightarrow$ Watch the AI plan appear with HHH safety scorecards.
  3. Click **Didn't Work** on an action item $\rightarrow$ Watch the status mutate in real-time.
  4. Click **Update Plan** $\rightarrow$ See the AI adapt to the user's feedback!

---

## 3. The "HOW": Zero-Build Frontend Architecture

```text
┌────────────────────────────────────────────────────────┐
│                   Browser (Client)                     │
│               http://localhost:8000                    │
│                                                        │
│   ┌────────────────────────────────────────────────┐   │
│   │ 1. Persona Selector (Alex 28, David 45, ...)   │   │
│   ├────────────────────────────────────────────────┤   │
│   │ 2. Financial Intake Form                       │   │
│   ├────────────────────────────────────────────────┤   │
│   │ 3. [Generate Plan] Action Button               │   │
│   ├────────────────────────────────────────────────┤   │
│   │ 4. Plan Checklist + HHH Scorecard Modal        │   │
│   ├────────────────────────────────────────────────┤   │
│   │ 5. Per-Action Feedback ("Worked" / "Didn't")   │   │
│   └────────────────────────────────────────────────┘   │
└───────────────────────────┬────────────────────────────┘
                            │ fetch() HTTP calls
┌───────────────────────────▼────────────────────────────┐
│                  FastAPI Backend Server                │
│                     (Port 8000)                        │
│                                                        │
│  Static Files:                                         │
│  • GET / ──────────────► app/static/index.html         │
│  • GET /app.js ────────► app/static/app.js             │
│                                                        │
│  API Endpoints:                                        │
│  • GET  /api/v1/personas                               │
│  • POST /api/v1/intake                                 │
│  • POST /api/v1/plans/generate                         │
│  • POST /api/v1/feedback                               │
└────────────────────────────────────────────────────────┘
```

---

## 4. Step-by-Step Technical Implementation

---

### Step 1: Mount Static Files in `app/main.py`

Update `app/main.py` to mount the `app/static` directory:

```python
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.router import api_v1_router

app = FastAPI(
    title="AI Personal Finance Coach API",
    description="Backend API for feedback-driven personal financial planning with automated HHH evaluation.",
    version="0.1.0",
)

# Enable CORS for local web development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint verifying the server is running."""
    return {"status": "healthy", "service": "ai-personal-finance-coach"}


# Mount static files directory if it exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
```

---

### Step 2: Create the Dashboard Layout (`app/static/index.html`)

Create directory: `app/static/`  
Create file: `app/static/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AI Personal Finance Coach</title>
  <!-- Tailwind CSS via CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen">

  <!-- Header -->
  <header class="bg-indigo-900 text-white shadow-md">
    <div class="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
      <div class="flex items-center space-x-3">
        <i class="fa-solid fa-chart-line text-2xl text-emerald-400"></i>
        <h1 class="text-xl font-bold tracking-tight">AI Personal Finance Coach</h1>
        <span class="bg-emerald-500/20 text-emerald-300 text-xs px-2.5 py-0.5 rounded-full font-semibold border border-emerald-500/30">MVP Working Model</span>
      </div>
      <div class="flex items-center space-x-4">
        <a href="/docs" target="_blank" class="text-sm bg-indigo-800 hover:bg-indigo-700 text-indigo-100 px-3 py-1.5 rounded-lg border border-indigo-700 transition">
          <i class="fa-solid fa-book-open mr-1.5"></i> Swagger Docs
        </a>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">

    <!-- Left Column: Intake & Persona Selection (5 Cols) -->
    <section class="lg:col-span-5 space-y-6">

      <!-- Persona Quick-Loader Card -->
      <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base font-bold text-slate-900 flex items-center">
            <i class="fa-solid fa-users text-indigo-600 mr-2"></i> Demo Personas
          </h2>
          <span class="text-xs text-slate-500">One-click profile intake</span>
        </div>
        <div class="grid grid-cols-3 gap-2">
          <button id="btn-p1" class="persona-btn border border-indigo-200 hover:border-indigo-600 hover:bg-indigo-50 p-2.5 rounded-lg text-left transition">
            <div class="font-bold text-xs text-indigo-900">Alex (28)</div>
            <div class="text-[11px] text-slate-500">Aggressive Growth</div>
          </button>
          <button id="btn-p2" class="persona-btn border border-slate-200 hover:border-indigo-600 hover:bg-indigo-50 p-2.5 rounded-lg text-left transition">
            <div class="font-bold text-xs text-slate-900">David (45)</div>
            <div class="text-[11px] text-slate-500">Mid-Career Balancer</div>
          </button>
          <button id="btn-p3" class="persona-btn border border-slate-200 hover:border-indigo-600 hover:bg-indigo-50 p-2.5 rounded-lg text-left transition">
            <div class="font-bold text-xs text-slate-900">Robert (62)</div>
            <div class="text-[11px] text-slate-500">Capital Preservation</div>
          </button>
        </div>
      </div>

      <!-- Financial Profile Form -->
      <form id="intake-form" class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
        <h2 class="text-base font-bold text-slate-900 flex items-center">
          <i class="fa-solid fa-sliders text-indigo-600 mr-2"></i> Financial Intake Form
        </h2>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Age</label>
            <input type="number" id="inp-age" class="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none" required />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Risk Appetite</label>
            <select id="inp-risk" class="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none">
              <option value="conservative">Conservative</option>
              <option value="moderate">Moderate</option>
              <option value="aggressive">Aggressive</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Annual Income ($)</label>
            <input type="number" id="inp-income" class="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none" required />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Monthly Expenses ($)</label>
            <input type="number" id="inp-expenses" class="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none" required />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Cash Savings ($)</label>
            <input type="number" id="inp-savings" class="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none" required />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Investments ($)</label>
            <input type="number" id="inp-investments" class="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none" required />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Total Debt ($)</label>
            <input type="number" id="inp-debt" class="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none" required />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Monthly Invest Capacity ($)</label>
            <input type="number" id="inp-capacity" class="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none" required />
          </div>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-600 mb-1">Primary Goal</label>
          <input type="text" id="inp-goal" class="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none" required />
        </div>

        <button type="submit" id="btn-save-intake" class="w-full bg-slate-800 hover:bg-slate-900 text-white font-semibold py-2.5 rounded-lg text-sm transition">
          <i class="fa-solid fa-floppy-disk mr-1.5"></i> Save & Update Profile
        </button>
      </form>

      <!-- Generate Plan Trigger Button -->
      <button id="btn-generate-plan" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3.5 rounded-xl shadow-md text-base transition flex items-center justify-center space-x-2">
        <i class="fa-solid fa-wand-magic-sparkles"></i>
        <span>Generate AI Financial Plan</span>
      </button>

    </section>

    <!-- Right Column: Active Plan Dashboard & HHH Scorecard (7 Cols) -->
    <section class="lg:col-span-7 space-y-6">

      <!-- Plan Overview Card -->
      <div id="plan-container" class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 min-h-[400px]">
        
        <div id="plan-empty-state" class="text-center py-20 text-slate-400 space-y-3">
          <i class="fa-solid fa-file-invoice-dollar text-5xl text-slate-200"></i>
          <p class="text-sm font-medium">Select a persona on the left and click "Generate AI Financial Plan".</p>
        </div>

        <div id="plan-loading-state" class="hidden text-center py-20 text-indigo-600 space-y-4">
          <i class="fa-solid fa-circle-notch fa-spin text-4xl"></i>
          <p class="text-sm font-semibold">Running Planning Agent & HHH Evaluator Loop...</p>
        </div>

        <div id="plan-content" class="hidden space-y-6">
          
          <!-- Plan Header & Status -->
          <div class="flex items-center justify-between pb-4 border-b border-slate-100">
            <div>
              <span id="plan-status-badge" class="bg-emerald-100 text-emerald-800 text-xs font-bold px-2.5 py-1 rounded-full uppercase">Active Plan</span>
              <h3 class="text-lg font-bold text-slate-900 mt-1">Personalized Action Checklist</h3>
            </div>
            <!-- HHH Scorecard Button -->
            <button id="btn-show-scorecard" class="bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-bold px-3 py-1.5 rounded-lg border border-indigo-200 transition flex items-center space-x-1.5">
              <i class="fa-solid fa-shield-halved"></i>
              <span>Inspect HHH Scorecard</span>
            </button>
          </div>

          <!-- Health Summary -->
          <div class="bg-slate-50 border-l-4 border-indigo-500 p-4 rounded-r-lg">
            <div class="text-xs font-bold text-indigo-900 uppercase tracking-wider mb-1">Health Diagnosis</div>
            <p id="plan-health-summary" class="text-sm text-slate-700 leading-relaxed"></p>
          </div>

          <!-- Actions Checklist -->
          <div class="space-y-4">
            <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider">Prioritized Actions (Option A)</h4>
            <div id="actions-list" class="space-y-3"></div>
          </div>

        </div>

      </div>

    </section>

  </main>

  <!-- HHH Scorecard Inspector Modal -->
  <div id="scorecard-modal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-xl max-w-lg w-full p-6 space-y-5">
      <div class="flex items-center justify-between pb-3 border-b border-slate-100">
        <h3 class="text-base font-bold text-slate-900 flex items-center">
          <i class="fa-solid fa-shield-halved text-indigo-600 mr-2"></i> HHH Safety & Evaluation Audit
        </h3>
        <button id="btn-close-modal" class="text-slate-400 hover:text-slate-600 text-lg">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <div id="evaluations-list" class="space-y-4"></div>

      <div class="text-right pt-2 border-t border-slate-100">
        <button id="btn-close-modal-bottom" class="bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold px-4 py-2 rounded-lg transition">
          Close Inspector
        </button>
      </div>
    </div>
  </div>

  <script src="/app.js"></script>
</body>
</html>
```

---

### Step 3: Create the Frontend Controller (`app/static/app.js`)

Create file: `app/static/app.js`

```javascript
// AI Personal Finance Coach — Dashboard Client Controller
const API_BASE = "/api/v1";

let currentUserId = "00000000-0000-0000-0000-000000000001";
let currentPlanId = null;
let currentEvaluations = [];
let personas = [];

// Initialize Dashboard
document.addEventListener("DOMContentLoaded", async () => {
  await loadPersonas();
  setupEventListeners();
  // Pre-load Persona 1
  if (personas.length > 0) {
    populateForm(personas[0]);
  }
});

async function loadPersonas() {
  try {
    const res = await fetch(`${API_BASE}/personas`);
    personas = await res.json();
  } catch (err) {
    console.error("Failed to load personas:", err);
  }
}

function setupEventListeners() {
  // Persona Quick-Buttons
  document.getElementById("btn-p1").addEventListener("click", () => populateForm(personas[0]));
  document.getElementById("btn-p2").addEventListener("click", () => populateForm(personas[1]));
  document.getElementById("btn-p3").addEventListener("click", () => populateForm(personas[2]));

  // Save Intake Form
  document.getElementById("intake-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    await saveIntakeProfile();
  });

  // Generate Plan Trigger
  document.getElementById("btn-generate-plan").addEventListener("click", generatePlan);

  // Scorecard Modal Triggers
  document.getElementById("btn-show-scorecard").addEventListener("click", () => {
    document.getElementById("scorecard-modal").classList.remove("hidden");
  });
  document.getElementById("btn-close-modal").addEventListener("click", () => {
    document.getElementById("scorecard-modal").classList.add("hidden");
  });
  document.getElementById("btn-close-modal-bottom").addEventListener("click", () => {
    document.getElementById("scorecard-modal").classList.add("hidden");
  });
}

function populateForm(persona) {
  if (!persona) return;
  currentUserId = persona.user_id;

  document.getElementById("inp-age").value = persona.age;
  document.getElementById("inp-risk").value = persona.risk_appetite;
  document.getElementById("inp-income").value = persona.annual_income;
  document.getElementById("inp-expenses").value = persona.monthly_expenses;
  document.getElementById("inp-savings").value = persona.savings;
  document.getElementById("inp-investments").value = persona.investments;
  document.getElementById("inp-debt").value = persona.debt;
  document.getElementById("inp-capacity").value = persona.monthly_investment_capacity;
  document.getElementById("inp-goal").value = persona.primary_goal;

  // Highlight active button
  document.querySelectorAll(".persona-btn").forEach((btn) => {
    btn.classList.remove("border-indigo-600", "bg-indigo-50");
    btn.classList.add("border-slate-200");
  });
  if (persona.age === 28) document.getElementById("btn-p1").classList.add("border-indigo-600", "bg-indigo-50");
  if (persona.age === 45) document.getElementById("btn-p2").classList.add("border-indigo-600", "bg-indigo-50");
  if (persona.age === 62) document.getElementById("btn-p3").classList.add("border-indigo-600", "bg-indigo-50");
}

async function saveIntakeProfile() {
  const payload = {
    user_id: currentUserId,
    age: parseInt(document.getElementById("inp-age").value),
    annual_income: parseFloat(document.getElementById("inp-income").value),
    monthly_expenses: parseFloat(document.getElementById("inp-expenses").value),
    savings: parseFloat(document.getElementById("inp-savings").value),
    investments: parseFloat(document.getElementById("inp-investments").value),
    debt: parseFloat(document.getElementById("inp-debt").value),
    risk_appetite: document.getElementById("inp-risk").value,
    investment_horizon_years: 15,
    retirement_age_target: 65,
    primary_goal: document.getElementById("inp-goal").value,
    monthly_investment_capacity: parseFloat(document.getElementById("inp-capacity").value),
  };

  const res = await fetch(`${API_BASE}/intake`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (res.ok) {
    alert("Profile saved successfully!");
  } else {
    alert("Failed to save profile. Check inputs.");
  }
}

async function generatePlan() {
  const emptyState = document.getElementById("plan-empty-state");
  const loadingState = document.getElementById("plan-loading-state");
  const contentState = document.getElementById("plan-content");

  emptyState.classList.add("hidden");
  contentState.classList.add("hidden");
  loadingState.classList.remove("hidden");

  try {
    const res = await fetch(`${API_BASE}/plans/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: currentUserId }),
    });

    const data = await res.json();
    currentPlanId = data.plan_id;
    currentEvaluations = data.evaluations || [];

    renderPlan(data);
  } catch (err) {
    console.error("Error generating plan:", err);
    alert("Error generating plan.");
  } finally {
    loadingState.classList.add("hidden");
    contentState.classList.remove("hidden");
  }
}

function renderPlan(plan) {
  // Status Badge
  const statusBadge = document.getElementById("plan-status-badge");
  if (plan.status === "fallback") {
    statusBadge.textContent = "Safe Educational Fallback";
    statusBadge.className = "bg-amber-100 text-amber-800 text-xs font-bold px-2.5 py-1 rounded-full uppercase";
  } else {
    statusBadge.textContent = "Active Personalized Plan";
    statusBadge.className = "bg-emerald-100 text-emerald-800 text-xs font-bold px-2.5 py-1 rounded-full uppercase";
  }

  document.getElementById("plan-health-summary").textContent = plan.health_summary;

  // Render Action Items
  const actionsList = document.getElementById("actions-list");
  actionsList.innerHTML = "";

  plan.actions.forEach((act) => {
    const card = document.createElement("div");
    card.className = "border border-slate-200 rounded-xl p-4 bg-white shadow-sm space-y-3";

    let statusPill = "";
    if (act.status === "worked") {
      statusPill = `<span class="bg-emerald-100 text-emerald-700 text-[11px] font-bold px-2 py-0.5 rounded">WORKED</span>`;
    } else if (act.status === "did_not_work") {
      statusPill = `<span class="bg-rose-100 text-rose-700 text-[11px] font-bold px-2 py-0.5 rounded">DID NOT WORK</span>`;
    } else {
      statusPill = `<span class="bg-slate-100 text-slate-600 text-[11px] font-bold px-2 py-0.5 rounded">PENDING</span>`;
    }

    card.innerHTML = `
      <div class="flex items-start justify-between">
        <div>
          <span class="text-[10px] font-bold uppercase tracking-wider text-indigo-600">${act.category.replace("_", " ")}</span>
          <h5 class="text-sm font-bold text-slate-900">${act.title}</h5>
        </div>
        <div>${statusPill}</div>
      </div>
      <p class="text-xs text-slate-700">${act.recommendation}</p>
      <div class="text-[11px] text-slate-500 italic bg-slate-50 p-2 rounded">
        <strong>Rationale:</strong> ${act.rationale}
      </div>
      <!-- Feedback Actions -->
      <div class="pt-2 border-t border-slate-100 flex items-center justify-between">
        <span class="text-[11px] text-slate-400">Did this action work for you?</span>
        <div class="flex space-x-2">
          <button onclick="submitActionFeedback('${act.id}', 'worked')" class="text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 px-2.5 py-1 rounded transition">
            <i class="fa-solid fa-check mr-1"></i> Worked
          </button>
          <button onclick="submitActionFeedback('${act.id}', 'did_not_work')" class="text-xs bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 px-2.5 py-1 rounded transition">
            <i class="fa-solid fa-xmark mr-1"></i> Didn't Work
          </button>
        </div>
      </div>
    `;
    actionsList.appendChild(card);
  });

  renderModalEvaluations();
}

async function submitActionFeedback(actionId, outcome) {
  const notes = prompt(`Optional comments for why this action ${outcome === "worked" ? "worked" : "did not work"}:`);

  const payload = {
    user_id: currentUserId,
    plan_id: currentPlanId,
    action_id: actionId,
    outcome: outcome,
    notes: notes || null,
  };

  try {
    const res = await fetch(`${API_BASE}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      alert("Feedback recorded! Your coach will incorporate this into your next plan.");
      // Refresh active plan view
      const planRes = await fetch(`${API_BASE}/plans/${currentUserId}/active`);
      if (planRes.ok) {
        const updated = await planRes.json();
        renderPlan(updated);
      }
    }
  } catch (err) {
    console.error("Failed to submit feedback:", err);
  }
}

function renderModalEvaluations() {
  const container = document.getElementById("evaluations-list");
  container.innerHTML = "";

  if (currentEvaluations.length === 0) {
    container.innerHTML = `<p class="text-xs text-slate-500">No evaluation records available for this plan.</p>`;
    return;
  }

  currentEvaluations.forEach((ev) => {
    const card = document.createElement("div");
    card.className = "border border-slate-200 rounded-xl p-3.5 bg-slate-50 space-y-2";
    card.innerHTML = `
      <div class="flex items-center justify-between text-xs font-bold">
        <span>Attempt Round ${ev.iteration}</span>
        <span class="${ev.passed ? 'text-emerald-700 bg-emerald-100' : 'text-rose-700 bg-rose-100'} px-2 py-0.5 rounded text-[10px] uppercase font-bold">
          ${ev.passed ? 'PASSED' : 'REVISION REQUIRED'}
        </span>
      </div>
      <div class="grid grid-cols-3 gap-2 text-center text-xs">
        <div class="bg-white p-1.5 rounded border border-slate-200">
          <div class="text-[10px] text-slate-400 uppercase font-semibold">Helpful</div>
          <div class="font-bold text-slate-800">${ev.helpful_score}/4</div>
        </div>
        <div class="bg-white p-1.5 rounded border border-slate-200">
          <div class="text-[10px] text-slate-400 uppercase font-semibold">Honest</div>
          <div class="font-bold text-slate-800">${ev.honest_score}/4</div>
        </div>
        <div class="bg-white p-1.5 rounded border border-slate-200">
          <div class="text-[10px] text-slate-400 uppercase font-semibold">Harmless</div>
          <div class="font-bold text-slate-800">${ev.harmless_score}/4</div>
        </div>
      </div>
      ${ev.critique ? `<div class="text-[11px] text-rose-800 bg-rose-50 p-2 rounded border border-rose-100"><strong>Critique:</strong> ${ev.critique}</div>` : ''}
    `;
    container.appendChild(card);
  });
}
```

---

### Step 4: Live Browser Verification

1. Start your FastAPI server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
2. Open your web browser to:
   👉 **`http://localhost:8000`**

3. **Verify the 60-Second Demo Loop:**
   - Click **Alex (28)** $\rightarrow$ Watch the form populate with $75,000 income, $10,000 student loan, and Aggressive risk.
   - Click **Generate AI Financial Plan** $\rightarrow$ Watch the loading spinner and then the active plan checklist appear.
   - Click **Inspect HHH Scorecard** $\rightarrow$ Verify the Helpful (4/4), Honest (4/4), and Harmless (4/4) scores appear in the modal.
   - Click **Worked** on Action 1 $\rightarrow$ Verify the status changes to `WORKED`.
   - Click **Didn't Work** on Action 2 $\rightarrow$ Enter comment: *"Minimum payment was too high"* $\rightarrow$ Verify status changes to `DID NOT WORK`.

---

## 5. Common Pitfalls & Zero-Question FAQ

* **Q: Do I need Node.js or npm to run this frontend?**  
  *A:* No! This is a zero-build frontend. FastAPI serves the HTML/JS directly via its `StaticFiles` middleware, and Tailwind CSS loads via CDN.
* **Q: How does this work with our pytest suite?**  
  *A:* All backend unit tests remain 100% green. The frontend is an interface layer that communicates exclusively with our tested `/api/v1` REST endpoints.

---

## 6. Git Commit, Push & Trello Progression

Once verified:

### 1. Stage, Commit and Push
```bash
git add app/main.py app/static/
git commit -m "feat(ui): implement interactive web demo dashboard with one-click persona loader and HHH scorecard inspector"
git push origin main
```

### 2. Update Trello Card
1. Navigate to **[Task 10 Card on Trello](https://trello.com/c/6af705b7df5da00fad956a0b)**.
2. Check off all checklist items.
3. Move the card from **`IN PROGRESS`** $\rightarrow$ **`DONE`**!

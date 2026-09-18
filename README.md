# ⚡ WorkforceAI — Dynamic Workforce & Resource Allocation System

> **A Complete, Demo-Ready Full-Stack Web Application for Hackathons & Enterprise Operations**  
> Combining **Machine Learning (Scikit-Learn Random Forest)** for duration and suitability prediction with **Constraint Optimization (Google OR-Tools CP-SAT)** for mathematical employee-task scheduling and event-driven dynamic reallocations.

---

## 🎯 Executive Overview & Core Problem

Organizations face continuous shifts in employee skills, dynamic workloads, availability, experience, locations, and real-time performance. Simultaneously, incoming tasks vary in required skills, SLA windows, priority, and estimated duration.

Static rule-based scheduling systems fail because they cannot predict realistic completion times or adapt dynamically when disruptions occur.

**WorkforceAI** solves this by establishing a clear two-stage intelligence pipeline:
1. **Machine Learning (Random Forest)** predicts task completion time and employee suitability based on historical patterns and structured feature vectors.
2. **Mathematical Optimization (Google OR-Tools CP-SAT)** evaluates all candidate pairings under hard capacity, active status, and skill constraints to find the optimal assignment schedule.
3. **Dynamic Reallocation Engine** detects live operational disruptions (e.g., employee sick leave, workload spikes, sudden high-priority tasks) and triggers real-time reassignment with complete explainability.

---

## 🏗️ Architecture & Technology Stack

```
                                    WORKFORCE-AI PIPELINE
                                    
 [ Live DB State ] ────► [ Feature Extraction ] ────► [ Scikit-Learn Random Forest ]
 (Employees, Tasks)     (Skills, Load, SLA)           - Predicted Completion Time (hrs)
                                                      - Employee-Task Suitability Score
                                                                     │
                                                                     ▼
 [ Reallocation Audit ] ◄──── [ Dynamic Assignment ] ◄──── [ Google OR-Tools CP-SAT ]
  - Differential Log           - Auto-Assign to DB          - Hard Capacity & Active Rules
  - In-App Notifications       - Explainability Reasons     - Multi-Criteria Maximization
```

### 💻 Technology Stack:
- **Frontend**: React 18, Vite, Vanilla CSS (Design System with Dark Glassmorphism & Cyber Accents), Lucide Icons, Recharts Interactive Visualizers.
- **Backend**: Python 3, FastAPI, RESTful APIs, SQLAlchemy 2.0 ORM, Pydantic V2 validation, PyJWT, Bcrypt.
- **Database**: SQLite (local zero-setup execution, architected for instant PostgreSQL swap via `DATABASE_URL`).
- **AI / ML**: Scikit-Learn `RandomForestRegressor` (Dual-Head inference for Completion Time & Suitability Score), Pandas, NumPy, Joblib.
- **Optimization**: Google OR-Tools `cp_model.CpModel` (Constraint Programming Solver).

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** and **npm**

### 1. Launch with One Click (Windows)
Double-click or run from PowerShell / Command Prompt:
```cmd
run_project.bat
```
This script automatically validates your environment, starts the FastAPI backend on port `8000`, starts the Vite frontend on port `5173`, and opens the services.

---

### 2. Manual Startup

#### Backend:
```bash
# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies (if needed)
pip install -r requirements.txt

# Train Random Forest model & seed database
python ml/train_model.py
python backend/seed.py

# Start FastAPI server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Frontend:
```bash
cd frontend
npm install
npm run dev
```

---

## 🌐 Application URLs

| Service | URL | Description |
| :--- | :--- | :--- |
| **Frontend Application** | [http://localhost:5173](http://localhost:5173) | Interactive Web Platform |
| **Backend REST API** | [http://localhost:8000](http://localhost:8000) | Root Health API |
| **Interactive Swagger Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | OpenAPI Interactive Playground |
| **ReDoc Documentation** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Detailed Schema Definitions |

---

## 🔐 Demo Credentials (3 User Roles)

| Role | Email | Password | Console Capabilities |
| :--- | :--- | :--- | :--- |
| **ADMIN / HR** | `admin@demo.com` | `admin123` | Full org directory, employee lifecycle, system audit logs, department capacity. |
| **MANAGER / LEAD** | `manager@demo.com` | `manager123` | Task backlog CRUD, AI Allocation Cockpit, Live Event Simulator, Team Workloads. |
| **EMPLOYEE (Priya)** | `employee@demo.com` | `employee123` | Personal profile, self-service skill/certification updates, task queue status. |

*(The login screen also includes 1-Click Demo Buttons for instant role switching during hackathon judging).*

---

## 🧠 AI / ML Engine: Random Forest Regressor

### How Random Forest is Used:
The Random Forest model is **strictly responsible for prediction**, not combinatorial optimization.

1. **Feature Engineering**:
   - `skill_match_ratio`: Ratio of employee skills intersecting task requirements (0.0 to 1.0).
   - `experience_years`: Total professional experience in years.
   - `current_workload_pct`: Dynamic load percentage $(CurrentWorkload / Capacity) \times 100$.
   - `availability_hours`: Free capacity headroom $(Capacity - CurrentWorkload)$.
   - `performance_score`: Historical performance metric (0–100).
   - `location_match`: Geographic / remote alignment $(1.0 \text{ or } 0.0)$.
   - `priority_weight`: Integer weight ($1=\text{Low}, 2=\text{Med}, 3=\text{High}, 4=\text{Critical}$).
   - `estimated_hours` & `sla_urgency_hours`: Task scope and SLA duration window.
   - `task_complexity`: Calculated heuristic rating (1 to 5).

2. **Dual-Head Output**:
   - **Predicted Completion Time ($R^2 \approx 0.98$)**: Non-linear regression estimating realistic execution duration taking into account developer speed, experience, and current workload friction.
   - **Suitability Score ($R^2 \approx 0.94$)**: 0–100 composite match probability.

3. **Model Artifact**:
   Serialized to `ml/models/workforce_rf_model.joblib` and cached in memory upon FastAPI startup.

---

## ⚙️ Optimization Engine: Google OR-Tools CP-SAT

### How OR-Tools Works:
Google OR-Tools acts as the **mathematical decision maker**, finding the optimal assignment matrix $X_{i,j} \in \{0, 1\}$ (assign employee $i$ to task $j$).

### 1. Hard Constraints:
- **Active & Available**: $X_{i,j} = 0$ if employee $i$ is inactive or marked `Unavailable`.
- **Skill Compatibility**: $X_{i,j} = 0$ if employee $i$ possesses 0 overlapping required skills for task $j$.
- **Capacity Constraint**: $\sum_j X_{i,j} \times \text{Duration}_j \le \text{RemainingCapacity}_i$.
- **Uniqueness**: $\sum_i X_{i,j} \le 1$ (Each task is assigned to at most 1 engineer).

### 2. Multi-Criteria Objective:
$$\text{Maximize } \sum_{i,j} X_{i,j} \times \Big( W_{\text{suit}} \cdot \text{Suitability}_{i,j} + W_{\text{skill}} \cdot \text{SkillMatch}_{i,j} + W_{\text{prio}} \cdot \text{Priority}_j - W_{\text{time}} \cdot \text{PredTime}_{i,j} - W_{\text{load}} \cdot \text{WorkloadPenalty}_i \Big)$$

### 3. Explainability Generation:
For every selected pairing, the system generates transparent bullet points:
- `✓ 95% skill match (Python, FastAPI, Docker)`
- `✓ 45% current workload (4.5h free capacity remaining)`
- `✓ Predicted completion time: 3.8h (SLA window: 12h)`
- `✓ Performance score: 94/100 (Engineering dept)`

---

## ⚡ Dynamic Reallocation Pipeline

When disruptions occur, the platform automatically rebalances work:

```
[ Event: "Employee Priya Unavailable" ]
               │
               ▼
[ Recalculate Dynamic Workloads ]
               │
               ▼
[ Run Random Forest Inferences on Backlog ]
               │
               ▼
[ Execute Google OR-Tools CP-SAT Solver ]
               │
               ▼
[ Differential Analysis (Old vs New Assignment) ]
               │
               ▼
[ Update DB: Reassign T101 from Priya -> Kumar ]
               │
               ▼
[ Log to AllocationHistory & Dispatch In-App Notification ]
```

---

## ⏱️ 5–7 Minute Hackathon Demo Walkthrough

Follow these steps for a demonstration to judges:

1. **Step 1: Introduction & Dashboard (1 min)**
   - Open `http://localhost:5173`.
   - Log in as **Manager** using the 1-Click Demo button.
   - Point out the Top KPI cards (Average Workload, SLA at Risk, Total Workforce).
   - Point out the visual workflow bar: `DATA → PREDICTION → OPTIMIZATION → ASSIGNMENT → MONITORING → REALLOCATION`.

2. **Step 2: Employee & Task Workload Introspection (1 min)**
   - Navigate to **Team Workload / Employees**.
   - Show how workload is dynamically calculated from assigned task hours (e.g. `4.5h / 8h = 56%`), not entered manually.
   - Open **Tasks & Sprints** and show the unassigned backlog tasks with varying priorities and SLA hours.

3. **Step 3: AI Allocation Engine Execution (1.5 min)**
   - Navigate to **AI Allocation**.
   - Click the prominent **"Run AI Allocation"** button.
   - Watch the Random Forest model infer completion times and OR-Tools solve the global constraints.
   - Inspect the **Explainability Cards** demonstrating why each candidate was matched.
   - Click **"Apply All Assignments"** to commit the matches to the database.

4. **Step 4: Interactive Live Disruption Simulation (1.5 min)**
   - Navigate to **Event Simulator / Live Monitoring** (or click **"Simulate Live Event"** in top nav).
   - Click **"Employee Unavailable"** (e.g., simulates sudden sick leave).
   - Show how the system detects the event, recomputes available capacity, triggers OR-Tools, reallocates tasks to the next best qualified engineer, and generates real-time notifications.

5. **Step 5: Audit Trail & Analytics (1 min)**
   - Open **Audit History** to show the immutable log showing `Priya -> Kumar (Trigger: Employee Unavailable)`.
   - Open **Team Analytics** to highlight the Workload Imbalance standard deviation chart and SLA compliance gauge.

---

## 🗄️ Database Architecture

| Table | Description |
| :--- | :--- |
| `users` | Role-based authentication accounts (`admin`, `manager`, `employee`). |
| `employees` | Employee profiles, skills JSON, capacity, dynamic workload hours, performance rating. |
| `tasks` | Task backlog, required skills JSON, priority, SLA hours, estimated duration, status. |
| `assignments` | Active task assignments with AI suitability scores and predicted completion times. |
| `allocation_history` | Audit trail recording all transitions, previous/new assignees, triggers, and reasons. |
| `monitoring_events` | Stream of live system disruptions, severity levels, and reallocated task tallies. |
| `notifications` | In-app notification alerts with read/unread flags. |

---

## 🧪 Automated Testing

Run the automated integration test suite:
```bash
python test_system.py
```
**Test Coverage**:
- Root & Health status
- Role-based authentication for Admin, Manager, and Employee
- Dynamic workload recalculation
- Scikit-Learn Random Forest Regressor predictions
- Google OR-Tools CP-SAT solver constraint enforcement
- Disruption simulation & automatic dynamic reallocation
- Dashboard and analytics metrics calculation

---

## 📜 License & Acknowledgements
- Developed for Hackathon demonstration.
- Built with Google OR-Tools, Scikit-Learn, FastAPI, React, and Vite.

# DispatchGrid v2

**Intelligent Workforce Scheduling, On-Demand Dispatch & Field Service Platform**

[![Status: Production Ready](https://img.shields.io/badge/Status-Complete%20%E2%9C%85-success)](https://github.com/Pranav2608445/Hack4Hire)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python-blue)](https://fastapi.tiangolo.com/)
[![Frontend: React + Vite](https://img.shields.io/badge/Frontend-React%2018%20%7C%20TypeScript%20%7C%20Tailwind-61dafb)](https://vitejs.dev/)
[![Database: SQLite](https://img.shields.io/badge/Database-SQLite%20%7C%20SQLAlchemy-lightgrey)](https://www.sqlite.org/)

An enterprise-grade, Uber-style field-service automation platform that unifies **AI-driven schedule optimization**, **real-time on-demand matching & dispatch**, **SLA tracking**, and **three role-based frontends** (Customer, Technician, and Admin Console) into a single cohesive ecosystem.

---

## 📑 Table of Contents

- [System Architecture](#-system-architecture)
- [Core Features & Frontends](#-core-features--frontends)
  - [1. Customer App (Mobile-First)](#1-customer-app-mobile-first)
  - [2. Technician App (Mobile-First Cockpit)](#2-technician-app-mobile-first-cockpit)
  - [3. Admin Control Center (Desktop-First Console)](#3-admin-control-center-desktop-first-console)
- [Intelligent Dispatch & Matching Engine](#-intelligent-dispatch--matching-engine)
- [SLA Management Engine](#-sla-management-engine)
- [Scheduling Optimization Engine (Phase 1–7)](#-scheduling-optimization-engine-phase-17)
- [Quick Start & Setup](#-quick-start--setup)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [Test Credentials](#-test-credentials)
- [REST API Reference](#-rest-api-reference)
- [Directory Structure](#-directory-structure)
- [Button Wiring & UI Audit](#-button-wiring--ui-audit)
- [License & Credits](#-license--credits)

---

## 🏛 System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CLIENT FRONTENDS (React 18)                     │
│  ┌──────────────────────┬──────────────────────┬────────────────────┐  │
│  │   Customer Portal    │  Technician Cockpit  │   Admin Console    │  │
│  │  (Uber-style Maps,   │ (Online/Offline,     │ (Fleet Map, KPIs,  │  │
│  │   Booking, Tracking) │  Offers, Navigation) │  SLA, Escalations) │  │
│  └──────────────────────┴──────────────────────┴────────────────────┘  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Axios / REST / WebSocket
┌───────────────────────────────────┴────────────────────────────────────┐
│                       BACKEND API (FastAPI + Python)                   │
│  ┌────────────────────┬────────────────────┬────────────────────────┐  │
│  │  JWT Auth & RBAC   │  Customer Router   │   Technician Router    │  │
│  ├────────────────────┼────────────────────┼────────────────────────┤  │
│  │    Admin Router    │  Matching Engine   │  SLA Background Engine │  │
│  ├────────────────────┼────────────────────┼────────────────────────┤  │
│  │  Greedy LFJ Engine │  ALNS Optimizer    │  Disruption Recovery   │  │
│  └────────────────────┴────────────────────┴────────────────────────┘  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SQLAlchemy ORM
┌───────────────────────────────────┴────────────────────────────────────┐
│                    DATABASE (SQLite: dispatchgrid.db)                  │
│  Users, Customer & Tech Profiles, Service Requests, Offers, Ratings,  │
│  Service Categories, SLA Tiers, Audit Logs, Scheduling Runs            │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🌟 Core Features & Frontends

DispatchGrid v2 includes three complete, dedicated user interfaces sharing a unified warm terracotta and espresso design system (`#C2531F` / `#2B2118` / `#FFF8F2`), accessible focus rings, dark mode support, and strict WCAG AA contrast.

### 1. Customer App (Mobile-First)
- **Live Interactive Map**: Full-screen canvas vector map showing the customer's location with animated nearby moving technician pins, real-time ETAs, and distance calculations.
- **Bottom Booking Sheet**:
  - Service category selector with real-time base rates and price-per-minute estimates.
  - Problem description & photo attachment upload preview.
  - Urgency level selector (**Normal**, **Urgent**, **Emergency**) explaining response targets.
  - Saved address book picker or current GPS coordinates.
  - Dynamic price and arrival time preview.
- **Live Radar Matching**: Pulse-animated *"Finding your technician..."* screen with cancellation option.
- **Real-Time Job Tracking Cockpit**:
  - 5-stage visual stepper: `Assigned` → `En route` → `Arrived` → `In progress` → `Completed`.
  - Live technician profile card (photo, name, rating, phone).
  - One-tap phone dialer (`tel:`) and in-app message modal.
  - Self-service booking cancellation with confirmation modal.
- **Post-Service Feedback**: 5-star rating selector, written review, and customizable technician tip ($0, $5, $10, custom).
- **Profile & Saved Addresses**: Saved address management (add, edit, delete with confirmation) and past booking history with "Book Again" shortcuts.

### 2. Technician App (Mobile-First Cockpit)
- **Giant Availability Toggle**: One-tap Online/Offline toggle with an animated pulse ring updating fleet visibility and matching eligibility.
- **Incoming Job Offer Modal**:
  - Full-screen job alert with a 60-second animated countdown timer bar.
  - Payout estimate, customer distance, urgency badge, and task scope.
  - Instant **Accept** (claims exclusive assignment) or **Decline** with mandatory reason selection (forwarding to the next best technician).
- **Active Job Cockpit**:
  - **Turn-by-Turn Navigation**: One-click external Google Maps launch directed to customer coordinates.
  - Single primary action button advancing the job lifecycle:
    - `I'm En Route` → `Arrived at Location`
    - `Save Diagnostic Note` (persists on-site field notes to the backend)
    - `Complete Job` (confirms diagnostic proof and prompts for review)
- **Earnings & Pay Analytics**: Daily and weekly income breakdowns, base pay vs. tips, and completed job counters.
- **Technician Profile**: Service radius slider (5 km to 50 km), max concurrent jobs capacity (1 to 5), verified certification level, and customer review cards.

### 3. Admin Control Center (Desktop-First Console)
- **Deep Espresso Navigation (`#2B2118`)**: High-contrast operations sidebar with notification badges.
- **Executive KPI Overview**:
  - Live counters: Total customers, technicians (online/offline/busy), active jobs by status.
  - Dispatch efficiency metrics: Assignment rate %, acceptance vs. rejection %, average time to assign.
  - SLA compliance percentage monitor and oldest unassigned job triage alert.
- **Real-Time Fleet Map**: Interactive canvas overview of all active technicians, ongoing jobs, and dynamic route lines with clickable detail cards.
- **Jobs & Dispatch Console**: Filterable by status and urgency with a right-hand detail drawer providing **Manual Assignment Overrides**, **Auto Re-Dispatch Triggers**, and **Cancellation**.
- **Escalation Incident Inbox**: Triage center for SLA-breached jobs and requests with exhausted offer cycles, featuring 1-click re-dispatch and manual assignment.
- **Technician Fleet Management**: Table with skills, performance, approve/suspend toggles, profile editing, and one-click CSV export.
- **Customer Directory**: Account activation toggles and comprehensive customer booking history drawers.
- **Feedback & CSAT**: Average rating tracker, review distribution histogram, and customer review resolution actions.
- **Revenue & Analytics Reports**: Top-earning technician leaderboard and direct CSV export for jobs and technicians.
- **Matching & SLA Settings**: Sliders to adjust algorithm scoring weights, offer timeout thresholds, service category CRUD, and SLA tier configuration.
- **System Audit Trail**: Searchable, immutable event log with side-by-side modal inspecting previous (`old_value`) vs. applied (`new_value`) JSON state diffs.

---

## ⚡ Intelligent Dispatch & Matching Engine

When a customer books a service request, the automated dispatch engine pairs the request with the highest-ranked available technician:

1. **Hard Constraint Filtering**:
   - Technician must be currently online and approved.
   - Technician must possess the required skill and certification level for the category.
   - Customer must be within technician's configured `service_radius_km`.
   - Technician must not exceed `max_concurrent_jobs`.
2. **Multi-Factor Weighted Scoring**:
   $$\text{Score} = w_{\text{dist}} \cdot S_{\text{dist}} + w_{\text{rating}} \cdot S_{\text{rating}} + w_{\text{workload}} \cdot S_{\text{workload}} + w_{\text{skill}} \cdot S_{\text{skill}} + w_{\text{acc}} \cdot S_{\text{acc}}$$
   *All weights are dynamically configurable via the Admin Settings console.*
3. **Automated Offer Cascade**:
   - Job is dispatched to the top-scoring candidate with a configurable countdown timer (default: 120s).
   - If rejected or expired, the engine advances to the next candidate automatically.
   - If all $N$ attempts are exhausted, the job is flagged and routed directly to the **Admin Escalation Inbox**.
4. **High-Risk & Emergency Prioritization**:
   - Broadcast to an expanded search radius (+30 km).
   - Filtered exclusively to senior certified technicians.
   - Shorter offer timeouts (60s) for rapid dispatch.
5. **Concurrency Safety**: Double-booking and race conditions are prevented using atomic database operations.

---

## ⏱ SLA Management Engine

- **Configurable SLA Tiers**:
  - **Critical**: 15 min response / 60 min resolution
  - **High**: 30 min response / 120 min resolution
  - **Normal**: 60 min response / 240 min resolution
  - **Low**: 120 min response / 480 min resolution
- **Deterministic Deadline Computation**: Calculated and stamped at booking creation.
- **Proactive Breach Detection**: Background worker continuously evaluates deadlines; jobs exceeding 80% of their window are marked `at_risk`.
- **Auto-Escalation**: Breached and at-risk jobs trigger real-time operator alerts and priority escalation.

---

## 🧠 Scheduling Optimization Engine (Phase 1–7)

In addition to real-time dispatch, DispatchGrid includes an optimization engine for batch scheduling:
- **Greedy LFJ (Least Flexible Job First)**: 85–95% job coverage in 1–3 seconds using multi-factor constraint validation (HC1–HC10).
- **ALNS (Adaptive Large Neighborhood Search)**: Metaheuristic using 4 destroy operators × 3 repair operators with Simulated Annealing to reduce travel time, idle time, and SLA penalties.
- **Disruption Recovery**: Automatic rescheduling when technicians become unavailable or emergency jobs inject mid-day.

---

## 🚀 Quick Start & How to Run (Step-by-Step)

To run the full stack locally, open **two terminal windows** in the project root:

```
┌──────────────────────────────────────┐     ┌──────────────────────────────────────┐
│  TERMINAL 1: Backend (FastAPI :8000) │     │  TERMINAL 2: Frontend (Vite :3000)   │
│  .\backend\START_V2.bat              │     │  cd frontend; npm run dev            │
└──────────────────────────────────────┘     └──────────────────────────────────────┘
```

### Prerequisites
- **Python 3.10+** (tested through Python 3.13)
- **Node.js 18+** & **npm**

---

### Step 1: Start the Backend (Port 8000)

#### Option A: One-Click Script (Recommended for Windows)
From the root directory, simply run:
```powershell
.\backend\START_V2.bat
```
*This automatically activates `venv`, seeds database test users/categories/SLA tiers, and boots FastAPI on `http://127.0.0.1:8000`.*

#### Option B: Manual Command
```powershell
cd backend
.\venv\Scripts\activate
# (On macOS/Linux: source venv/bin/activate)

# Seed database with test users, technicians, and categories
python -m app.seed.v2_seed

# Start backend server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

> **Backend Status Checks:**
> - 🩺 Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)
> - 📖 Swagger UI Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
> - 📄 ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### Step 2: Start the Frontend (Port 3000)

In a **second terminal window**:
```powershell
cd frontend

# Install packages (first time only)
npm install

# Start Vite dev server
npm.cmd run dev
# (On macOS/Linux: npm run dev)
```

Now open **[http://localhost:3000](http://localhost:3000)** in your browser!

---

### Step 3: Quick 60-Second End-to-End Walkthrough

1. Go to **[http://localhost:3000](http://localhost:3000)**.
2. Click the **Customer Demo** pill on the login screen (fills `alice@example.com` / `Customer@1234`) and sign in.
3. Select **AC Service**, view nearby moving technician pins on the map with live ETA, and click **Book Now**.
4. In the top navbar, use the role switcher to switch to **Technician** (`raj.tech@example.com` / `Tech@1234`).
5. Flip the **Online Toggle** — the incoming job offer modal pops up with a 60-second countdown!
6. Click **Accept Offer**, test turn-by-turn navigation, click **En Route** → **Arrived** → **Complete Job**.
7. Switch to **Admin** (`admin@dispatchgrid.dev` / `Admin@1234`) to view fleet KPIs, the Live Map, Jobs triage drawer, and Escalations inbox.

---

## 🔑 Test Credentials

The login page contains **1-click quick login buttons** to fill credentials instantly:

| Role | Email | Password | Primary Landing Page |
|:---|:---|:---|:---|
| **Admin** | `admin@dispatchgrid.dev` | `Admin@1234` | `/admin/overview` |
| **Technician** | `raj.tech@example.com` | `Tech@1234` | `/technician/dashboard` |
| **Customer** | `alice@example.com` | `Customer@1234` | `/customer/book` |

*Additional accounts:*
- **Customers**: `bob@example.com`, `carol@example.com` (Password: `Customer@1234`)
- **Technicians**: `priya.tech@example.com`, `amit.tech@example.com`, `sunita.tech@example.com`, `deepak.tech@example.com` (Password: `Tech@1234`)

---

## 📡 REST API Reference

### 🔐 Authentication & Session
- `POST /api/auth/register` — Register a customer or technician
- `POST /api/auth/login` — Authenticate and receive JWT access token
- `GET /api/auth/me` — Current user profile and role verification
- `POST /api/auth/logout` — Revoke active session

### 👤 Customer Endpoints
- `GET /api/customer/profile` | `PATCH /api/customer/profile` — View and edit profile
- `GET /api/customer/addresses` | `POST /api/customer/addresses` — Manage saved addresses
- `DELETE /api/customer/addresses/{index}` — Remove saved address
- `GET /api/customer/categories` — List active service offerings
- `GET /api/customer/nearby-technicians` — Query nearest technicians with ETA & distance
- `POST /api/customer/requests` — Submit a service request
- `GET /api/customer/requests` — View customer's booking history
- `GET /api/customer/requests/{id}` — Live tracking and assigned tech location
- `PATCH /api/customer/requests/{id}/cancel` — Cancel active request
- `POST /api/customer/requests/{id}/rate` — Submit rating, review text, and optional tip

### 🔧 Technician Endpoints
- `GET /api/technician/profile` | `PATCH /api/technician/profile` — Manage bio, radius & capacity
- `PATCH /api/technician/availability` — Toggle Online / Offline status
- `PATCH /api/technician/location` — Broadcast updated GPS coordinates
- `GET /api/technician/offers` — View pending job offers
- `POST /api/technician/offers/{id}/accept` — Accept job offer
- `POST /api/technician/offers/{id}/reject` — Reject job offer with reason
- `GET /api/technician/jobs` | `GET /api/technician/jobs/{id}` — Assigned job history and detail
- `PATCH /api/technician/jobs/{id}/status` — Advance status (`en_route`, `in_progress`, `completed`)
- `POST /api/technician/jobs/{id}/notes` — Append on-site diagnostic notes
- `GET /api/technician/earnings` — Summary of gross earnings, base pay, and tips
- `GET /api/technician/ratings` — Customer feedback review history

### 🛡 Admin Endpoints
- `GET /api/admin/dashboard/overview` — Executive KPIs, fleet breakdown, oldest unassigned job
- `GET /api/admin/dashboard/dispatch` — Dispatch metrics, offer acceptance/rejection percentages
- `GET /api/admin/dashboard/workload` — Per-technician capacity utilization
- `GET /api/admin/dashboard/sla` — SLA compliance rates, breached and at-risk counters
- `GET /api/admin/dashboard/feedback` — CSAT stats and rating distribution
- `GET /api/admin/dashboard/revenue` — Financial summaries and top technician earnings
- `GET /api/admin/customers` | `PATCH /api/admin/customers/{id}` — Manage customer accounts
- `GET /api/admin/technicians` | `PATCH /api/admin/technicians/{id}/approve` | `.../suspend` — Fleet controls
- `GET /api/admin/jobs` — Full jobs registry with filters
- `PATCH /api/admin/jobs/{id}/assign` — Force manual technician assignment
- `PATCH /api/admin/jobs/{id}/reassign` — Trigger auto re-dispatch matching
- `PATCH /api/admin/jobs/{id}/cancel` — Admin cancellation override
- `GET /api/admin/config/matching` | `PATCH /api/admin/config/matching` — Algorithm scoring weights
- `GET /api/admin/config/categories` — Service catalog management
- `GET /api/admin/config/sla-tiers` — SLA tier definitions
- `GET /api/admin/audit-log` — Full system audit history
- `GET /api/admin/export/jobs` | `GET /api/admin/export/technicians` — CSV data downloads

---

## 📁 Directory Structure

```
Hackathon_Project/
├── .gitignore                      # Comprehensive root gitignore
├── README.md                       # Master system documentation
├── backend/
│   ├── START_V2.bat                # One-click startup script (Windows)
│   ├── TEST_CREDENTIALS.md         # Credentials quick-reference
│   ├── dispatchgrid.db             # Local SQLite database
│   ├── requirements.txt            # Python dependencies
│   ├── app/
│   │   ├── main.py                 # FastAPI application factory
│   │   ├── config.py               # Settings and environment bindings
│   │   ├── database.py             # SQLAlchemy session & Base
│   │   ├── models/                 # ORM entities (User, Request, Offer, SLA, etc.)
│   │   ├── schemas/                # Pydantic validation models
│   │   ├── services/               # Auth, matching engine & SLA services
│   │   ├── routers/                # REST endpoints (auth, customer, tech, admin)
│   │   ├── scheduler/              # Phase 1-7 scheduling & optimization engine
│   │   └── seed/                   # Database seeders (v2_seed.py)
│   └── tests/                      # Automated test suite
│
└── frontend/
    ├── package.json                # Dependencies and scripts
    ├── vite.config.ts              # Vite server & proxy configuration
    ├── tailwind.config.js          # Design tokens & color theme configuration
    └── src/
        ├── App.tsx                 # Routing and role guards
        ├── index.css               # Design system CSS variables & animations
        ├── types/index.ts          # TypeScript domain type definitions
        ├── services/apiClient.ts   # Axios API client
        ├── context/AuthContext.tsx # Authentication state and role management
        ├── components/
        │   ├── common/             # Zero-dependency UI library (Button, Modal, Map, etc.)
        │   └── layout/             # Navbar, Sidebar, DashboardLayout
        └── pages/
            ├── Login.tsx           # Multi-role authentication & test pills
            ├── customer/           # BookService, MyBookings, CustomerProfile, History
            ├── technician/         # MySchedule, JobHistory, Earnings, TechnicianProfile
            └── admin/              # Overview, LiveMap, Jobs, Escalations, Feedback, Settings, Audit
```

---

## 🎯 Button Wiring & UI Audit

In accordance with the **Golden Rule ("No Dead UI")**, every interactive element in DispatchGrid v2 is verified to perform an action, update state, navigate routes, or execute an API request with visible feedback (toast notifications, modal confirmation, or status advancement).

👉 **Review the complete [Button Wiring Checklist](file:///C:/Users/sathe/.gemini/antigravity/brain/071aaf50-09a0-4187-bb60-62b56653bcd6/button_wiring_checklist.md)** auditing all 54 user actions across the Customer, Technician, and Admin interfaces.

---

## 📄 License & Credits

Built for the Field Service Intelligent Dispatch Hackathon.  
© 2026 DispatchGrid Team. All rights reserved.

# Smart Delivery Routing

A backend system for solving the Vehicle Routing Problem (VRP) in last-mile delivery operations. It assigns delivery orders to vehicles, optimizes routes using road network data, and coordinates real-time communication between dispatchers and drivers.

---

## Problem Statement

Last-mile delivery is one of the most expensive parts of the supply chain. Dispatchers manually assigning orders to drivers results in suboptimal routes, excessive fuel costs, and unbalanced vehicle loads. This system automates that process: given a set of pending orders, vehicles, and warehouses, it computes optimized delivery routes that respect vehicle weight and volume capacity, minimizes total travel distance, and notifies drivers immediately when their route is ready.

---

## Features

### Order Management
- Full CRUD with status lifecycle: `pending → assigned → delivered / cancelled`
- Bulk import via CSV upload
- Paginated listing with filters (status, warehouse) and partial search by order ID
- Status transitions are enforced by a state machine

### Route Optimization
- **Nearest Neighbor** solver — greedy construction heuristic with weight and volume capacity constraints
- Asynchronous (`POST /optimize/async`) modes
- Capacity constraints: weight and volume per vehicle
- Multi-warehouse support — vehicles start from their assigned warehouse
- Distance matrix computed via OSRM (real road network), cached in Redis for 7 days
- Haversine fallback if OSRM is unavailable

### Batch Automation
- Each optimize run stamps a `optimization_job_id` on assigned orders
- When all orders in a batch reach terminal status (delivered/cancelled), the system automatically triggers the next optimization run without manual intervention
- Admin is notified via WebSocket when auto-trigger fires

### Real-Time Notifications
- **WebSocket** (`/ws`): admin dashboard receives live events when orders are delivered or a new optimization is triggered
- **FCM Push Notifications**: drivers receive a push notification with stop count and distance when their route is assigned
- Notification history stored in DB, accessible via API

### Driver Management
- Drivers are Supabase auth users with a `driver` role
- FCM token registration endpoint for mobile app integration
- Each driver is linked to a vehicle

### KPI Reporting
- Per-vehicle: stops count, distance, weight fill rate, volume fill rate
- Fleet-level: total distance, vehicles used, unassigned order count, average fill rates

---

## System Architecture

The project follows **Clean Architecture** with strict unidirectional dependency flow:

```
Interface → Application → Domain ← Infrastructure
```

| Layer | Location | Responsibility |
|---|---|---|
| **Domain** | `domain/` | Entities (`Order`, `Vehicle`, `Route`), repository interfaces, validators. No external dependencies. |
| **Application** | `application/` | Use cases, solvers, KPI computation, service abstractions. Depends only on domain. |
| **Infrastructure** | `infrastructure/` | Supabase repositories, Celery tasks, Redis client, OSRM client, FCM service, WebSocket manager. Implements domain interfaces. |
| **Interface** | `interface/api/` | FastAPI routers, Pydantic schemas, dependency injection wiring. Infrastructure imports are centralized in `dependencies.py` — routers never import concrete implementations. |

**Dependency Inversion in practice**: routers receive `OrderRepository` (domain interface) via `Depends()`, never `SupabaseOrderRepository` (concrete). All wiring happens in `dependencies.py`.

**Celery tasks** act as a secondary entry point (analogous to HTTP routers): they call application use cases and coordinate infrastructure side effects, following the same inward-only dependency direction.

---

## Tech Stack

| Category | Technology |
|---|---|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **Background Jobs** | Celery 5, Redis |
| **Database** | Supabase (PostgreSQL + Auth) |
| **Routing Engine** | OSRM (self-hosted, car profile) |
| **Optimization** | Custom Nearest Neighbor (VRP solver) |
| **Push Notifications** | Firebase Cloud Messaging (FCM) |
| **Real-Time** | FastAPI WebSocket |
| **Caching** | Redis (distance matrix, job tracking) |
| **Visualization** | Streamlit + Folium (standalone UI) |
| **DevOps** | Docker, Docker Compose, GitHub Actions |
| **Code Quality** | Ruff (linter), pytest |

---

## Project Structure

```
src/smart_delivery_routing/
├── domain/
│   ├── models.py          # Order, Vehicle, Warehouse, Route, Driver, Notification
│   ├── repositories.py    # Abstract repository interfaces
│   └── validators.py      # Domain validation rules
│
├── application/
│   ├── routing_use_cases.py   # optimize_routes() — core VRP workflow
│   ├── order_use_cases.py     # CRUD + status transitions + batch completion signal
│   ├── kpi.py                 # KPI computation and comparison
│   ├── data_loader.py         # CSV parsing for bulk import
│   ├── services.py            # Abstract ports: RouteSolver, DistanceCalculator, JobService
│   └── solvers/
│       ├── nearest_neighbor.py   # Greedy O(n²) solver (active)
│       └── ortools_solver.py     # OR-Tools VRP with GLS metaheuristic (implemented, not yet wired)
│
├── infrastructure/
│   ├── celery/tasks.py          # run_optimize Celery task
│   ├── osrm/                    # OSRM distance matrix + road geometry
│   ├── supabase/repositories/   # Concrete DB implementations
│   ├── redis_client.py          # Matrix cache + job tracking
│   ├── fcm_notification_service.py
│   ├── websocket.py             # In-memory ConnectionManager
│   └── job_service.py           # CeleryRedisJobService
│
└── interface/api/
    ├── routers/           # One file per resource
    ├── dependencies.py    # All DI wiring — the only place infrastructure is imported
    ├── schemas.py         # Pydantic request/response models
    └── __init__.py        # FastAPI app + middleware + exception handlers
```

---

## Core Workflow

```
1. Import
   CSV upload (orders, vehicles, warehouses)
   → validation → upsert to Supabase

2. Optimize (async)
   POST /optimize/async
   → Celery task queued in Redis
   → distance matrix computed (OSRM, cached in Redis)
   → solver assigns orders to vehicles respecting capacity
   → orders marked ASSIGNED, optimization_job_id stamped
   → routes saved to DB
   → FCM push sent to each driver's mobile app
   → job result stored in Redis (24h TTL)

3. Delivery
   Driver updates order → DELIVERED
   → WebSocket event broadcast to admin dashboard
   → system checks if all orders in batch are terminal
   → if batch complete: next optimization auto-triggered
   → WebSocket event: optimization.auto_triggered

4. Query
   GET /jobs/{job_id} → full route result with geometry
   GET /notifications → driver's notification history
```

---

## Optimization Logic

### Nearest Neighbor
Greedy construction heuristic. For each vehicle, repeatedly picks the nearest unassigned order that fits within remaining weight and volume capacity. After each vehicle finishes its route, it is repositioned to the warehouse nearest to the next batch of pending orders. **O(n²)** per vehicle, fast and deterministic. Used for both synchronous and asynchronous optimization.

An OR-Tools CVRP solver (Guided Local Search, 30s time limit) is implemented in `solvers/ortools_solver.py` and available for future integration as a higher-quality alternative.

### Distance Matrix
- OSRM `/table/v1/driving` API computes actual road distances in km for all (warehouse + order) location pairs
- Matrix is MD5-keyed by sorted location set and cached in Redis for 7 days
- Haversine formula used as fallback if OSRM is unreachable

### Constraints
- Vehicle weight capacity (`max_weight`)
- Vehicle volume capacity (`max_volume`)
- Orders filtered to `PENDING` status before solving

### KPIs
| Metric | Description |
|---|---|
| Total distance | Sum of all route distances in km |
| Vehicles used | Number of vehicles with at least one stop |
| Unassigned count | Orders that could not be assigned due to capacity |
| Fill rate (weight) | Actual weight loaded / vehicle max weight, per vehicle |
| Fill rate (volume) | Actual volume loaded / vehicle max volume, per vehicle |

---

## API Overview

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | — | Sign in, returns JWT + role |
| POST | `/auth/logout` | Any | Sign out |
| POST | `/import/upload` | Admin | Bulk CSV import (orders, vehicles, warehouses) |
| GET | `/orders` | Driver+ | List orders with pagination, filter, search |
| POST | `/orders` | Admin | Create order |
| PUT | `/orders/{id}` | Admin | Update order (triggers batch check on terminal status) |
| DELETE | `/orders/{id}` | Admin | Delete pending order |
| POST | `/optimize` | Admin | Synchronous optimization (all solvers) |
| POST | `/optimize/async` | Admin | Queue async optimization job |
| GET | `/jobs/{job_id}` | Admin | Poll job status and result |
| GET | `/vehicles` | Driver+ | List vehicles |
| GET | `/warehouses` | Driver+ | List warehouses |
| POST | `/drivers/fcm-token` | Driver | Register FCM token |
| GET | `/notifications` | Driver | Get notification history |
| PATCH | `/notifications/{id}/read` | Driver | Mark notification as read |
| WS | `/ws?token=` | Admin | Real-time event stream |

---

## Environment Variables

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key   # used for internal Celery auto-trigger

# Redis
REDIS_URL=redis://localhost:6379/0

# OSRM
OSRM_URL=http://localhost:5000

# Firebase (path to service account JSON)
FIREBASE_CREDENTIALS=/app/firebase-service-account.json
```

---

## Running Locally

### Prerequisites
- Docker & Docker Compose
- OSRM map data pre-processed for your region (`.osrm` files)
- Supabase project with tables: `orders`, `vehicles`, `warehouses`, `drivers`, `notifications`, `routes`
- Firebase project with a service account JSON

### 1. Clone and configure
```bash
git clone https://github.com/phvghuy/smart-delivery-routing
cd smart-delivery-routing
touch .env
```

### 2. Place required files

**Firebase credentials**

1. Go to [Firebase Console](https://console.firebase.google.com) → Project Settings → Service Accounts
2. Click **Generate new private key** → download the JSON file
3. Rename it to `firebase-service-account.json` and place it in the project root

**OSRM map data**

OSRM requires pre-processed map data for your delivery region. The steps below use Vietnam as an example.

```bash
# Download OSM data for your region from https://download.geofabrik.de
wget https://download.geofabrik.de/asia/vietnam-latest.osm.pbf

# Pre-process using Docker (car profile)
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/car.lua /data/vietnam-latest.osm.pbf
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-partition /data/vietnam-latest.osrm
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-customize /data/vietnam-latest.osrm

# Move all generated files into the data directory
mv vietnam-latest.osrm* src/smart_delivery_routing/infrastructure/osrm/data/
```

> Pre-processing can take several minutes and requires ~4GB of RAM for country-level data. For smaller regions, resource requirements are significantly lower.

### 3. Start all services
```bash
docker compose up --build
```

API available at `http://localhost:8000`
Interactive docs at `http://localhost:8000/docs`

### 4. Supabase schema (run in SQL Editor)
```sql
-- Orders
CREATE TABLE orders (
    order_id             TEXT PRIMARY KEY,
    warehouse_id         TEXT NOT NULL,
    dest_lat             FLOAT NOT NULL,
    dest_lng             FLOAT NOT NULL,
    weight               FLOAT NOT NULL,
    volume               FLOAT NOT NULL,
    status               TEXT NOT NULL DEFAULT 'pending',
    optimization_job_id  TEXT
);

-- Vehicles
CREATE TABLE vehicles (
    vehicle_id            TEXT PRIMARY KEY,
    current_warehouse_id  TEXT NOT NULL,
    capacity_weight       FLOAT NOT NULL,
    capacity_volume       FLOAT NOT NULL
);

-- Warehouses
CREATE TABLE warehouses (
    warehouse_id  TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    lat           FLOAT NOT NULL,
    lng           FLOAT NOT NULL
);

-- Drivers (linked to Supabase auth users)
CREATE TABLE drivers (
    driver_id   TEXT PRIMARY KEY,
    vehicle_id  TEXT,
    fcm_token   TEXT
);

-- Notifications
CREATE TABLE notifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id   TEXT NOT NULL,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL,
    data        JSONB DEFAULT '{}',
    is_read     BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Routes (persisted optimization results)
CREATE TABLE routes (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id            TEXT NOT NULL,
    vehicle_id        TEXT NOT NULL,
    total_distance_km FLOAT,
    stops             JSONB,
    created_at        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON routes(job_id);
CREATE INDEX ON routes(vehicle_id);
```

---

## Docker Setup

| Container | Image | Purpose |
|---|---|---|
| `api` | Custom (Python 3.12) | FastAPI application + Uvicorn |
| `worker` | Custom (Python 3.12) | Celery worker for async optimization |
| `redis` | `redis:7-alpine` | Task queue broker + result backend + matrix cache |
| `osrm` | `osrm/osrm-backend` | Self-hosted road routing engine (MLD algorithm) |

All containers share the same Redis instance. The `api` and `worker` containers mount `firebase-service-account.json` as a read-only volume. DNS is set to `8.8.8.8` on both to ensure Supabase/FCM connectivity from within Docker.

---

## Background Job System

```
POST /optimize/async
  → CeleryRedisJobService.submit(token)
    → run_optimize.delay(token)           # queued in Redis
    → job_id registered in Redis (24h TTL)
    → returns job_id immediately (HTTP 202)

Worker picks up task:
  run_optimize(token)
    → authenticate Supabase client with user token
    → fetch orders, vehicles, warehouses
    → compute/cache distance matrix (OSRM → Redis)
    → NearestNeighborSolver.solve()
    → persist routes to DB
    → stamp optimization_job_id on assigned orders
    → send FCM notifications to drivers
    → result stored in Redis via Celery backend

GET /jobs/{job_id}
  → AsyncResult from Celery backend
  → status: pending | success | failure | expired
```

Redis serves three distinct roles: Celery broker, Celery result backend, and distance matrix cache.

---

## Deployment

### VPS with Docker Compose
```bash
# On VPS
git clone https://github.com/phvghuy/smart-delivery-routing
cd smart-delivery-routing

# Copy files that are not in git
# - .env (see Environment Variables section)
# - firebase-service-account.json (see Running Locally → Step 2)
# - OSRM pre-processed data (see Running Locally → Step 2)

# Start
docker compose up -d --build
```

Open port `8000` in your VPS firewall.

### Frontend
The admin dashboard is a separate Reactjs application deployed on Vercel. The backend CORS config allows `https://sdr-admin.vercel.app`.

---

## Future Improvements

- **Rate limiting** on `/optimize/async` to prevent queue flooding (`slowapi`)
- **WebSocket scale-out** using Redis Pub/Sub to support multiple API instances
- **Real-time driver location tracking** — drivers stream GPS → admin map updates via existing WebSocket
- **2-opt local search** post-processing on top of Nearest Neighbor for better route quality
- **Time windows** (VRPTW) — delivery slots per order
- **Structured logging** with `structlog` replacing `print` statements in Celery tasks
- **Health check endpoint** for Docker/load balancer readiness probes

---

## Tradeoffs & Engineering Decisions

**Single shared Supabase client per request, authenticated with the user's JWT** — RLS policies enforce data isolation at the DB level. The service role key is only used for internal Celery auto-trigger where no user context is available.

**Distance matrix cached in Redis for 7 days** — the location set (warehouses + orders) changes rarely between optimize runs. Caching avoids repeated OSRM calls that can take several seconds for large fleets.

**Batch completion signal returned from use case, not raised as exception** — `update_order()` returns `(Order, bool)` rather than emitting a side effect or raising a domain event. This keeps the use case testable and the trigger logic in the interface layer where infrastructure access (Celery, WebSocket) is appropriate.

**In-memory WebSocket ConnectionManager** — sufficient for single-instance deployment. Acknowledged limitation: does not survive horizontal scaling without a Redis Pub/Sub adapter.

**Geometry not persisted to DB** — road geometry (polylines from OSRM) is derived data, recomputable from stops at any time. Storing it would add significant JSONB payload per route row with no query benefit.

---

## Resume/Portfolio Value

This project demonstrates:

- **Clean Architecture** applied to a real domain problem with enforced layer separation and dependency inversion
- **VRP algorithm implementation** from scratch (Nearest Neighbor) with capacity constraints across multiple vehicles and warehouses
- **Asynchronous task processing** with Celery and Redis in a Dockerized environment
- **Real-time systems** with WebSocket (admin) and FCM push notifications (mobile)
- **Domain-driven state machines** for order lifecycle management
- **External service integration**: OSRM (self-hosted), Supabase (auth + RLS + DB), Firebase
- **CI/CD** with GitHub Actions (lint + tests on every push)
- **Production concerns**: Redis caching strategy, auto-trigger with idempotency, service role auth for internal tasks

# Smart Delivery Routing

![CI](https://github.com/phvghuy/smart-delivery-routing/actions/workflows/ci.yml/badge.svg)

A backend system for an e-commerce logistics platform. Manages the full lifecycle of a parcel — from the moment a seller creates a shipping request to final delivery at the customer's door — including hub-to-hub linehaul coordination and last-mile driver route assignment.

---

## Problem Statement

When a seller submits a shipping request, the system must:

1. Identify the nearest origin hub (to the pickup address) and destination hub (to the delivery address)
2. Track the parcel through 10 status transitions from pickup to delivery
3. Coordinate truck trips between hubs (linehaul)
4. Automatically assign delivery routes to available drivers and notify them in real time

---

## Architecture

The project follows **Domain-Driven Design (DDD)** with five independent bounded contexts:

```
interface/api/        ← FastAPI routers, Pydantic schemas, dependency injection wiring
application/          ← Use cases (orchestration only, no infrastructure imports)
domain/
  ├── shipping/       ← ShippingRequest: orders submitted by sellers
  ├── linehaul/       ← Hub, Parcel, Truck, TruckTrip: inter-hub transport
  ├── delivery/       ← Driver, DeliveryRoute, RouteStop: last-mile delivery
  ├── tracking/       ← TrackingEvent: parcel status history
  └── shared/         ← Shared value objects: Address, Location, Load, Money
infrastructure/
  ├── supabase/       ← Concrete repository implementations (PostgreSQL via Supabase)
  ├── haversine.py    ← Distance matrix calculator for hub selection
  ├── telemetry.py    ← OpenTelemetry setup (traces exported to Jaeger)
  └── celery/         ← Async tasks: process_shipping_request, create_delivery_routes
```

**Dependency rule:** Domain has no knowledge of infrastructure. Infrastructure implements abstract repository interfaces defined by the domain. Routers receive interfaces via `Depends()` — never concrete classes. All wiring is centralized in `dependencies.py`.

---

## Parcel Lifecycle

```
[Seller creates ShippingRequest]
            │
            ▼ returns immediately
        CREATED
            │
            ▼ Celery task (async)
  System finds nearest hubs (Haversine)
            │
      ┌─────┴─────┐
      │           │
  Both found   Not found
      │           │
  ACCEPTED     REJECTED
      │
      ▼
Parcel: AWAITING_PICKUP
        │
        ▼  driver picks up
      PICKED_UP
        │
        ▼  delivered to origin hub
    AT_ORIGIN_HUB
        │
        ▼  loaded onto truck
  IN_LINEHAUL_TRANSIT
        │
        ▼  truck arrives at destination
  AT_DESTINATION_HUB
        │
        ▼  driver assigned
   OUT_FOR_DELIVERY
        │
   ┌────┴─────┐
   │          │
DELIVERED  DELIVERY_FAILED → RETURNED
```

Every status transition creates a `TrackingEvent` recording the source location (driver / hub / truck / customer / system).

---

## Features

### Shipping
- Full request validation: addresses, load (weight + volume), receiver info, COD amount
- `POST /shipping-requests` returns immediately with `CREATED` status — processing is non-blocking
- A Celery task picks up the request asynchronously: finds the nearest origin and destination hubs, creates the parcel, then updates status to `ACCEPTED` or `REJECTED`

### Linehaul
- Hub management (types: sorting center, local hub)
- Truck management with weight and volume capacity
- Truck trip scheduling and tracking: PLANNED → DEPARTED → ARRIVED
- Add/remove parcels from a trip with real-time capacity checking

### Last-Mile Delivery
- Automatic route generation: parcels grouped by hub, drivers grouped by hub, greedy assignment by capacity
- Stop order optimized with nearest-neighbor algorithm (OSRM for real road distances, Haversine fallback)
- Drivers receive FCM push notifications when a route is assigned
- Admin receives real-time events via WebSocket
- Drivers update each stop: DELIVERED or FAILED (with a specific reason)

### Tracking
- Full event history for every parcel
- Each event records its location source type (driver, hub, truck, customer, system)

---

## Tech Stack

| Category | Technology |
|---|---|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **Database** | PostgreSQL (hosted on Supabase) |
| **Background Jobs** | Celery 5, Redis |
| **Routing Engine** | OSRM (self-hosted), Haversine fallback |
| **Push Notifications** | Firebase Cloud Messaging (FCM) |
| **Real-Time** | WebSocket (FastAPI native) |
| **Observability** | OpenTelemetry SDK + Jaeger |
| **Containerization** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions (lint + unit tests) |
| **Code Quality** | Ruff, pytest, pytest-cov |

---

## Project Structure

```
src/smart_delivery_routing/
├── domain/
│   ├── shipping/       # ShippingRequest, status enum, validator
│   ├── linehaul/       # Hub, Parcel, Truck, TruckTrip + validators
│   ├── delivery/       # Driver, DeliveryRoute, RouteStop + validators
│   ├── tracking/       # TrackingEvent
│   └── shared/         # Address, Location, Load, Money, Capacity
│
├── application/
│   ├── shipping_use_cases.py        # create, list, get, update status
│   ├── parcel_use_cases.py          # 10 state transition use cases
│   ├── truck_trip_use_cases.py      # depart/arrive with batch parcel updates
│   ├── delivery_route_use_cases.py  # greedy assignment + nearest-neighbor
│   ├── driver_use_cases.py
│   └── hub_use_cases.py
│
├── infrastructure/
│   ├── supabase/repositories/       # Concrete implementations per domain
│   ├── haversine.py                 # NxN distance matrix calculator
│   ├── telemetry.py                 # OpenTelemetry + Jaeger initialization
│   ├── celery/                      # Async task: create_delivery_routes
│   ├── fcm_notification_service.py
│   └── websocket.py
│
└── interface/api/
    ├── routers/         # One file per resource
    ├── dependencies.py  # All DI wiring in one place
    ├── schemas.py       # Pydantic request/response models
    └── __init__.py      # FastAPI app, middleware, telemetry init
```

---

## API Overview

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | — | Sign in, returns JWT |
| GET | `/shipping-requests` | Admin | List requests (cursor pagination) |
| POST | `/shipping-requests` | Admin | Create request → returns `CREATED`, processing handled async by Celery |
| GET | `/shipping-requests/{id}` | Admin | Get request detail |
| PATCH | `/shipping-requests/{id}/status` | Admin | Manual status update |
| GET | `/parcels` | Admin | List parcels |
| PATCH | `/parcels/{id}/pickup` | Admin | Driver picks up parcel |
| PATCH | `/parcels/{id}/deliver-to-origin-hub` | Admin | Parcel delivered to origin hub |
| PATCH | `/parcels/{id}/dispatch-linehaul` | Admin | Parcel loaded onto truck |
| PATCH | `/parcels/{id}/arrive-destination-hub` | Admin | Truck arrives at destination hub |
| PATCH | `/parcels/{id}/dispatch-for-delivery` | Admin | Assign driver for last-mile |
| PATCH | `/parcels/{id}/confirm-delivery` | Admin | Confirm successful delivery |
| PATCH | `/parcels/{id}/fail-delivery` | Admin | Mark delivery failed (with reason) |
| GET | `/hubs` | Admin | List hubs |
| POST | `/hubs` | Admin | Create hub |
| GET | `/trucks` | Admin | List trucks |
| GET | `/truck-trips` | Admin | List truck trips |
| POST | `/truck-trips` | Admin | Schedule a truck trip |
| POST | `/truck-trips/{id}/depart` | Admin | Depart (batch-updates all parcels) |
| POST | `/truck-trips/{id}/arrive` | Admin | Arrive (batch-updates all parcels) |
| GET | `/drivers` | Admin | List drivers |
| POST | `/delivery-routes/generate` | Admin | Auto-generate delivery routes |
| GET | `/notifications` | Driver | Notification history |
| WS | `/ws?token=` | Admin | Real-time event stream |

---

## Running Locally

### Prerequisites
- Docker & Docker Compose
- `.env` file (see below)
- `firebase-service-account.json` from Firebase Console → Project Settings → Service Accounts
- OSRM pre-processed map data (optional — Haversine is used as fallback)

### Environment Variables

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
REDIS_URL=redis://redis:6379/0
OSRM_URL=http://osrm:5000
FIREBASE_CREDENTIALS=/app/firebase-service-account.json
```

### Start

```bash
git clone https://github.com/phvghuy/smart-delivery-routing
cd smart-delivery-routing

docker compose up --build
```

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Jaeger UI | http://localhost:16686 |

### Run Tests

```bash
uv run pytest tests/ -m "not integration" --tb=short
```

---

## CI/CD

GitHub Actions runs two parallel jobs on every push to `main`:

| Job | Steps |
|---|---|
| **lint** | `ruff check src/` — fails on any linting error |
| **test** | `pytest` with coverage report — fails if coverage drops below 30% |

---

## Observability

The system integrates **OpenTelemetry + Jaeger** for distributed tracing:

- Every HTTP request automatically generates a root span (FastAPI auto-instrumentation)
- The Celery worker also exports traces — `process_shipping_request` creates a root span with three child spans: `hub.find_nearest_origin`, `hub.find_nearest_destination`, `parcel.create`
- Traces are exported to Jaeger via gRPC (OTLP protocol) from both the API and worker containers
- View traces at [http://localhost:16686](http://localhost:16686) after running `docker compose up`

---

## Design Decisions

**Haversine distance matrix for hub selection** — On shipping request creation, the system fetches all active hubs and places the target address at index 0 of the location list. `HaversineDistanceCalculator.compute_matrix()` returns an NxN matrix; `matrix[0][1:]` gives distances from the target to every hub in one pass. Reuses existing infrastructure instead of writing a separate nearest-hub function.

**Explicit state machine per transition** — Each of the 10 parcel status transitions has its own use case function (`pickup_parcel`, `deliver_to_origin_hub`, `dispatch_linehaul`...) rather than a generic `update_status`. Each transition carries different side effects: updating `current_hub_id`, clearing it, choosing the right `TrackingEvent` location type.

**Fake repository pattern in tests** — Unit tests use in-memory implementations of abstract repositories. No Supabase or Redis required. Tests that need external services are marked `@pytest.mark.integration` and skipped in CI.

**Centralized DI wiring** — `dependencies.py` is the only file that knows `SupabaseHubRepository` exists. Routers depend only on `HubRepository` (the abstract interface). Swapping the database layer requires changes in exactly one file.

**Async shipping pipeline via Celery** — `POST /shipping-requests` validates and persists the request, then enqueues a Celery task via the abstract `JobService` interface. The router never imports Celery directly, keeping the interface layer decoupled from infrastructure. The worker runs `process_shipping_request` independently: finds hubs, creates the parcel, and updates the status. This separation means the API response time is not affected by hub lookup or parcel creation latency.
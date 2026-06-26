from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from smart_delivery_routing.infrastructure.firebase import initialize_firebase
from smart_delivery_routing.infrastructure.telemetry import setup_telemetry

from .routers import auth, delivery_routes, drivers, hubs, notifications, parcels, shipping_requests, truck_trips, trucks, ws, health

initialize_firebase()

app = FastAPI(title="Smart Delivery Routing")

setup_telemetry(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://sdr-admin.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(drivers.router)
app.include_router(delivery_routes.router)
app.include_router(hubs.router)
app.include_router(trucks.router)
app.include_router(truck_trips.router)
app.include_router(shipping_requests.router)
app.include_router(parcels.router)
app.include_router(notifications.router)
app.include_router(ws.router)
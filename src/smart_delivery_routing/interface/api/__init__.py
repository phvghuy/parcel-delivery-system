from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from smart_delivery_routing.infrastructure.firebase import initialize_firebase

# TODO: restore after domain.models migration
# from smart_delivery_routing.application.data_loader import LoadError
# from smart_delivery_routing.application.order_use_cases import (
#     InvalidStatusTransition, OrderAlreadyExists, OrderNotDeletable, OrderNotFound,
# )
# from smart_delivery_routing.application.routing_use_cases import NoPendingOrders, ValidationFailed
# from smart_delivery_routing.application.vehicle_use_cases import VehicleAlreadyExists, VehicleNotFound
# from smart_delivery_routing.application.warehouse_use_cases import (
#     WarehouseAlreadyExists, WarehouseHasActiveOrders, WarehouseNotFound,
# )

from .routers import auth, delivery_routes, drivers, hubs, notifications, parcels, shipping_requests, truck_trips, trucks, ws

# TODO: restore after domain.models migration
# from .routers import imports, jobs, optimize, orders, vehicles, warehouses

initialize_firebase()

app = FastAPI(title="Smart Delivery Routing")

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

# TODO: restore after domain.models migration
# app.include_router(jobs.router)

# TODO: restore after domain.models migration
# app.include_router(imports.router)
# app.include_router(orders.router)
# app.include_router(vehicles.router)
# app.include_router(warehouses.router)
# app.include_router(optimize.router)


# TODO: restore after domain.models migration — exception handlers below
# @app.exception_handler(ValidationFailed)
# def handle_validation_failed(_, exc: ValidationFailed) -> JSONResponse:
#     return JSONResponse(
#         status_code=422,
#         content={"errors": [{"id": e.entity_id, "field": e.field, "reason": e.reason} for e in exc.errors]},
#     )

# @app.exception_handler(LoadError)
# def handle_load_error(_, exc: LoadError) -> JSONResponse:
#     return JSONResponse(status_code=400, content={"error": str(exc)})

# @app.exception_handler(NoPendingOrders)
# def handle_no_pending_orders(_, __: NoPendingOrders) -> JSONResponse:
#     return JSONResponse(status_code=400, content={"error": "No pending orders left."})

# @app.exception_handler(OrderNotFound)
# def handle_order_not_found(_, exc: OrderNotFound) -> JSONResponse:
#     return JSONResponse(status_code=404, content={"error": str(exc)})

# @app.exception_handler(OrderAlreadyExists)
# def handle_order_already_exists(_, exc: OrderAlreadyExists) -> JSONResponse:
#     return JSONResponse(status_code=409, content={"error": str(exc)})

# @app.exception_handler(InvalidStatusTransition)
# def handle_invalid_status_transition(_, exc: InvalidStatusTransition) -> JSONResponse:
#     return JSONResponse(status_code=422, content={"error": str(exc)})

# @app.exception_handler(OrderNotDeletable)
# def handle_order_not_deletable(_, exc: OrderNotDeletable) -> JSONResponse:
#     return JSONResponse(status_code=409, content={"error": str(exc)})

# @app.exception_handler(VehicleNotFound)
# def handle_vehicle_not_found(_, exc: VehicleNotFound) -> JSONResponse:
#     return JSONResponse(status_code=404, content={"error": str(exc)})

# @app.exception_handler(VehicleAlreadyExists)
# def handle_vehicle_already_exists(_, exc: VehicleAlreadyExists) -> JSONResponse:
#     return JSONResponse(status_code=409, content={"error": str(exc)})

# @app.exception_handler(WarehouseNotFound)
# def handle_warehouse_not_found(_, exc: WarehouseNotFound) -> JSONResponse:
#     return JSONResponse(status_code=404, content={"error": str(exc)})

# @app.exception_handler(WarehouseAlreadyExists)
# def handle_warehouse_already_exists(_, exc: WarehouseAlreadyExists) -> JSONResponse:
#     return JSONResponse(status_code=409, content={"error": str(exc)})

# @app.exception_handler(WarehouseHasActiveOrders)
# def handle_warehouse_has_active_orders(_, exc: WarehouseHasActiveOrders) -> JSONResponse:
#     return JSONResponse(status_code=409, content={"error": str(exc)})

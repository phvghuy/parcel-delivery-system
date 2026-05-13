from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from smart_delivery_routing.application.data_loader import LoadError
from smart_delivery_routing.application.use_cases import NoPendingOrders, ValidationFailed

from .routers import auth, imports, jobs, optimize

app = FastAPI(title="Smart Delivery Routing")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(imports.router)
app.include_router(optimize.router)
app.include_router(jobs.router)


@app.exception_handler(ValidationFailed)
def handle_validation_failed(_, exc: ValidationFailed) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"errors": [{"id": e.entity_id, "field": e.field, "reason": e.reason} for e in exc.errors]},
    )


@app.exception_handler(LoadError)
def handle_load_error(_, exc: LoadError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.exception_handler(NoPendingOrders)
def handle_no_pending_orders(_, __: NoPendingOrders) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": "No pending orders left."})

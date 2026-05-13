from pydantic import BaseModel, Field


# --- Auth ---

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    role: str


# --- Routing ---

class StopResponse(BaseModel):
    order_id: str
    lat: float
    lng: float


class RouteResponse(BaseModel):
    vehicle_id: str
    stops: list[StopResponse]
    total_distance_km: float


class VehicleKPIResponse(BaseModel):
    vehicle_id: str
    stops_count: int
    distance_km: float
    fill_rate_weight: float
    fill_rate_volume: float


class KPIReportResponse(BaseModel):
    total_distance_km: float
    vehicles_used: int
    unassigned_count: int
    average_fill_rate_weight: float
    average_fill_rate_volume: float
    per_vehicle: list[VehicleKPIResponse]


class SolverResultResponse(BaseModel):
    solver: str
    routes: list[RouteResponse]
    unassigned_orders: list[str]
    kpi: KPIReportResponse


class OptimizeResponse(BaseModel):
    results: list[SolverResultResponse]


class AsyncOptimizeResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # pending | success | failure | expired
    result: OptimizeResponse | None = None
    error: str | None = None

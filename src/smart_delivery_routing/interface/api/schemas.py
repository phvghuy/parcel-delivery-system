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
    geometry: list[list[float]] = []  # [[lat, lng], ...] following actual roads


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


# --- Orders CRUD ---

class OrderResponse(BaseModel):
    order_id: str
    warehouse_id: str
    lat: float
    lng: float
    weight: float
    volume: float
    status: str


class PaginatedOrderResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    page: int
    size: int
    pages: int


class CreateOrderRequest(BaseModel):
    order_id: str
    warehouse_id: str
    lat: float
    lng: float
    weight: float = Field(gt=0)
    volume: float = Field(gt=0)


class UpdateOrderRequest(BaseModel):
    warehouse_id: str
    lat: float
    lng: float
    weight: float = Field(gt=0)
    volume: float = Field(gt=0)
    status: str


# --- Vehicles CRUD ---

class VehicleResponse(BaseModel):
    vehicle_id: str
    current_warehouse_id: str
    max_weight: float
    max_volume: float


class CreateVehicleRequest(BaseModel):
    vehicle_id: str
    current_warehouse_id: str
    max_weight: float = Field(gt=0)
    max_volume: float = Field(gt=0)


class UpdateVehicleRequest(BaseModel):
    current_warehouse_id: str
    max_weight: float = Field(gt=0)
    max_volume: float = Field(gt=0)


# --- Warehouses CRUD ---

class WarehouseResponse(BaseModel):
    warehouse_id: str
    name: str
    lat: float
    lng: float


class CreateWarehouseRequest(BaseModel):
    warehouse_id: str
    name: str
    lat: float
    lng: float


class UpdateWarehouseRequest(BaseModel):
    name: str
    lat: float
    lng: float

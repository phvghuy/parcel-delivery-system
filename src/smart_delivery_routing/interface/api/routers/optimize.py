from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer

from smart_delivery_routing.application.solvers.nearest_neighbor import NearestNeighborSolver
from smart_delivery_routing.application.tasks import run_optimize
from smart_delivery_routing.application.use_cases import OptimizeRoutesInput, OptimizeRoutesOutput, optimize_routes
from smart_delivery_routing.domain.ports import OrderRepository, RouteSolver, VehicleRepository, WarehouseRepository
from smart_delivery_routing.config import OSRM_URL
from smart_delivery_routing.infrastructure.osrm.distance import OSRMDistanceCalculator
from smart_delivery_routing.infrastructure.redis_client import register_job
from ..dependencies import get_order_repo, get_vehicle_repo, get_warehouse_repo, require_admin
from ..schemas import AsyncOptimizeResponse, KPIReportResponse, OptimizeResponse, RouteResponse, SolverResultResponse, StopResponse, VehicleKPIResponse

_security = HTTPBearer()

router = APIRouter(tags=["optimize"])

_SOLVERS: list[tuple[str, RouteSolver]] = [
    ("nearest_neighbor", NearestNeighborSolver()),
]
_distance_calculator = OSRMDistanceCalculator(base_url=OSRM_URL)


@router.post("/optimize", response_model=OptimizeResponse)
def optimize(
    order_repo: OrderRepository = Depends(get_order_repo),
    vehicle_repo: VehicleRepository = Depends(get_vehicle_repo),
    warehouse_repo: WarehouseRepository = Depends(get_warehouse_repo),
    _: None = Depends(require_admin),
) -> OptimizeResponse:
    orders = order_repo.get_orders()
    vehicles = vehicle_repo.get_vehicles()
    warehouses = warehouse_repo.get_warehouses()
    return _run_all_solvers(
        OptimizeRoutesInput(orders=orders, vehicles=vehicles, warehouses=warehouses),
        order_repo,
        vehicle_repo,
    )


@router.post("/optimize/async", response_model=AsyncOptimizeResponse, status_code=202)
def optimize_async(
    token=Depends(_security),
    _: None = Depends(require_admin),
) -> AsyncOptimizeResponse:
    task = run_optimize.delay(token.credentials)
    register_job(task.id)
    return AsyncOptimizeResponse(job_id=task.id)


def _run_all_solvers(
    input: OptimizeRoutesInput,
    order_repo: OrderRepository,
    vehicle_repo: VehicleRepository,
) -> OptimizeResponse:
    return OptimizeResponse(
        results=[
            _to_solver_result(solver_name, optimize_routes(input, solver, _distance_calculator, order_repo, vehicle_repo))
            for solver_name, solver in _SOLVERS
        ]
    )


def _to_solver_result(solver_name: str, output: OptimizeRoutesOutput) -> SolverResultResponse:
    return SolverResultResponse(
        solver=solver_name,
        routes=[
            RouteResponse(
                vehicle_id=r.vehicle_id,
                stops=[StopResponse(order_id=s.order_id, lat=s.location.lat, lng=s.location.lng) for s in r.stops],
                total_distance_km=r.total_distance,
            )
            for r in output.result.routes
        ],
        unassigned_orders=output.result.unassigned_orders,
        kpi=KPIReportResponse(
            total_distance_km=output.kpi.total_distance_km,
            vehicles_used=output.kpi.vehicles_used,
            unassigned_count=output.kpi.unassigned_count,
            average_fill_rate_weight=output.kpi.average_fill_rate_weight,
            average_fill_rate_volume=output.kpi.average_fill_rate_volume,
            per_vehicle=[
                VehicleKPIResponse(
                    vehicle_id=v.vehicle_id,
                    stops_count=v.stops_count,
                    distance_km=v.distance_km,
                    fill_rate_weight=v.fill_rate_weight,
                    fill_rate_volume=v.fill_rate_volume,
                )
                for v in output.kpi.per_vehicle
            ],
        ),
    )

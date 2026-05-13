from dataclasses import dataclass

from smart_delivery_routing.domain.models import Order, RoutingResult, Vehicle, Warehouse
from smart_delivery_routing.domain.ports import DistanceCalculator, OrderRepository, RouteSolver, VehicleRepository
from smart_delivery_routing.domain.validators import ValidationError, validate_orders, validate_vehicles

from .kpi import KPIReport, compute_kpi


@dataclass(frozen=True)
class OptimizeRoutesInput:
    orders: list[Order]
    vehicles: list[Vehicle]
    warehouses: list[Warehouse]


@dataclass(frozen=True)
class OptimizeRoutesOutput:
    result: RoutingResult
    kpi: KPIReport


class ValidationFailed(Exception):
    def __init__(self, errors: list[ValidationError]) -> None:
        self.errors = errors
        super().__init__(f"{len(errors)} validation error(s)")

    
class NoPendingOrders(Exception):
    pass


def optimize_routes(
    input: OptimizeRoutesInput,
    solver: RouteSolver,
    distance_calculator: DistanceCalculator,
    order_repo: OrderRepository,
    vehicle_repo: VehicleRepository,
) -> OptimizeRoutesOutput:
    _validate(input.orders, input.vehicles)
    pending_orders = [o for o in input.orders if o.status == "pending"]
    if not pending_orders:
        raise NoPendingOrders("No pending orders left.")

    distance_matrix = _build_distance_matrix(input.orders, input.warehouses, distance_calculator)
    result = solver.solve(input.orders, input.vehicles, input.warehouses, distance_matrix)
    kpi = compute_kpi(result, input.orders, input.vehicles)
    _persist_result(result, input.vehicles, order_repo, vehicle_repo)
    return OptimizeRoutesOutput(result=result, kpi=kpi)


def _persist_result(
    result: RoutingResult,
    vehicles: list[Vehicle],
    order_repo: OrderRepository,
    vehicle_repo: VehicleRepository,
) -> None:
    assigned_ids = [s.order_id for r in result.routes for s in r.stops]
    if assigned_ids:
        order_repo.mark_assigned(assigned_ids)

    vehicle_map = {v.vehicle_id: v for v in vehicles}
    for route in result.routes:
        vehicle = vehicle_map.get(route.vehicle_id)
        if vehicle:
            vehicle_repo.update_warehouse(vehicle.vehicle_id, vehicle.current_warehouse_id)


def _validate(orders: list[Order], vehicles: list[Vehicle]) -> None:
    errors = validate_vehicles(vehicles) + validate_orders(orders, vehicles)
    if errors:
        raise ValidationFailed(errors)


def _build_distance_matrix(
    orders: list[Order],
    warehouses: list[Warehouse],
    distance_calculator: DistanceCalculator,
) -> list[list[float]]:
    locations = [w.location for w in warehouses] + [o.location for o in orders]
    return distance_calculator.compute_matrix(locations)

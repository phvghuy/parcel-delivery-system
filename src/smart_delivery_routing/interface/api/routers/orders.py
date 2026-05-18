from fastapi import APIRouter, Depends, Query

from smart_delivery_routing.application import order_use_cases
from smart_delivery_routing.domain.models import Location, Order, OrderStatus
from smart_delivery_routing.domain.repositories import OrderRepository
from ..dependencies import get_order_repo, require_admin, require_driver
from ..schemas import CreateOrderRequest, OrderResponse, PaginatedOrderResponse, UpdateOrderRequest

router = APIRouter(prefix="/orders", tags=["orders"])


def _to_response(order: Order) -> OrderResponse:
    return OrderResponse(
        order_id=order.order_id,
        warehouse_id=order.warehouse_id,
        lat=order.location.lat,
        lng=order.location.lng,
        weight=order.weight,
        volume=order.volume,
        status=order.status.value,
    )


@router.get("", response_model=PaginatedOrderResponse)
def list_orders(
    page: int = Query(1, ge=1, description="Page number, starting from 1"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status: pending, assigned, delivered"),
    warehouse_id: str | None = Query(None, description="Filter by warehouse ID"),
    search: str | None = Query(None, description="Search by order ID (partial match)"),
    order_repo: OrderRepository = Depends(get_order_repo),
    _: None = Depends(require_driver),
) -> PaginatedOrderResponse:
    status_filter = OrderStatus(status) if status else None
    result = order_use_cases.list_orders_paginated(page, size, order_repo, status_filter, warehouse_id, search)
    return PaginatedOrderResponse(
        items=[_to_response(o) for o in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: str,
    order_repo: OrderRepository = Depends(get_order_repo),
    _: None = Depends(require_driver),
) -> OrderResponse:
    return _to_response(order_use_cases.get_order(order_id, order_repo))


@router.post("", response_model=OrderResponse, status_code=201)
def create_order(
    body: CreateOrderRequest,
    order_repo: OrderRepository = Depends(get_order_repo),
    _: None = Depends(require_admin),
) -> OrderResponse:
    order = Order(
        order_id=body.order_id,
        warehouse_id=body.warehouse_id,
        location=Location(lat=body.lat, lng=body.lng),
        weight=body.weight,
        volume=body.volume,
    )
    return _to_response(order_use_cases.create_order(order, order_repo))


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: str,
    body: UpdateOrderRequest,
    order_repo: OrderRepository = Depends(get_order_repo),
    _: None = Depends(require_admin),
) -> OrderResponse:
    order = Order(
        order_id=order_id,
        warehouse_id=body.warehouse_id,
        location=Location(lat=body.lat, lng=body.lng),
        weight=body.weight,
        volume=body.volume,
        status=OrderStatus(body.status),
    )
    return _to_response(order_use_cases.update_order(order_id, order, order_repo))


@router.delete("/{order_id}", status_code=204)
def delete_order(
    order_id: str,
    order_repo: OrderRepository = Depends(get_order_repo),
    _: None = Depends(require_admin),
) -> None:
    order_use_cases.delete_order(order_id, order_repo)

from dataclasses import dataclass

from smart_delivery_routing.domain.models import Order, OrderStatus
from smart_delivery_routing.domain.repositories import OrderRepository
from smart_delivery_routing.domain.validators import validate_order_fields

from .routing_use_cases import ValidationFailed


@dataclass(frozen=True)
class PagedOrders:
    items: list[Order]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.size))  # ceiling division


# --- Domain exceptions ---

@dataclass(frozen=True)
class OrderNotFound(Exception):
    order_id: str

    def __str__(self) -> str:
        return f"Order '{self.order_id}' not found."


@dataclass(frozen=True)
class OrderAlreadyExists(Exception):
    order_id: str

    def __str__(self) -> str:
        return f"Order '{self.order_id}' already exists."


@dataclass(frozen=True)
class InvalidStatusTransition(Exception):
    order_id: str
    from_status: OrderStatus
    to_status: OrderStatus

    def __str__(self) -> str:
        return (
            f"Cannot transition order '{self.order_id}' "
            f"from '{self.from_status.value}' to '{self.to_status.value}'."
        )


@dataclass(frozen=True)
class OrderNotDeletable(Exception):
    order_id: str
    status: OrderStatus

    def __str__(self) -> str:
        return (
            f"Order '{self.order_id}' cannot be deleted "
            f"while in status '{self.status.value}'."
        )


# --- Status transition rules ---
# DELIVERED is terminal; PENDING ↔ ASSIGNED is allowed; any → DELIVERED is allowed.
_ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING:   {OrderStatus.ASSIGNED, OrderStatus.DELIVERED, OrderStatus.CANCELLED},
    OrderStatus.ASSIGNED:  {OrderStatus.PENDING, OrderStatus.DELIVERED, OrderStatus.CANCELLED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


def _check_status_transition(order_id: str, current: OrderStatus, next_: OrderStatus) -> None:
    if current == next_:
        return
    if next_ not in _ALLOWED_TRANSITIONS[current]:
        raise InvalidStatusTransition(order_id=order_id, from_status=current, to_status=next_)


# --- Use cases ---

def list_orders(repo: OrderRepository) -> list[Order]:
    return repo.get_orders()


def list_orders_paginated(
    page: int,
    size: int,
    repo: OrderRepository,
    status: OrderStatus | None = None,
    warehouse_id: str | None = None,
    search: str | None = None,
) -> PagedOrders:
    items, total = repo.get_orders_paginated(page, size, status, warehouse_id, search)
    return PagedOrders(items=items, total=total, page=page, size=size)


def get_order(order_id: str, repo: OrderRepository) -> Order:
    order = repo.get_order_by_id(order_id)
    if order is None:
        raise OrderNotFound(order_id=order_id)
    return order


def create_order(order: Order, repo: OrderRepository) -> Order:
    errors = validate_order_fields(order)
    if errors:
        raise ValidationFailed(errors)

    if repo.get_order_by_id(order.order_id) is not None:
        raise OrderAlreadyExists(order_id=order.order_id)

    return repo.create_order(order)


def update_order(order_id: str, updated: Order, repo: OrderRepository) -> Order:
    errors = validate_order_fields(updated)
    if errors:
        raise ValidationFailed(errors)

    existing = repo.get_order_by_id(order_id)
    if existing is None:
        raise OrderNotFound(order_id=order_id)

    _check_status_transition(order_id, existing.status, updated.status)

    return repo.update_order(updated)


def delete_order(order_id: str, repo: OrderRepository) -> None:
    existing = repo.get_order_by_id(order_id)
    if existing is None:
        raise OrderNotFound(order_id=order_id)

    if existing.status != OrderStatus.PENDING:
        raise OrderNotDeletable(order_id=order_id, status=existing.status)

    repo.delete_order(order_id)

from abc import ABC, abstractmethod

from .models import Order, OrderStatus, Vehicle, Warehouse


class OrderRepository(ABC):
    @abstractmethod
    def save_orders(self, orders: list[Order]) -> None: ...

    @abstractmethod
    def get_orders(self) -> list[Order]: ...

    @abstractmethod
    def get_orders_paginated(
        self,
        page: int,
        size: int,
        status: OrderStatus | None = None,
        warehouse_id: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Order], int]: ...

    @abstractmethod
    def get_order_by_id(self, order_id: str) -> Order | None: ...

    @abstractmethod
    def get_pending_orders(self) -> list[Order]: ...

    @abstractmethod
    def create_order(self, order: Order) -> Order: ...

    @abstractmethod
    def update_order(self, order: Order) -> Order: ...

    @abstractmethod
    def delete_order(self, order_id: str) -> None: ...

    @abstractmethod
    def mark_assigned(self, order_ids: list[str]) -> None: ...


class VehicleRepository(ABC):
    @abstractmethod
    def save_vehicles(self, vehicles: list[Vehicle]) -> None: ...

    @abstractmethod
    def get_vehicles(self) -> list[Vehicle]: ...

    @abstractmethod
    def get_vehicle_by_id(self, vehicle_id: str) -> Vehicle | None: ...

    @abstractmethod
    def create_vehicle(self, vehicle: Vehicle) -> Vehicle: ...

    @abstractmethod
    def update_vehicle(self, vehicle: Vehicle) -> Vehicle: ...

    @abstractmethod
    def delete_vehicle(self, vehicle_id: str) -> None: ...

    @abstractmethod
    def update_warehouse(self, vehicle_id: str, warehouse_id: str) -> None: ...


class WarehouseRepository(ABC):
    @abstractmethod
    def save_warehouses(self, warehouses: list[Warehouse]) -> None: ...

    @abstractmethod
    def get_warehouses(self) -> list[Warehouse]: ...

    @abstractmethod
    def get_warehouse_by_id(self, warehouse_id: str) -> Warehouse | None: ...

    @abstractmethod
    def create_warehouse(self, warehouse: Warehouse) -> Warehouse: ...

    @abstractmethod
    def update_warehouse(self, warehouse: Warehouse) -> Warehouse: ...

    @abstractmethod
    def delete_warehouse(self, warehouse_id: str) -> None: ...

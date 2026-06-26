from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from uuid import UUID

from ..shared.value_objects import Address, Load, Money


@dataclass(frozen=True)
class Receiver:
    name: str
    phone: str


class ShippingRequestStatus(IntEnum):
    CREATED = 1
    ACCEPTED = 2
    REJECTED = 3
    CANCELLED = 4
    FAILED = 5


class ServiceLevel(IntEnum):
    STANDARD = 1
    EXPRESS = 2
    SAME_DAY = 3


@dataclass
class ShippingRequest:
    id: UUID
    external_order_id: str
    seller_id: UUID
    pickup_address: Address
    delivery_address: Address
    receiver: Receiver
    load: Load
    created_at: datetime
    service_type: ServiceLevel = ServiceLevel.STANDARD
    cod_amount: Money | None = None
    status: ShippingRequestStatus = ShippingRequestStatus.CREATED

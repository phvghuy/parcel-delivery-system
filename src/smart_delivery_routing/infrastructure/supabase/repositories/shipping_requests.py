from datetime import datetime
from uuid import UUID

from supabase import Client

from smart_delivery_routing.domain.shipping import (
    Receiver,
    ServiceLevel,
    ShippingRequest,
    ShippingRequestQuery,
    ShippingRequestRepository,
    ShippingRequestStatus,
)
from smart_delivery_routing.domain.shared import Address, Load, Location, Money


class SupabaseShippingRequestRepository(ShippingRequestRepository):
    def __init__(self, client: Client) -> None:
        self._client = client

    def create(self, request: ShippingRequest) -> ShippingRequest:
        row = self._client.table("shipping_requests").insert(self._to_row(request)).execute()
        return self._to_model(row.data[0])

    def get_by_id(self, request_id: UUID) -> ShippingRequest | None:
        response = (
            self._client.table("shipping_requests")
            .select("*")
            .eq("id", str(request_id))
            .maybe_single()
            .execute()
        )
        if response is None or response.data is None:
            return None
        return self._to_model(response.data)

    def list(self, query: ShippingRequestQuery) -> list[ShippingRequest]:
        q = (
            self._client.table("shipping_requests")
            .select("*")
            .order("created_at", desc=True)
            .order("id", desc=True)
            .limit(query.page_size + 1)  # fetch one extra to detect next page
        )

        if query.statuses:
            q = q.in_("status", [s.value for s in query.statuses])

        if query.service_types:
            q = q.in_("service_type", [t.value for t in query.service_types])

        if query.cursor_created_at is not None:
            cursor_ts = query.cursor_created_at.isoformat()
            cursor_id = str(query.cursor_id)
            # rows where created_at < cursor, OR same timestamp but id < cursor_id
            q = q.or_(
                f"created_at.lt.{cursor_ts},"
                f"and(created_at.eq.{cursor_ts},id.lt.{cursor_id})"
            )

        response = q.execute()
        return [self._to_model(row) for row in response.data]

    def update_status(self, request_id: UUID, status: ShippingRequestStatus) -> None:
        self._client.table("shipping_requests").update(
            {"status": status.value}
        ).eq("id", str(request_id)).execute()

    @staticmethod
    def _to_row(request: ShippingRequest) -> dict:
        row = {
            "id": str(request.id),
            "external_order_id": request.external_order_id,
            "seller_id": str(request.seller_id),
            "pickup_address_text": request.pickup_address.text,
            "pickup_lat": request.pickup_address.location.lat,
            "pickup_lng": request.pickup_address.location.lng,
            "delivery_address_text": request.delivery_address.text,
            "delivery_lat": request.delivery_address.location.lat,
            "delivery_lng": request.delivery_address.location.lng,
            "receiver_name": request.receiver.name,
            "receiver_phone": request.receiver.phone,
            "weight": request.load.weight,
            "volume": request.load.volume,
            "service_type": request.service_type.value,
            "status": request.status.value,
            "created_at": request.created_at.isoformat(),
        }
        if request.cod_amount is not None:
            row["cod_amount"] = request.cod_amount.amount
            row["cod_currency"] = request.cod_amount.currency
        return row

    @staticmethod
    def _to_model(row: dict) -> ShippingRequest:
        cod_amount = None
        if row.get("cod_amount") is not None:
            cod_amount = Money(
                amount=row["cod_amount"],
                currency=row.get("cod_currency", "VND"),
            )
        return ShippingRequest(
            id=UUID(row["id"]),
            external_order_id=row["external_order_id"],
            seller_id=UUID(row["seller_id"]),
            pickup_address=Address(
                text=row["pickup_address_text"],
                location=Location(lat=float(row["pickup_lat"]), lng=float(row["pickup_lng"])),
            ),
            delivery_address=Address(
                text=row["delivery_address_text"],
                location=Location(lat=float(row["delivery_lat"]), lng=float(row["delivery_lng"])),
            ),
            receiver=Receiver(name=row["receiver_name"], phone=row["receiver_phone"]),
            load=Load(weight=float(row["weight"]), volume=float(row["volume"])),
            created_at=datetime.fromisoformat(row["created_at"]),
            service_type=ServiceLevel(row["service_type"]),
            cod_amount=cod_amount,
            status=ShippingRequestStatus(row["status"]),
        )
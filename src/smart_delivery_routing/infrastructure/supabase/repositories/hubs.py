from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from supabase import Client

from smart_delivery_routing.domain.linehaul import Hub, HubRepository, HubStatus, HubType
from smart_delivery_routing.domain.shared import Address, Location
from smart_delivery_routing.domain.linehaul import HubQuery
from smart_delivery_routing.infrastructure.haversine import HaversineDistanceCalculator

_calculator = HaversineDistanceCalculator()


class SupabaseHubRepository(HubRepository):
    def __init__(self, client: Client) -> None:
        self._client = client

    def create(self, hub: Hub) -> Hub:
        row = self._client.table("hubs").insert(self._to_row(hub)).execute()
        return self._to_model(row.data[0])
    
    def get_by_id(self, hub_id: UUID) -> Hub | None:
        response = (
            self._client.table("hubs")
            .select("*")
            .eq("id", str(hub_id))
            .maybe_single()
            .execute()
        )
        if response is None or response.data is None:
            return None
        return self._to_model(response.data)
    
    def list(self, query: HubQuery) -> tuple[list[Hub], int]:
        from_idx = (query.page - 1) * query.page_size
        to_idx = from_idx + query.page_size - 1

        q = self._client.table("hubs").select("*", count="exact").range(from_idx, to_idx)
        if not query.include_deleted:
            q = q.is_("deleted_at", "null")

        if query.statuses:
            q = q.in_("status", [s.value for s in query.statuses])

        if query.types:
            q = q.in_("type", [t.value for t in query.types])

        if query.search:
            subjects = [s.strip() for s in query.search.split(",") if s.strip()]
            conditions = ",".join(
                f"name.ilike.%{s}%,address_text.ilike.%{s}%"
                for s in subjects
            )
            q = q.or_(conditions)

        response = q.execute()
        return [self._to_model(row) for row in response.data], response.count or 0
    
    def update(self, hub: Hub) -> Hub:
        response = (
            self._client.table("hubs")
            .update(self._to_row(hub))
            .eq("id", str(hub.id))
            .execute()
        )
        return self._to_model(response.data[0])

    def delete(self, hub_id: UUID) -> None:
        self._client.table("hubs").update(
            {"deleted_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", str(hub_id)).execute()

    def find_nearest(self, location: Location, limit: int = 1) -> list[Hub]:
        response = (
            self._client.table("hubs")
            .select("*")
            .eq("status", HubStatus.ACTIVE.value)
            .is_("deleted_at", "null")
            .execute()
        )
        hubs = [self._to_model(row) for row in response.data]
        if not hubs:
            return []
        all_locations = [location] + [h.address.location for h in hubs]
        matrix = _calculator.compute_matrix(all_locations)
        distances = matrix[0][1:]
        ranked = sorted(enumerate(distances), key=lambda x: x[1])
        return [hubs[i] for i, _ in ranked[:limit]]

    @staticmethod
    def _to_row(hub: Hub) -> dict:
        return {
            "id": str(hub.id),
            "name": hub.name,
            "type": hub.type.value,
            "address_text": hub.address.text,
            "lat": hub.address.location.lat,
            "lng": hub.address.location.lng,
            "status": hub.status.value,
        }

    @staticmethod
    def _to_model(row: dict) -> Hub:
        return Hub(
            id=UUID(row["id"]),
            name=row["name"],
            type=HubType(row["type"]),
            address=Address(
                text=row["address_text"],
                location=Location(lat=float(row["lat"]), lng=float(row["lng"])),
            ),
            status=HubStatus(row["status"]),
            deleted_at=datetime.fromisoformat(row["deleted_at"]) if row.get("deleted_at") else None,
        )
from __future__ import annotations
from smart_delivery_routing.domain.linehaul import HubRepository, Hub, HubType, HubStatus, HubQuery
from smart_delivery_routing.infrastructure.sqlalchemy.tables import hubs
from smart_delivery_routing.domain.shared import Address, Location
from smart_delivery_routing.infrastructure.redis_client import get_hub_cache, set_hub_cache
from smart_delivery_routing.infrastructure.haversine import HaversineDistanceCalculator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, update, select, or_, func
from uuid import UUID
from datetime import datetime, timezone
from collections.abc import Mapping


_calculator = HaversineDistanceCalculator()

class SQLAlchemyHubRepository(HubRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, hub: Hub) -> Hub:
        stmt = insert(hubs).values(self._to_row(hub))
        await self._session.execute(stmt)
        return hub

    async def get_by_id(self, hub_id: UUID) -> Hub | None:
        stmt = select(hubs).where(hubs.c.id == hub_id)
        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()
        if not row:
            return None
        return self._to_model(row)

    async def list(self, query: HubQuery) -> tuple[list[Hub], int]:
        offset = (query.page - 1) * query.page_size
        conditions = []
        if not query.include_deleted:
            conditions.append(hubs.c.deleted_at.is_(None))
        if query.statuses:
            conditions.append(hubs.c.status.in_([s.value for s in query.statuses]))
        if query.types:
            conditions.append(hubs.c.type.in_([t.value for t in query.types]))
        if query.search:
            subjects = [s.strip() for s in query.search.split(",") if s.strip()]
            conditions.append(or_(*(
                or_(hubs.c.name.ilike(f"%{s}%"), hubs.c.address_text.ilike(f"%{s}%"))
                for s in subjects
            )))
        count_col = func.count().over().label("total")
        stmt = select(hubs, count_col).where(*conditions).offset(offset).limit(query.page_size)
        result = await self._session.execute(stmt)
        rows = result.mappings().all()
        items = [self._to_model(row) for row in rows]
        total = rows[0]["total"] if rows else 0
        return items, total

    async def update(self, hub: Hub) -> Hub:
        stmt = update(hubs).where(hubs.c.id == hub.id).values(self._to_row(hub))
        await self._session.execute(stmt)
        return hub

    async def delete(self, hub_id: UUID) -> None:
        stmt = update(hubs).where(hubs.c.id == hub_id).values(deleted_at=datetime.now(timezone.utc))
        await self._session.execute(stmt)

    async def find_nearest(self, location: Location, limit: int = 1) -> list[Hub]:
        cached_rows = get_hub_cache()
        if cached_rows is None:
            stmt = select(hubs).where(
                hubs.c.status == HubStatus.ACTIVE.value,
                hubs.c.deleted_at.is_(None)
            )
            result = await self._session.execute(stmt)
            rows = result.mappings().all()
            cached_rows = [dict(row) for row in rows]
            set_hub_cache(cached_rows)

        hub_list = [self._to_model(row) for row in cached_rows]
        if not hub_list:
            return []
        all_locations = [location] + [h.address.location for h in hub_list]
        matrix = _calculator.compute_matrix(all_locations)
        distances = matrix[0][1:]
        ranked = sorted(enumerate(distances), key=lambda x: x[1])
        return [hub_list[i] for i, _ in ranked[:limit]]
    
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
    def _to_model(row: Mapping) -> Hub:
        return Hub(
            id=row["id"],
            name=row["name"],
            type=HubType(row["type"]),
            address=Address(
                text=row["address_text"],
                location=Location(lat=float(row["lat"]), lng=float(row["lng"])),
            ),
            status=HubStatus(row["status"]),
            deleted_at=row["deleted_at"] if row.get("deleted_at") else None,
        )

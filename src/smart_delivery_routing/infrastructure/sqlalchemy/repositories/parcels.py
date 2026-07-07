from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, update, select, or_, and_
from collections.abc import Mapping
from uuid import UUID

from smart_delivery_routing.domain.shared import Load
from smart_delivery_routing.infrastructure.sqlalchemy.tables import parcels, hubs
from smart_delivery_routing.domain.linehaul import Parcel, ParcelQuery, ParcelRepository, ParcelStatus


origin_hub = hubs.alias("origin_hub")
destination_hub = hubs.alias("destination_hub")
current_hub = hubs.alias("current_hub")


class SQLAlchemyParcelRepository(ParcelRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, parcel: Parcel) -> Parcel:
        stmt = insert(parcels).values(
            id=parcel.id,
            created_at=parcel.created_at,
            updated_at=parcel.updated_at,
            **self._to_row(parcel),
        )
        await self._session.execute(stmt)
        return parcel
    
    async def get_by_id(self, parcel_id: UUID) -> Parcel | None:
        stmt = (
            select(
                parcels,
                origin_hub.c.name.label("origin_hub_name"),
                destination_hub.c.name.label("destination_hub_name"),
                current_hub.c.name.label("current_hub_name"),
            )
            .join(origin_hub, parcels.c.origin_hub_id == origin_hub.c.id)
            .join(destination_hub, parcels.c.destination_hub_id == destination_hub.c.id)
            .outerjoin(current_hub, parcels.c.current_hub_id == current_hub.c.id)
            .where(parcels.c.id == parcel_id)
        )
        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()
        if not row:
            return None
        return self._to_model(row)
    
    async def list(self, query: ParcelQuery) -> list[Parcel]:
        conditions = []
        if query.statuses:
            conditions.append(parcels.c.status.in_([s.value for s in query.statuses]))
        if query.cursor_created_at is not None:
            conditions.append(
                or_(
                    parcels.c.created_at < query.cursor_created_at,
                    and_(
                        parcels.c.created_at == query.cursor_created_at,
                        parcels.c.id < query.cursor_id,
                    )
                )
            )
        stmt = (
            select(
                parcels,
                origin_hub.c.name.label("origin_hub_name"),
                destination_hub.c.name.label("destination_hub_name"),
                current_hub.c.name.label("current_hub_name"),
            )
            .join(origin_hub, parcels.c.origin_hub_id == origin_hub.c.id)
            .join(destination_hub, parcels.c.destination_hub_id == destination_hub.c.id)
            .outerjoin(current_hub, parcels.c.current_hub_id == current_hub.c.id)
            .where(*conditions)
            .order_by(parcels.c.created_at.desc(), parcels.c.id.desc())
            .limit(query.page_size + 1)
        )
        result = await self._session.execute(stmt)
        rows = result.mappings().all()
        return [self._to_model(row) for row in rows]

    async def update(self, parcel: Parcel) -> Parcel:
        stmt = update(parcels).where(parcels.c.id == parcel.id).values(self._to_row(parcel))
        await self._session.execute(stmt)
        return parcel

    @staticmethod
    def _to_row(parcel: Parcel) -> dict:
        return {
            "shipping_request_id": str(parcel.shipping_request_id),
            "tracking_number": parcel.tracking_number,
            "origin_hub_id": str(parcel.origin_hub_id),
            "destination_hub_id": str(parcel.destination_hub_id),
            "current_hub_id": str(parcel.current_hub_id) if parcel.current_hub_id else None,
            "weight": parcel.load.weight,
            "volume": parcel.load.volume,
            "status": parcel.status.value,
        }

    @staticmethod
    def _to_model(row: Mapping) -> Parcel:
        return Parcel(
            id=row["id"],
            shipping_request_id=row["shipping_request_id"],
            tracking_number=row["tracking_number"],
            origin_hub_id=row["origin_hub_id"],
            destination_hub_id=row["destination_hub_id"],
            current_hub_id=row["current_hub_id"] if row["current_hub_id"] else None,
            load=Load(weight=float(row["weight"]), volume=float(row["volume"])),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            status=ParcelStatus(row["status"]),
            origin_hub_name=row["origin_hub_name"],
            destination_hub_name=row["destination_hub_name"],
            current_hub_name=row["current_hub_name"] or "",
        )
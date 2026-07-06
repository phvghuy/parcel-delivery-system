from dataclasses import dataclass
from uuid import UUID

from smart_delivery_routing.domain.linehaul import Hub, HubQuery, HubRepository, validate_hub
from smart_delivery_routing.domain.shared import ValidationError


@dataclass(frozen=True)
class PagedHubs:
    items: list[Hub]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.size))


# --- Domain exceptions ---

@dataclass(frozen=True)
class ValidationFailed(Exception):
    errors: list[ValidationError]

    def __str__(self) -> str:
        return "; ".join(f"{e.field}: {e.reason}" for e in self.errors)


@dataclass(frozen=True)
class HubNotFound(Exception):
    hub_id: UUID

    def __str__(self) -> str:
        return f"Hub '{self.hub_id}' not found."


# --- Use cases ---

async def list_hubs(query: HubQuery, repo: HubRepository) -> PagedHubs:
    items, total = await repo.list(query)
    return PagedHubs(items=items, total=total, page=query.page, size=query.page_size)


async def get_hub(hub_id: UUID, repo: HubRepository) -> Hub:
    hub = await repo.get_by_id(hub_id)
    if hub is None:
        raise HubNotFound(hub_id=hub_id)
    return hub


async def create_hub(hub: Hub, repo: HubRepository) -> Hub:
    errors = validate_hub(hub)
    if errors:
        raise ValidationFailed(errors=errors)
    return await repo.create(hub)


async def update_hub(hub_id: UUID, updated: Hub, repo: HubRepository) -> Hub:
    errors = validate_hub(updated)
    if errors:
        raise ValidationFailed(errors=errors)
    if await repo.get_by_id(hub_id) is None:
        raise HubNotFound(hub_id=hub_id)
    return await repo.update(updated)


async def delete_hub(hub_id: UUID, repo: HubRepository) -> None:
    if await repo.get_by_id(hub_id) is None:
        raise HubNotFound(hub_id=hub_id)
    await repo.delete(hub_id)
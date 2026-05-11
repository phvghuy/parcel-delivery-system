from collections.abc import Callable
from pathlib import Path

import folium

from smart_delivery_routing.domain.models import Order, RoutingResult, Warehouse

_COLORS = [
    "blue", "red", "green", "purple", "orange",
    "darkred", "darkblue", "darkgreen", "cadetblue", "pink",
]

GeometryFn = Callable[[list[tuple[float, float]]], list[list[float]]]


def build_map(
    result: RoutingResult,
    orders: list[Order],
    warehouses: list[Warehouse],
    vehicle_origins: dict[str, str],
    vehicle_destinations: dict[str, str],
    geometry_fn: GeometryFn | None = None,
) -> folium.Map:
    order_by_id = {o.order_id: o for o in orders}
    warehouse_by_id = {w.warehouse_id: w for w in warehouses}

    center = warehouses[0].location if warehouses else None
    fmap = folium.Map(
        location=[center.lat, center.lng] if center else [10.8, 106.7],
        zoom_start=12,
    )

    for wh in warehouses:
        _add_warehouse_marker(fmap, wh)

    for idx, route in enumerate(result.routes):
        if not route.stops:
            continue

        color = _COLORS[idx % len(_COLORS)]
        group = folium.FeatureGroup(name=f"{route.vehicle_id} ({len(route.stops)} stops)", show=True)

        origin_wh = warehouse_by_id.get(vehicle_origins.get(route.vehicle_id, ""))
        dest_wh = warehouse_by_id.get(vehicle_destinations.get(route.vehicle_id, ""))

        stop_coords = [[s.location.lat, s.location.lng] for s in route.stops]

        # Origin warehouse → first stop (nét đứt dài = xuất phát)
        if origin_wh:
            o = origin_wh.location
            folium.PolyLine(
                locations=_road([[o.lat, o.lng], stop_coords[0]], geometry_fn),
                color=color, weight=2.5, opacity=0.75, dash_array="12 6",
                tooltip=f"{route.vehicle_id}: depart from {origin_wh.name or origin_wh.warehouse_id}",
            ).add_to(group)

        # stop → stop
        if len(stop_coords) > 1:
            folium.PolyLine(
                locations=_road(stop_coords, geometry_fn),
                color=color, weight=2.5, opacity=0.8,
                tooltip=f"{route.vehicle_id} — {route.total_distance:.1f} km",
            ).add_to(group)

        # Last stop → destination warehouse (nét chấm ngắn = về kho)
        if dest_wh:
            d = dest_wh.location
            folium.PolyLine(
                locations=_road([stop_coords[-1], [d.lat, d.lng]], geometry_fn),
                color=color, weight=2, opacity=0.5, dash_array="3 8",
                tooltip=f"{route.vehicle_id}: return to {dest_wh.name or dest_wh.warehouse_id}",
            ).add_to(group)

        for idx, stop in enumerate(route.stops):
            _add_stop_marker(group, idx + 1, order_by_id[stop.order_id], color)

        group.add_to(fmap)

    _add_unassigned_markers(fmap, result.unassigned_orders, order_by_id)
    folium.LayerControl(collapsed=False).add_to(fmap)

    return fmap


def _road(coords: list[list[float]], geometry_fn: GeometryFn | None) -> list[list[float]]:
    if geometry_fn is None:
        return coords
    return geometry_fn([(c[0], c[1]) for c in coords])


def save_map(fmap: folium.Map, path: str | Path) -> None:
    fmap.save(str(path))


def _add_warehouse_marker(fmap: folium.Map, warehouse: Warehouse) -> None:
    folium.Marker(
        location=[warehouse.location.lat, warehouse.location.lng],
        popup=f"<b>{warehouse.name or warehouse.warehouse_id}</b>",
        tooltip=warehouse.name or warehouse.warehouse_id,
        icon=folium.Icon(color="black", icon="home", prefix="fa"),
    ).add_to(fmap)


def _add_stop_marker(group: folium.FeatureGroup, idx: int, order: Order, color: str) -> None:
    popup_html = (
        f"<b>{order.order_id}</b><br>"
        f"Weight: {order.weight} kg<br>"
        f"Volume: {order.volume} m³<br>"
        f"Delivery Order: {idx}"
    )
    folium.CircleMarker(
        location=[order.location.lat, order.location.lng],
        radius=6,
        color=color,
        fill=True,
        fill_opacity=0.8,
        popup=folium.Popup(popup_html, max_width=200),
        tooltip=order.order_id,
    ).add_to(group)


def _add_unassigned_markers(
    fmap: folium.Map,
    unassigned_ids: list[str],
    order_by_id: dict[str, Order],
) -> None:
    if not unassigned_ids:
        return
    group = folium.FeatureGroup(name=f"Unassigned ({len(unassigned_ids)})", show=True)
    for order_id in unassigned_ids:
        order = order_by_id[order_id]
        folium.CircleMarker(
            location=[order.location.lat, order.location.lng],
            radius=5,
            color="gray",
            fill=True,
            fill_opacity=0.5,
            popup=folium.Popup(
                f"<b>{order_id}</b><br>Weight: {order.weight} kg<br>Volume: {order.volume} m³",
                max_width=200,
            ),
            tooltip=f"{order_id} (unassigned)",
        ).add_to(group)
    group.add_to(fmap)
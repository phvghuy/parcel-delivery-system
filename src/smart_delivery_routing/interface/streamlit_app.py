import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from smart_delivery_routing.application.data_loader import (
    LoadError,
    load_orders_from_bytes,
    load_vehicles_from_bytes,
    load_warehouses_from_bytes,
)
from smart_delivery_routing.application.kpi import KPIReport
from smart_delivery_routing.application.solvers.nearest_neighbor import NearestNeighborSolver
from smart_delivery_routing.application.use_cases import (
    OptimizeRoutesInput,
    OptimizeRoutesOutput,
    ValidationFailed,
    optimize_routes,
)
from smart_delivery_routing.infrastructure.distance import HaversineDistanceCalculator
from smart_delivery_routing.infrastructure.osrm import get_road_geometry
from smart_delivery_routing.infrastructure.repositories.supabase_orders import SupabaseOrderRepository
from smart_delivery_routing.infrastructure.repositories.supabase_vehicles import SupabaseVehicleRepository
from smart_delivery_routing.infrastructure.repositories.supabase_warehouses import SupabaseWarehouseRepository
from smart_delivery_routing.infrastructure.supabase_client import get_supabase_client
from smart_delivery_routing.interface.visualizer import build_map

st.set_page_config(page_title="Smart Delivery Routing", page_icon="🚚", layout="wide")

_solver = NearestNeighborSolver()
_distance_calculator = HaversineDistanceCalculator()


def _get_repos():
    client = get_supabase_client()
    return (
        SupabaseOrderRepository(client),
        SupabaseVehicleRepository(client),
        SupabaseWarehouseRepository(client),
    )


def main() -> None:
    st.title("Smart Delivery Routing")

    with st.sidebar:
        _render_sidebar()

    days: list[dict] = st.session_state.get("days", [])

    if not days:
        st.info("Import data and click **Optimize** to start.")
        return

    if st.button("Continue Optimize", type="primary"):
        _optimize()

    for entry in reversed(days):
        expanded = entry["day"] == len(days)
        with st.expander(f"Day {entry['day']} — {entry['assigned']} orders assigned", expanded=expanded):
            _render_result(entry)


def _render_sidebar() -> None:
    st.header("1. Import Data")

    orders_file = st.file_uploader("Orders CSV", type="csv", key="orders_upload")
    vehicles_file = st.file_uploader("Vehicles CSV", type="csv", key="vehicles_upload")
    warehouses_file = st.file_uploader("Warehouses CSV", type="csv", key="warehouses_upload")

    import_ready = orders_file and vehicles_file and warehouses_file
    if st.button("Import", disabled=not import_ready):
        _import(orders_file, vehicles_file, warehouses_file)

    st.divider()

    st.header("2. Optimize")
    imported = st.session_state.get("imported", False)
    days = st.session_state.get("days", [])

    if not days and st.button("Optimize", type="primary", disabled=not imported):
        _optimize()


def _import(orders_file, vehicles_file, warehouses_file) -> None:
    order_repo, vehicle_repo, warehouse_repo = _get_repos()
    try:
        orders = load_orders_from_bytes(orders_file.read(), source=orders_file.name)
        vehicles = load_vehicles_from_bytes(vehicles_file.read(), source=vehicles_file.name)
        warehouses = load_warehouses_from_bytes(warehouses_file.read(), source=warehouses_file.name)
    except LoadError as e:
        st.error(str(e))
        return

    order_repo.save_orders(orders)
    vehicle_repo.save_vehicles(vehicles)
    warehouse_repo.save_warehouses(warehouses)

    st.session_state["imported"] = True
    st.session_state["days"] = []
    st.success(f"Imported {len(orders)} orders · {len(vehicles)} vehicles · {len(warehouses)} warehouses")


def _optimize() -> None:
    order_repo, vehicle_repo, warehouse_repo = _get_repos()

    orders = order_repo.get_pending_orders()
    vehicles = vehicle_repo.get_vehicles()
    warehouses = warehouse_repo.get_warehouses()

    if not orders:
        st.sidebar.warning("No pending orders left.")
        return

    vehicle_origins = {v.vehicle_id: v.current_warehouse_id for v in vehicles}

    input_data = OptimizeRoutesInput(orders=orders, vehicles=vehicles, warehouses=warehouses)

    with st.spinner("Optimizing..."):
        try:
            output = optimize_routes(
                input_data, _solver, _distance_calculator,
                order_repo=order_repo,
                vehicle_repo=vehicle_repo,
            )
        except ValidationFailed as e:
            for err in e.errors:
                st.sidebar.error(f"[{err.entity_id}] {err.field}: {err.reason}")
            return

    vehicle_destinations = {v.vehicle_id: v.current_warehouse_id for v in vehicles}

    days: list[dict] = st.session_state.get("days", [])
    days.append({
        "day": len(days) + 1,
        "output": output,
        "orders": orders,
        "warehouses": warehouses,
        "vehicle_origins": vehicle_origins,
        "vehicle_destinations": vehicle_destinations,
        "assigned": len([s for r in output.result.routes for s in r.stops]),
    })
    st.session_state["days"] = days


# --- Result rendering ---

def _render_result(entry: dict) -> None:
    output: OptimizeRoutesOutput = entry["output"]
    _render_kpi_metrics(output.kpi)
    st.divider()
    _render_map_section(output, entry)
    st.divider()
    _render_vehicle_table(output.kpi)
    if output.result.unassigned_orders:
        _render_unassigned(output.result.unassigned_orders)


def _render_kpi_metrics(kpi: KPIReport) -> None:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Distance", f"{kpi.total_distance_km:.1f} km")
    c2.metric("Vehicles Used", kpi.vehicles_used)
    c3.metric("Unassigned", kpi.unassigned_count)
    c4.metric("Avg Fill (Weight)", f"{kpi.average_fill_rate_weight:.1%}")
    c5.metric("Avg Fill (Volume)", f"{kpi.average_fill_rate_volume:.1%}")


def _render_map_section(output: OptimizeRoutesOutput, entry: dict) -> None:
    st.subheader("Route Map")
    fmap = build_map(
        output.result,
        entry["orders"],
        entry["warehouses"],
        entry["vehicle_origins"],
        entry["vehicle_destinations"],
        geometry_fn=get_road_geometry,
    )
    st_folium(fmap, use_container_width=True, height=800, returned_objects=[])


def _render_vehicle_table(kpi: KPIReport) -> None:
    st.subheader("Per Vehicle")
    rows = [
        {
            "Vehicle": v.vehicle_id,
            "Stops": v.stops_count,
            "Distance (km)": round(v.distance_km, 2),
            "Fill Weight": f"{v.fill_rate_weight:.1%}",
            "Fill Volume": f"{v.fill_rate_volume:.1%}",
        }
        for v in kpi.per_vehicle
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_unassigned(unassigned: list[str]) -> None:
    with st.expander(f"Unassigned Orders ({len(unassigned)})"):
        st.dataframe(pd.DataFrame({"order_id": unassigned}), hide_index=True)


if __name__ == "__main__":
    main()
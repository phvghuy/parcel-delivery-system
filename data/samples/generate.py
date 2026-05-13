"""Generate sample warehouses, orders, and vehicles CSV for TP.HCM area.

Fleet is fixed per warehouse (realistic SME constraint), independent of order count.
A vehicle does multiple trips per day — more orders just means more unassigned orders
if total capacity is insufficient.

Usage:
    python generate.py                        # default: 150 orders, fixed fleet
    python generate.py --orders 1000          # 1000 orders, same fixed fleet
    python generate.py --orders 5000 --seed 123 --out ./large
"""

import argparse
import random
import pandas as pd
from pathlib import Path

# TP.HCM bounding box
LAT_MIN, LAT_MAX = 10.65, 10.90
LNG_MIN, LNG_MAX = 106.60, 106.90

WAREHOUSES = [
    ("WH-001", "Kho Bình Dương",  10.9800, 106.6500),
    ("WH-002", "Kho Thủ Đức",     10.8500, 106.7700),
    ("WH-003", "Kho Bình Chánh",  10.6800, 106.6100),
]

# Fixed fleet per warehouse: (vehicle_id_suffix, max_weight_kg, max_volume_m3)
# Reflects a mid-size delivery company in HCMC: ~5 vehicles per hub
FLEET: dict[str, list[tuple[str, int, float]]] = {
    "WH-001": [
        ("001", 800,  2.0),
        ("002", 800,  2.0),
        ("003", 1200, 3.5),
        ("004", 1200, 3.5),
        ("005", 2000, 5.0),
    ],
    "WH-002": [
        ("006", 500,  1.5),
        ("007", 800,  2.0),
        ("008", 1200, 3.5),
        ("009", 2000, 5.0),
        ("010", 2000, 5.0),
    ],
    "WH-003": [
        ("011", 500,  1.5),
        ("012", 500,  1.5),
        ("013", 800,  2.0),
        ("014", 1200, 3.5),
        ("015", 2000, 5.0),
    ],
}


def generate_warehouses() -> pd.DataFrame:
    return pd.DataFrame([
        {"warehouse_id": wid, "name": name, "lat": lat, "lng": lng}
        for wid, name, lat, lng in WAREHOUSES
    ])


def generate_orders(n: int) -> pd.DataFrame:
    warehouse_ids = [wid for wid, *_ in WAREHOUSES]
    width = max(4, len(str(n)))
    rows = [
        {
            "order_id":     f"ORD-{i:0{width}d}",
            "warehouse_id": random.choice(warehouse_ids),
            "lat":          round(random.uniform(LAT_MIN, LAT_MAX), 6),
            "lng":          round(random.uniform(LNG_MIN, LNG_MAX), 6),
            "weight":       round(random.uniform(5.0, 150.0), 2),
            "volume":       round(random.uniform(0.01, 0.80), 3),
        }
        for i in range(1, n + 1)
    ]
    return pd.DataFrame(rows)


def generate_vehicles() -> pd.DataFrame:
    rows = [
        {
            "vehicle_id":   f"VEH-{suffix}",
            "warehouse_id": wh_id,
            "max_weight":   max_weight,
            "max_volume":   max_volume,
        }
        for wh_id, vehicles in FLEET.items()
        for suffix, max_weight, max_volume in vehicles
    ]
    return pd.DataFrame(rows)


def _print_capacity_summary(orders_df: pd.DataFrame, vehicles_df: pd.DataFrame) -> None:
    total_order_weight = orders_df["weight"].sum()
    total_order_volume = orders_df["volume"].sum()
    total_vehicle_weight = vehicles_df["max_weight"].sum()
    total_vehicle_volume = vehicles_df["max_volume"].sum()
    print(f"\nCapacity check:")
    print(f"  Orders  : {total_order_weight:,.0f} kg / {total_order_volume:.1f} m³")
    print(f"  Fleet   : {total_vehicle_weight:,.0f} kg / {total_vehicle_volume:.1f} m³")
    print(f"  Ratio   : {total_order_weight / total_vehicle_weight:.1f}x weight, {total_order_volume / total_vehicle_volume:.1f}x volume")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate delivery routing sample data")
    parser.add_argument("--orders", type=int, default=150, help="Number of orders (default: 150)")
    parser.add_argument("--seed",   type=int, default=42,  help="Random seed (default: 42)")
    parser.add_argument("--out",    type=str, default=None, help="Output directory (default: same as script)")
    args = parser.parse_args()

    random.seed(args.seed)
    output_dir = Path(args.out) if args.out else Path(__file__).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    warehouses_df = generate_warehouses()
    orders_df     = generate_orders(args.orders)
    vehicles_df   = generate_vehicles()

    warehouses_df.to_csv(output_dir / "warehouses.csv", index=False)
    orders_df.to_csv(output_dir / "orders.csv", index=False)
    vehicles_df.to_csv(output_dir / "vehicles.csv", index=False)

    print(f"Generated {len(warehouses_df)} warehouses → {output_dir / 'warehouses.csv'}")
    print(f"Generated {len(orders_df)} orders      → {output_dir / 'orders.csv'}")
    print(f"Generated {len(vehicles_df)} vehicles    → {output_dir / 'vehicles.csv'}")

    print("\nOrders per warehouse:")
    print(orders_df.groupby("warehouse_id").size().to_string())

    print("\nVehicles per warehouse:")
    print(vehicles_df.groupby("warehouse_id")[["max_weight", "max_volume"]].sum().to_string())

    print(f"\nOrders weight: {orders_df['weight'].min():.1f} – {orders_df['weight'].max():.1f} kg")
    print(f"Orders volume: {orders_df['volume'].min():.3f} – {orders_df['volume'].max():.3f} m³")

    _print_capacity_summary(orders_df, vehicles_df)
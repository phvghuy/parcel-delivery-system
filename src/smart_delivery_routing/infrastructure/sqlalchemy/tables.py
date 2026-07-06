from sqlalchemy import MetaData, Table, Column, Integer, Float, String, DateTime
from sqlalchemy.dialects.postgresql import UUID


metadata = MetaData()


trucks = Table("trucks", metadata,
    Column("id", UUID, primary_key=True),
    Column("plate_number", String, nullable=False),
    Column("max_weight", Float, nullable=False),
    Column("max_volume", Float, nullable=False),
    Column("status", Integer, nullable=False),
    Column("deleted_at", DateTime(timezone=True), nullable=True),
)

hubs = Table("hubs", metadata,
    Column("id", UUID, primary_key=True),
    Column("name", String, nullable=False),
    Column("type", Integer, nullable=False),
    Column("address_text", String, nullable=False),
    Column("lat", Float, nullable=False),
    Column("lng", Float, nullable=False),
    Column("status", Integer, nullable=False),
    Column("deleted_at", DateTime(timezone=True), nullable=True)
)

shipping_requests = Table("shipping_requests", metadata,
    Column("id", UUID, primary_key=True),
    Column("external_order_id", String, nullable=False),
    Column("seller_id", UUID, nullable=False),
    Column("pickup_address_text", String, nullable=False),
    Column("pickup_lat", Float, nullable=False),
    Column("pickup_lng", Float, nullable=False),
    Column("delivery_address_text", String, nullable=False),
    Column("delivery_lat", Float, nullable=False),
    Column("delivery_lng", Float, nullable=False),
    Column("receiver_name", String, nullable=False),
    Column("receiver_phone", String, nullable=False),
    Column("weight", Float, nullable=False),
    Column("volume", Float, nullable=False),
    Column("service_type", Integer, nullable=False),
    Column("status", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("cod_amount", Float, nullable=True),
    Column("cod_currency", String, nullable=True)
)

parcels = Table("parcels", metadata,
    Column("id", UUID, primary_key=True),
    Column("shipping_request_id", UUID, nullable=False),
    Column("tracking_number", String, nullable=False),
    Column("origin_hub_id", UUID, nullable=False),
    Column("destination_hub_id", UUID, nullable=False),
    Column("current_hub_id", UUID, nullable=True),
    Column("weight", Float, nullable=False),
    Column("volume", Float, nullable=False),
    Column("status", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False)                
)

truck_trips = Table("truck_trips", metadata,
    Column("id", UUID, primary_key=True),
    Column("truck_id", UUID, nullable=False),
    Column("origin_hub_id", UUID, nullable=False),
    Column("destination_hub_id", UUID, nullable=False),
    Column("status", Integer, nullable=False),
    Column("planned_departure_time", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("actual_departure_time", DateTime(timezone=True), nullable=True),
    Column("actual_arrival_time", DateTime(timezone=True), nullable=True),
    Column("deleted_at", DateTime(timezone=True), nullable=True)                    
)

truck_trip_items = Table("truck_trip_items", metadata,
    Column("id", UUID, primary_key=True),
    Column("truck_trip_id", UUID, nullable=False),
    Column("parcel_id", UUID, nullable=False),
    Column("loaded_at", DateTime(timezone=True), nullable=False),
    Column("unloaded_at", DateTime(timezone=True), nullable=True)
)

tracking_events = Table("tracking_events", metadata,
    Column("id", UUID, primary_key=True),
    Column("parcel_id", UUID, nullable=False),
    Column("status", Integer, nullable=False),
    Column("location_kind", Integer, nullable=False),
    Column("location_name", String, nullable=False),
    Column("location_id", UUID, nullable=True),
    Column("note", String, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False)
)

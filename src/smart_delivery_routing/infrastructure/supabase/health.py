from smart_delivery_routing.infrastructure.supabase.client import get_supabase_service_client


def health_check_supabase() -> bool:
    client = get_supabase_service_client()
    try:
        client.table("hubs").select("*").limit(1).execute()
        return True
    except Exception:
        return False
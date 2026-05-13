from supabase import Client, create_client

from smart_delivery_routing.config import SUPABASE_KEY, SUPABASE_URL


def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

from smart_delivery_routing.infrastructure.supabase.client import get_supabase_client
from smart_delivery_routing.config import SUPABASE_JWT_SECRET, SUPABASE_URL
from jwt import PyJWKClient
import jwt


jwks_client = PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")

def sign_in(email: str, password: str) -> dict:
    return get_supabase_client().auth.sign_in_with_password({
        "email": email,
        "password": password
    })


def sign_out(access_token: str) -> None:
    get_supabase_client().auth.sign_out()


def get_user_role(access_token: str) -> str | None:
    signing_key = jwks_client.get_signing_key_from_jwt(access_token)
    payload = jwt.decode(access_token, signing_key.key, algorithms=["ES256"], audience="authenticated")
    return payload.get("app_metadata", {}).get("role")


def get_user_id(access_token: str) -> str:
    user = get_supabase_client().auth.get_user(access_token)
    return str(user.user.id)
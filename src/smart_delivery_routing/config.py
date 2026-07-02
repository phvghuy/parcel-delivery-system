import os

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
OSRM_URL = os.environ.get("OSRM_URL", "http://localhost:5000")
FIREBASE_CREDENTIALS = os.environ.get("FIREBASE_CREDENTIALS", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

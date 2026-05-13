import os

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
OSRM_URL = os.environ.get("OSRM_URL", "http://localhost:5000")

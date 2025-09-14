import os, pathlib
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

def env(name: str, default: str | None = None, required: bool = False) -> str | None:
    val = os.environ.get(name, default)
    if required and not val:
        raise RuntimeError(f"Missing required env var: {name}")
    return val

def mask(s: str | None) -> str | None:
    if not s: return None
    return f"{s[:6]}…{s[-6:]} (len {len(s)})"

# Strava creds
STRAVA_CLIENT_ID     = env("STRAVA_CLIENT_ID", required=True)
STRAVA_CLIENT_SECRET = env("STRAVA_CLIENT_SECRET", required=True)
STRAVA_ACCESS_TOKEN  = env("STRAVA_ACCESS_TOKEN")   # can be empty before first OAuth
STRAVA_REFRESH_TOKEN = env("STRAVA_REFRESH_TOKEN")
STRAVA_EXPIRES_AT    = int(env("STRAVA_EXPIRES_AT", str(0)) or "0")

# Poke inbound (optional, to push a message)
POKE_API_KEY    = env("POKE_API_KEY")
POKE_INBOUND_URL= env("POKE_INBOUND_URL", "https://poke.com/api/v1/inbound-sms/webhook")

HOST = env("HOST", "0.0.0.0")
PORT = int(env("PORT", "8000"))

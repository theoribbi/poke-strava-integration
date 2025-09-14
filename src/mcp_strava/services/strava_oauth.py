import time
import urllib.parse
import requests
from mcp_strava.settings import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REDIRECT_URI

CLIENT_ID     = STRAVA_CLIENT_ID
CLIENT_SECRET = STRAVA_CLIENT_SECRET
REDIRECT_URI  = STRAVA_REDIRECT_URI
SCOPES        = "read,activity:read_all"

def _post_form(url: str, data: dict, timeout: int = 10) -> dict:
    r = requests.post(url, data=data, timeout=timeout)
    r.raise_for_status()
    return r.json()

def authorize_url(state: str = "ok") -> str:
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": SCOPES,
        "state": state,
    }
    return "https://www.strava.com/oauth/authorize?" + urllib.parse.urlencode(params)

def exchange_code(code: str) -> dict:
    data = _post_form(
        "https://www.strava.com/oauth/token",
        {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        },
    )
    data["created_at"] = int(time.time())
    return data

def refresh_token(refresh_token_value: str) -> dict:
    data = _post_form(
        "https://www.strava.com/oauth/token",
        {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token_value,
        },
    )
    data["created_at"] = int(time.time())
    return data

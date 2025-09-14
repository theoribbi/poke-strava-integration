import time, requests
from typing import Any, Dict, List
from mcp_strava.settings import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_ACCESS_TOKEN, STRAVA_REFRESH_TOKEN, STRAVA_EXPIRES_AT

# Initialize tokens from env vars as fallback, but prefer JSON file
_tokens = {
    "access_token": STRAVA_ACCESS_TOKEN,
    "refresh_token": STRAVA_REFRESH_TOKEN,
    "expires_at": STRAVA_EXPIRES_AT or int(time.time()) + 60,  # safe default
}

def _load_tokens_from_file():
    """Load tokens from JSON file if available, otherwise use env vars"""
    try:
        from mcp_strava.services.token_store import load_tokens
        file_tokens = load_tokens()
        if file_tokens:
            print(f"[STRAVA_CLIENT] Loading tokens from file")
            # Only update if file has valid tokens
            if file_tokens.get("access_token"):
                _tokens["access_token"] = file_tokens["access_token"]
            if file_tokens.get("refresh_token"):
                _tokens["refresh_token"] = file_tokens["refresh_token"]
            if file_tokens.get("expires_at"):
                _tokens["expires_at"] = file_tokens["expires_at"]
        else:
            print(f"[STRAVA_CLIENT] No tokens file found")
            # If env vars are empty/None, set them to empty string to be clear
            if not _tokens["access_token"]:
                print(f"[STRAVA_CLIENT] No access token in env vars either")
    except Exception as e:
        print(f"[STRAVA_CLIENT] Error loading tokens from file: {e}")

# Load tokens from file on import
_load_tokens_from_file()

class StravaAuthError(RuntimeError): pass

def reload_tokens():
    """Reload tokens from file - useful after OAuth callback"""
    _load_tokens_from_file()

def _refresh() -> None:
    if not _tokens["refresh_token"]:
        raise StravaAuthError("Missing STRAVA_REFRESH_TOKEN for refresh")
    
    print(f"[STRAVA_CLIENT] Refreshing tokens...")
    r = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": _tokens["refresh_token"]
    }, timeout=30)
    if r.status_code >= 400:
        raise StravaAuthError(f"Refresh failed {r.status_code} {r.text}")
    
    d = r.json()
    _tokens.update({
        "access_token": d["access_token"],
        "refresh_token": d.get("refresh_token", _tokens["refresh_token"]),
        "expires_at": d.get("expires_at", int(time.time()) + 6*3600),
    })
    
    # Save refreshed tokens to file
    try:
        from mcp_strava.services.token_store import save_tokens
        save_tokens({
            "access_token": _tokens["access_token"],
            "refresh_token": _tokens["refresh_token"],
            "expires_at": _tokens["expires_at"],
            "token_type": "Bearer",
            "scope": d.get("scope", "read,activity:read_all")
        })
        print(f"[STRAVA_CLIENT] Tokens refreshed and saved to file")
    except Exception as e:
        print(f"[STRAVA_CLIENT] Warning: Could not save refreshed tokens: {e}")

def _auth_header() -> Dict[str, str]:
    # If no access token, try to reload from file first
    if not _tokens["access_token"]:
        print("[STRAVA_CLIENT] No access token, trying to reload from file...")
        _load_tokens_from_file()
    
    # Still no token? Error
    if not _tokens["access_token"]:
        raise StravaAuthError("Missing STRAVA_ACCESS_TOKEN - please authenticate first")
    
    # Check if token is expired
    if _tokens["expires_at"] - int(time.time()) < 60:
        _refresh()
    
    return {"Authorization": f"Bearer {_tokens['access_token']}"}

def get_athlete() -> Dict[str, Any]:
    r = requests.get("https://www.strava.com/api/v3/athlete", headers=_auth_header(), timeout=30)
    if r.status_code == 401:
        _refresh(); r = requests.get("https://www.strava.com/api/v3/athlete", headers=_auth_header(), timeout=30)
    r.raise_for_status()
    return r.json()

def get_recent_activities(per_page: int = 5) -> List[Dict[str, Any]]:
    r = requests.get("https://www.strava.com/api/v3/athlete/activities",
                     headers=_auth_header(),
                     params={"per_page": max(1, min(per_page, 100))},
                     timeout=30)
    if r.status_code == 401:
        _refresh(); r = requests.get("https://www.strava.com/api/v3/athlete/activities",
                                     headers=_auth_header(),
                                     params={"per_page": per_page}, timeout=30)
    r.raise_for_status()
    return r.json()

def get_activities_list(limit: int = 30, after: int = None, before: int = None) -> List[Dict[str, Any]]:
    """
    Get activities with optional date filtering
    
    Args:
        limit: Number of activities to return (max 200)
        after: Unix timestamp - return activities after this date
        before: Unix timestamp - return activities before this date
    """
    params = {"per_page": max(1, min(limit, 200))}
    
    if after is not None:
        params["after"] = after
    if before is not None:
        params["before"] = before
    
    r = requests.get("https://www.strava.com/api/v3/athlete/activities",
                     headers=_auth_header(),
                     params=params,
                     timeout=30)
    if r.status_code == 401:
        _refresh()
        r = requests.get("https://www.strava.com/api/v3/athlete/activities",
                         headers=_auth_header(),
                         params=params, 
                         timeout=30)
    r.raise_for_status()
    return r.json()

def get_activity(activity_id: int) -> Dict[str, Any]:
    r = requests.get(f"https://www.strava.com/api/v3/activities/{activity_id}",
                     headers=_auth_header(),
                     params={"include_all_efforts": "false"},
                     timeout=30)
    if r.status_code == 401:
        _refresh(); r = requests.get(f"https://www.strava.com/api/v3/activities/{activity_id}",
                                     headers=_auth_header(),
                                     params={"include_all_efforts": "false"},
                                     timeout=30)
    r.raise_for_status()
    return r.json()

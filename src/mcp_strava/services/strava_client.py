import time, requests
from typing import Any, Dict, List
from mcp_strava.settings import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_ACCESS_TOKEN, STRAVA_REFRESH_TOKEN, STRAVA_EXPIRES_AT

_tokens = {
    "access_token": STRAVA_ACCESS_TOKEN,
    "refresh_token": STRAVA_REFRESH_TOKEN,
    "expires_at": STRAVA_EXPIRES_AT or int(time.time()) + 60,  # safe default
}

class StravaAuthError(RuntimeError): pass

def _refresh() -> None:
    if not _tokens["refresh_token"]:
        raise StravaAuthError("Missing STRAVA_REFRESH_TOKEN for refresh")
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

def _auth_header() -> Dict[str, str]:
    if not _tokens["access_token"]:
        raise StravaAuthError("Missing STRAVA_ACCESS_TOKEN")
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

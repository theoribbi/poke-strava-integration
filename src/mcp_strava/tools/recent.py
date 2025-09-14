from typing import List, Dict, Any
from mcp_strava.services.strava_client import get_recent_activities
from mcp_strava.services.metrics import normalize

def recent_activities(limit: int = 5) -> List[Dict[str, Any]]:
    raw = get_recent_activities(per_page=limit)
    return [normalize(a) for a in raw]

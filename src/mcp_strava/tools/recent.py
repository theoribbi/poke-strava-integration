from typing import List, Dict, Any
from mcp_strava.services.strava_client import get_recent_activities
from mcp_strava.services.metrics import normalize

def recent_activities(limit: int = 5) -> Dict[str, Any]:
    raw = get_recent_activities(per_page=limit)
    activities = [normalize(a) for a in raw]
    return {
        "activities": activities,
        "count": len(activities),
        "poke_prompt": "user asked for recent activities. respond in casual poke style - brief and friendly. mention the activities naturally, maybe highlight something interesting. keep it conversational."
    }

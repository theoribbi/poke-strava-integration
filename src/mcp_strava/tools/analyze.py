from mcp_strava.services.strava_client import get_activity
from mcp_strava.services.metrics import normalize

def analyze_activity(activity_id: int) -> dict:
    """
    Fetch one Strava activity, normalize metrics, and build a short human message.
    Returns machine-friendly fields + 'content' for direct display in Poke.
    """
    a = get_activity(activity_id)
    act = normalize(a)

    parts = [f"{act.get('name','Activity')} • {act.get('sport','Workout')}"]
    dk = act.get("distance_km"); mt = act.get("moving_time_min")
    if dk is not None: parts.append(f"{dk} km")
    if mt is not None: parts.append(f"{mt} min")
    if act.get("pace_min_per_km") is not None:
        parts.append(f"{act['pace_min_per_km']}/km")
    if act.get("avg_speed_kmh") is not None:
        parts.append(f"{act['avg_speed_kmh']} km/h")
    if act.get("pace_per_100m") is not None:
        parts.append(f"{act['pace_per_100m']}/100m")
    if act.get("avg_hr") is not None:
        parts.append(f"{round(act['avg_hr'],1)} bpm")

    content = " • ".join(parts)

    def mmss_to_min(p):
        if isinstance(p, str) and ":" in p:
            m, s = p.split(":")
            return int(m) + int(s)/60
        return None

    payload = {
        "activity_id": act["id"],
        "activity": {
            "id": act["id"],
            "name": act.get("name"),
            "sport": act.get("sport"),
            "start_date_utc": a.get("start_date"),  # raw ISO from Strava
            "distance_km": act.get("distance_km"),
            "moving_time_min": act.get("moving_time_min"),
            "elev_gain_m": act.get("elev_gain_m"),
            "avg_hr": act.get("avg_hr"),
            "pace_min_per_km": mmss_to_min(act.get("pace_min_per_km")),
            "avg_speed_kmh": act.get("avg_speed_kmh"),
            "pace_per_100m_min": mmss_to_min(act.get("pace_per_100m")),
        },
        "content": content,
        "poke_prompt": "user just uploaded a new activity to strava. respond in casual poke style - brief and encouraging about their workout. be supportive but not overly formal. highlight something interesting about the performance."
    }
    return payload

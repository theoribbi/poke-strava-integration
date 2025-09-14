from datetime import timedelta, datetime, timezone
from mcp_strava.services.strava_client import get_recent_activities
from mcp_strava.services.metrics import normalize, summarize

def _parse_iso_utc(s: str | None):
    if not s:
        return None
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
        dt = datetime.fromisoformat(s)
        return (dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc))
    except Exception:
        return None

def _utc_week_window(reference: datetime | None = None):
    """Semaine courante en UTC: lundi 00:00:00Z → dimanche 23:59:59Z."""
    now_utc = (reference or datetime.utcnow()).replace(tzinfo=timezone.utc)
    d0 = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    start = d0 - timedelta(days=d0.weekday())
    end   = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return start, end

def _by_sport(acts):
    out = {}
    for a in acts:
        k = (a.get("sport") or "Other")
        x = out.setdefault(k, {"count": 0, "distance_km": 0.0, "moving_time_min": 0.0, "elev_gain_m": 0.0})
        x["count"] += 1
        x["distance_km"] += float(a.get("distance_km") or 0.0)
        x["moving_time_min"] += float(a.get("moving_time_min") or 0.0)
        x["elev_gain_m"] += float(a.get("elev_gain_m") or 0.0)
    for v in out.values():
        v["distance_km"] = round(v["distance_km"], 2)
        v["moving_time_min"] = round(v["moving_time_min"], 1)
        v["elev_gain_m"] = round(v["elev_gain_m"], 1)
    return out

def weekly_summary(include_content: bool = False):
    """
    Machine-friendly summary of the current UTC calendar week (Monday→Sunday).
    """
    week_start, week_end = _utc_week_window()

    raw = get_recent_activities(per_page=200)
    acts = []
    for a in raw:
        n = normalize(a)
        n["_dt"] = _parse_iso_utc(n.get("start_date"))
        acts.append(n)

    def in_week(a):
        dt = a.get("_dt")
        return dt is not None and (week_start <= dt <= week_end)

    week_acts = [a for a in acts if in_week(a)]
    stats = summarize(week_acts)

    payload = {
        "window": {
            "start_utc": week_start.isoformat().replace("+00:00", "Z"),
            "end_utc":   week_end.isoformat().replace("+00:00", "Z"),
        },
        "summary": stats,  # {count, distance_km, moving_time_min, elev_gain_m, avg_pace_min_per_km, avg_hr}
        "breakdown_by_sport": _by_sport(week_acts),
        "activities": [
            {
                "id": a["id"],
                "name": a.get("name"),
                "sport": a.get("sport"),
                "start_date_utc": a.get("start_date"),
                "distance_km": a.get("distance_km"),
                "moving_time_min": a.get("moving_time_min"),
                "elev_gain_m": a.get("elev_gain_m"),
                "avg_hr": a.get("avg_hr"),
                "pace_min_per_km": (
                    (lambda p: (int(p.split(':')[0]) + int(p.split(':')[1])/60)
                     if isinstance(p, str) and ':' in p else None)(a.get("pace_min_per_km"))
                ),
                "avg_speed_kmh": a.get("avg_speed_kmh"),
                "pace_per_100m_min": (
                    (lambda p: (int(p.split(':')[0]) + int(p.split(':')[1])/60)
                     if isinstance(p, str) and ':' in p else None)(a.get("pace_per_100m"))
                ),
            } for a in week_acts
        ],
    }

    if include_content:
        s = stats
        def fmt(x,u=""): return "—" if x is None else f"{x}{u}"
        payload["content"] = (
            f"Week {payload['window']['start_utc']} → {payload['window']['end_utc']}\n"
            f"- Activities: {s['count']}\n"
            f"- Distance: {fmt(s['distance_km'],' km')}\n"
            f"- Time: {fmt(s['moving_time_min'],' min')}\n"
            f"- Elev gain: {fmt(s['elev_gain_m'],' m')}\n"
            f"- Avg pace: {fmt(s['avg_pace_min_per_km'],' min/km')}\n"
            f"- Avg HR: {fmt(s['avg_hr'])}"
        )

    return payload

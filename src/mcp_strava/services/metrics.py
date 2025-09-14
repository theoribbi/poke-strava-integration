from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone

RUN_LIKE = {"Run", "TrailRun", "VirtualRun"}
RIDE_LIKE = {"Ride", "MountainBikeRide", "GravelRide", "VirtualRide", "EBikeRide"}
SWIM_LIKE = {"Swim"}
ROW_LIKE  = {"Rowing", "Canoeing", "Kayaking"}
GYM_LIKE  = {"WeightTraining", "Elliptical", "StairStepper", "Workout", "HIIT"}

def sec_to_mmss(sec: float) -> str:
    m = int(sec // 60); s = int(round(sec - m*60))
    return f"{m}:{s:02d}"

def normalize(a: Dict[str, Any]) -> Dict[str, Any]:
    sport = (a.get("sport_type") or a.get("type") or "Workout")
    dist_m = float(a.get("distance") or 0.0)
    mt_s   = float(a.get("moving_time") or 0.0)
    elev_m = float(a.get("total_elevation_gain") or 0.0)
    hr     = a.get("average_heartrate")
    out: Dict[str, Any] = {
        "id": a["id"], "name": a.get("name"), "sport": sport,
        "start_date": a.get("start_date"),
        "distance_km": round(dist_m/1000.0, 2),
        "moving_time_min": round(mt_s/60.0, 1),
        "elev_gain_m": round(elev_m, 1),
        "avg_hr": hr
    }
    if sport in RUN_LIKE and dist_m > 0 and mt_s > 0:
        pace = sec_to_mmss(mt_s / (dist_m/1000.0)); out["pace_min_per_km"] = pace
        out["summary"] = f"{out['distance_km']} km • {out['moving_time_min']} min • {pace}/km"
    elif sport in RIDE_LIKE and dist_m > 0 and mt_s > 0:
        speed = (dist_m/1000.0) / (mt_s/3600.0); out["avg_speed_kmh"] = round(speed, 1)
        out["summary"] = f"{out['distance_km']} km • {out['moving_time_min']} min • {out['avg_speed_kmh']} km/h"
    elif sport in SWIM_LIKE and dist_m > 0 and mt_s > 0:
        pace100 = sec_to_mmss(mt_s / (dist_m/100.0)); out["pace_per_100m"] = pace100
        out["summary"] = f"{int(dist_m)} m • {out['moving_time_min']} min • {pace100}/100m"
    elif sport in ROW_LIKE and dist_m > 0 and mt_s > 0:
        speed = (dist_m/1000.0) / (mt_s/3600.0); out["avg_speed_kmh"] = round(speed, 1)
        out["summary"] = f"{out['distance_km']} km • {out['moving_time_min']} min • {out['avg_speed_kmh']} km/h"
    else:
        out["summary"] = f"{out['moving_time_min']} min" + (f" • {round(hr,1)} bpm" if hr else "")
    return out

def summarize(acts: List[Dict[str, Any]]) -> Dict[str, Any]:
    km = sum(a["distance_km"] for a in acts)
    mins = sum(a["moving_time_min"] for a in acts)
    elev = sum(a.get("elev_gain_m", 0) for a in acts)
    runs = [a for a in acts if (a["sport"] or "").lower().startswith("run")]
    paces = []
    for a in runs:
        p = a.get("pace_min_per_km")
        if p:
            m,s = map(int, p.split(":")); paces.append(m + s/60)
    avg_pace = round(sum(paces)/len(paces), 2) if paces else None
    hrs = [a["avg_hr"] for a in acts if a.get("avg_hr") is not None]
    avg_hr = round(sum(hrs)/len(hrs), 1) if hrs else None
    return {
        "count": len(acts),
        "distance_km": round(km, 2),
        "moving_time_min": round(mins, 1),
        "elev_gain_m": round(elev, 1),
        "avg_pace_min_per_km": avg_pace,
        "avg_hr": avg_hr
    }

def week_window(today_utc: datetime | None = None):
    d = (today_utc or datetime.utcnow()).date()
    start = datetime(d.year, d.month, d.day)
    start = start - timedelta(days=start.weekday())
    end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return start.replace(tzinfo=timezone.utc), end.replace(tzinfo=timezone.utc)

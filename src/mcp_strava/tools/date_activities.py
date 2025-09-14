"""Get Strava activities by date or date range"""
from datetime import datetime, timezone
from typing import List, Dict, Optional
from mcp_strava.services.strava_client import get_activities_list
from mcp_strava.services.metrics import normalize

def parse_date(date_str: str) -> datetime:
    """Parse date string in various formats to datetime"""
    formats = [
        "%Y-%m-%d",          # 2024-07-25
        "%d/%m/%Y",          # 25/07/2024
        "%d-%m-%Y",          # 25-07-2024
        "%Y-%m-%d %H:%M",    # 2024-07-25 14:30
        "%d/%m/%Y %H:%M",    # 25/07/2024 14:30
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date: {date_str}. Supported formats: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY")

def get_activities_by_date(
    date: Optional[str] = None,
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    limit: int = 30
) -> Dict:
    """
    Get Strava activities for a specific date or date range.
    
    Args:
        date: Single date (YYYY-MM-DD, DD/MM/YYYY, or DD-MM-YYYY)
        start_date: Start of date range (same formats)
        end_date: End of date range (same formats)  
        limit: Maximum number of activities to return
        
    Returns:
        Dict with activities and metadata
    """
    
    if date and (start_date or end_date):
        raise ValueError("Use either 'date' for single date or 'start_date'/'end_date' for range, not both")
    
    if not date and not start_date:
        raise ValueError("Must specify either 'date' or 'start_date'")
    
    # Handle single date
    if date:
        parsed_date = parse_date(date)
        # Get activities for the entire day
        after_timestamp = int(parsed_date.timestamp())
        before_timestamp = int((parsed_date.replace(hour=23, minute=59, second=59)).timestamp())
        date_desc = f"on {parsed_date.strftime('%Y-%m-%d')}"
    
    # Handle date range
    else:
        start_dt = parse_date(start_date)
        if end_date:
            end_dt = parse_date(end_date)
            if end_dt < start_dt:
                raise ValueError("end_date must be after start_date")
        else:
            # If no end_date, use same day as start_date
            end_dt = start_dt.replace(hour=23, minute=59, second=59)
        
        after_timestamp = int(start_dt.timestamp())
        before_timestamp = int(end_dt.replace(hour=23, minute=59, second=59).timestamp())
        
        if start_date == end_date or not end_date:
            date_desc = f"on {start_dt.strftime('%Y-%m-%d')}"
        else:
            date_desc = f"from {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}"
    
    # Get activities from Strava API
    raw_activities = get_activities_list(
        limit=limit,
        after=after_timestamp,
        before=before_timestamp
    )
    
    # Normalize activities
    activities = []
    for raw_activity in raw_activities:
        try:
            normalized = normalize(raw_activity)
            activities.append(normalized)
        except Exception as e:
            print(f"[DATE_ACTIVITIES] Error normalizing activity {raw_activity.get('id', 'unknown')}: {e}")
            continue
    
    # Create summary
    if not activities:
        content = f"No activities found {date_desc}"
    else:
        total_distance = sum(a.get("distance_km", 0) for a in activities if a.get("distance_km"))
        total_time = sum(a.get("moving_time_min", 0) for a in activities if a.get("moving_time_min"))
        sports = list(set(a.get("sport", "Unknown") for a in activities))
        
        summary_parts = [
            f"{len(activities)} activities {date_desc}",
            f"{total_distance:.1f} km total" if total_distance > 0 else None,
            f"{total_time:.0f} min total" if total_time > 0 else None,
            f"Sports: {', '.join(sports)}" if len(sports) <= 3 else f"Sports: {', '.join(sports[:3])} +{len(sports)-3} more"
        ]
        content = " • ".join(filter(None, summary_parts))
    
    return {
        "date_filter": date_desc,
        "count": len(activities),
        "activities": activities,
        "summary": {
            "total_distance_km": round(sum(a.get("distance_km", 0) for a in activities if a.get("distance_km")), 2),
            "total_time_min": round(sum(a.get("moving_time_min", 0) for a in activities if a.get("moving_time_min")), 1),
            "sports": list(set(a.get("sport", "Unknown") for a in activities)),
        },
        "content": content
    }

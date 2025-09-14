from fastmcp import FastMCP
from mcp_strava.tools.recent import recent_activities
from mcp_strava.tools.weekly import weekly_summary
from mcp_strava.tools.analyze import analyze_activity
from mcp_strava.tools.date_activities import get_activities_by_date

mcp = FastMCP("Strava MCP")

@mcp.tool(description="Fetch recent Strava activities, normalized across sports")
def get_recent_activities(limit: int = 5):
    return recent_activities(limit=limit)

@mcp.tool(description="Weekly summary for the current UTC calendar week (Monday→Sunday)")
def get_weekly_summary(include_content: bool = False):
    from mcp_strava.tools.weekly import weekly_summary as _weekly
    return _weekly(include_content=include_content)

@mcp.tool(description="Analyze a specific Strava activity by ID with detailed metrics")
def analyze_activity_by_id(activity_id: int):
    """Get detailed analysis of a Strava activity by its ID"""
    return analyze_activity(activity_id=activity_id)

@mcp.tool(description="Get Strava activities for a specific date or date range")
def get_activities_by_date_range(
    date: str = None,
    start_date: str = None, 
    end_date: str = None,
    limit: int = 30
):
    """
    Get activities for a specific date or date range.
    
    Examples:
    - Single date: date="2024-07-25" or date="25/07/2024"
    - Date range: start_date="2024-07-25", end_date="2024-07-30"
    - From date onwards: start_date="2024-07-25" (will get activities for that day only)
    
    Supported date formats: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY
    """
    return get_activities_by_date(
        date=date,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )

# Optional: a MCP text resource to display directly in Poke
@mcp.resource("weekly://summary")
def weekly_resource() -> str:
    w = weekly_summary()
    return w["content"]

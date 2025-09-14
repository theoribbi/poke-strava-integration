from fastmcp import FastMCP
from mcp_strava.tools.recent import recent_activities
from mcp_strava.tools.weekly import weekly_summary
from mcp_strava.tools.analyze import analyze_activity
from mcp_strava.tools.date_activities import get_activities_by_date
from mcp_strava.services.token_store import load_tokens
from mcp_strava.services.strava_client import get_athlete
from mcp_strava.services.webhook_manager import create_webhook_subscription_async, list_webhook_subscriptions, delete_webhook_subscription
from mcp_strava.settings import PUBLIC_URL

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

@mcp.tool(description="Start Strava authentication process - get authorization URL")
def start_strava_auth():
    """
    Generate your app's authorization URL to connect Strava account.
    
    Returns the URL to your server that will handle the Strava OAuth flow.
    After authorization, you'll be redirected back to complete the setup.
    """
    try:
        # Use YOUR server's auth start endpoint
        auth_url = f"{PUBLIC_URL}/auth/strava/start"
        
        return {
            "status": "auth_required",
            "authorization_url": auth_url,
            "instructions": [
                "1. Click or visit the authorization URL above",
                "2. You'll be redirected to Strava to log in",
                "3. Click 'Authorize' to give permission to the app",
                "4. You'll be redirected back to see confirmation",
                "5. Then you can use all Strava tools!"
            ],
            "content": f"🚀 To connect your Strava account, visit: {auth_url}\n\nThis will take you through the Strava authorization process. After authorization, you'll be able to use all Strava tools to analyze your activities!"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "content": f"❌ Error generating authorization URL: {e}"
        }

@mcp.tool(description="Check Strava connection status and user info")
def check_strava_connection():
    """
    Check if Strava is properly connected and show user information.
    
    Returns connection status and athlete info if connected.
    """
    try:
        # Check if we have tokens
        tokens = load_tokens()
        if not tokens:
            return {
                "status": "not_connected",
                "content": "❌ Not connected to Strava. Use 'start_strava_auth' to connect your account.",
                "next_action": "Use the start_strava_auth tool to get your authorization URL"
            }
        
        # Try to fetch athlete info to verify connection works
        try:
            athlete = get_athlete()
            return {
                "status": "connected",
                "athlete": {
                    "id": athlete.get("id"),
                    "name": f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip(),
                    "username": athlete.get("username"),
                    "city": athlete.get("city"),
                    "state": athlete.get("state"),
                    "country": athlete.get("country"),
                    "profile_medium": athlete.get("profile_medium"),
                    "follower_count": athlete.get("follower_count"),
                    "friend_count": athlete.get("friend_count")
                },
                "content": f"✅ Connected to Strava as {athlete.get('firstname', '')} {athlete.get('lastname', '')} (@{athlete.get('username', 'N/A')})\nLocation: {athlete.get('city', 'N/A')}, {athlete.get('state', 'N/A')}\nFollowers: {athlete.get('follower_count', 0)} | Following: {athlete.get('friend_count', 0)}"
            }
        except Exception as api_error:
            return {
                "status": "token_expired", 
                "error": str(api_error),
                "content": "⚠️ Connected but tokens may be expired. Use 'start_strava_auth' to reconnect.",
                "next_action": "Re-authenticate using start_strava_auth tool"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "content": f"❌ Error checking Strava connection: {e}"
        }

@mcp.tool(description="Create Strava webhook subscription for automatic activity notifications")
async def setup_strava_webhook(callback_url: str | None = None):
    return await create_webhook_subscription_async(callback_override=callback_url)


@mcp.tool(description="List all active Strava webhook subscriptions")
def list_strava_webhooks():
    """
    List all active webhook subscriptions to see what's currently configured.
    """
    return list_webhook_subscriptions()

@mcp.tool(description="Delete a Strava webhook subscription")
def delete_strava_webhook(subscription_id: int):
    """
    Delete a webhook subscription by ID.
    
    Use list_strava_webhooks first to see available subscriptions and their IDs.
    """
    return delete_webhook_subscription(subscription_id)

@mcp.tool(description="Enable automatic Strava notifications after user confirmation")
def enable_strava_notifications():
    """
    Enable automatic workout notifications after user has confirmed they want them.
    
    This will:
    1. Set up the webhook subscription
    2. Send a welcome message with available features to Poke
    """
    from mcp_strava.services.poke import send_poke
    
    # Set up webhook
    webhook_result = create_webhook_subscription()
    
    if webhook_result.get("status") in ["success", "already_exists"]:
        # Send features overview to Poke
        features_message = "Automatic Strava notifications enabled successfully. Available features: weekly summary, search workouts by date/range, recent activities list, analyze specific workouts by ID. User can request weekly stats, activities from specific dates, recent workout analysis, or upload new activity to test automatic analysis."

        send_result = send_poke(features_message)
        
        return {
            "status": "success",
            "webhook_result": webhook_result,
            "poke_result": send_result,
            "content": "✅ Notifications enabled and user informed about features!"
        }
    else:
        return {
            "status": "error",
            "webhook_result": webhook_result,
            "content": f"❌ Failed to enable notifications: {webhook_result.get('error', 'Unknown error')}"
        }

@mcp.tool(description="Skip automatic notifications and send feature overview")
def skip_notifications_send_features():
    """
    User declined automatic notifications, but send them the available features anyway.
    """
    from mcp_strava.services.poke import send_poke
    
    features_message = "User declined automatic Strava notifications but manual features still available. Features: weekly summary, search workouts by date/range, recent activities list, analyze specific workouts by ID. User can request weekly stats, activities from specific dates, or recent workout analysis. Can enable automatic notifications later if desired."

    send_result = send_poke(features_message)
    
    return {
        "status": "success",
        "poke_result": send_result,
        "content": "✅ User informed about available features without notifications!"
    }

# Optional: a MCP text resource to display directly in Poke
@mcp.resource("weekly://summary")
def weekly_resource() -> str:
    w = weekly_summary()
    return w["content"]

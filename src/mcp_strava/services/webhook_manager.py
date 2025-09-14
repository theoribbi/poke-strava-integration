"""Strava webhook subscription management"""
import requests
from typing import Dict, List
from mcp_strava.settings import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_VERIFY_TOKEN, PUBLIC_URL

from typing import Optional

def create_webhook_subscription(callback_override: Optional[str] = None) -> Dict:
    callback_url = callback_override or f"{PUBLIC_URL}/strava/webhook"
    callback_url = callback_url.rstrip("/")

    try:
        probe = requests.get(
            f"{callback_url}?hub.mode=subscribe&hub.verify_token={STRAVA_VERIFY_TOKEN}&hub.challenge=__probe__",
            timeout=10,
        )
        # Must be JSON with {"hub.challenge":"__probe__"} and 200
        if probe.status_code != 200 or "hub.challenge" not in (probe.json() or {}):
            print("[WEBHOOK] Self-check failed:", probe.status_code, probe.text[:200])
            return {
                "status": "error",
                "content": "❌ Callback self-check failed. Verify your PUBLIC_URL and handler.",
                "details": {"status": probe.status_code, "body": probe.text[:200]},
            }
    except Exception as e:
        return {"status": "error", "content": f"❌ Callback unreachable: {e}"}

    data = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "callback_url": callback_url,
        "verify_token": STRAVA_VERIFY_TOKEN,
    }

    print(f"[WEBHOOK] Creating subscription with callback: {callback_url}")
    resp = requests.post("https://www.strava.com/api/v3/push_subscriptions", data=data, timeout=30)
    print(f"[WEBHOOK] Create response: {resp.status_code} - {resp.text}")

    if resp.status_code == 201:
        return {"status": "success", "subscription": resp.json(), "content": f"✅ Subscription OK → {callback_url}"}
    if resp.status_code == 409:
        return {"status": "already_exists", "content": "⚠️ Subscription already exists."}
    return {"status": "error", "error": resp.text, "content": f"❌ {resp.status_code} - {resp.text}"}


def list_webhook_subscriptions() -> Dict:
    """List all Strava webhook subscriptions"""
    params = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET
    }
    
    try:
        response = requests.get(
            "https://www.strava.com/api/v3/push_subscriptions",
            params=params,
            timeout=30
        )
        
        print(f"[WEBHOOK] List response: {response.status_code} - {response.text}")
        
        if response.status_code == 200:
            subscriptions = response.json()
            
            if not subscriptions:
                return {
                    "status": "none",
                    "subscriptions": [],
                    "content": "📭 No webhook subscriptions found. Use 'create_webhook_subscription' to set one up."
                }
            
            content_lines = ["📡 Active webhook subscriptions:"]
            for sub in subscriptions:
                content_lines.append(f"• ID: {sub.get('id')}")
                content_lines.append(f"  Callback: {sub.get('callback_url')}")
                content_lines.append(f"  Created: {sub.get('created_at')}")
                content_lines.append("")
            
            return {
                "status": "success",
                "subscriptions": subscriptions,
                "content": "\n".join(content_lines)
            }
        else:
            return {
                "status": "error",
                "error": response.text,
                "content": f"❌ Failed to list webhook subscriptions: {response.status_code} - {response.text}"
            }
            
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e),
            "content": f"❌ Error listing webhook subscriptions: {e}"
        }

def delete_webhook_subscription(subscription_id: int) -> Dict:
    """Delete a Strava webhook subscription"""
    params = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET
    }
    
    try:
        response = requests.delete(
            f"https://www.strava.com/api/v3/push_subscriptions/{subscription_id}",
            params=params,
            timeout=30
        )
        
        print(f"[WEBHOOK] Delete response: {response.status_code} - {response.text}")
        
        if response.status_code == 204:
            return {
                "status": "success",
                "content": f"✅ Webhook subscription {subscription_id} deleted successfully."
            }
        else:
            return {
                "status": "error",
                "error": response.text,
                "content": f"❌ Failed to delete webhook subscription: {response.status_code} - {response.text}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "content": f"❌ Error deleting webhook subscription: {e}"
        }

"""Strava webhook subscription management"""
import requests
import httpx
from typing import Dict, List
from mcp_strava.settings import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_VERIFY_TOKEN, PUBLIC_URL

from typing import Optional

async def create_webhook_subscription_async(callback_override: Optional[str] = None) -> Dict:
    callback_url = (callback_override or f"{PUBLIC_URL}/strava/webhook").rstrip("/")
    probe_challenge = "__probe__"

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            # lightweight self-check: must return the raw challenge
            probe = await client.get(
                f"{callback_url}?hub.mode=subscribe&hub.verify_token={STRAVA_VERIFY_TOKEN}&hub.challenge={probe_challenge}"
            )
            if probe.status_code != 200 or probe.text.strip() != probe_challenge:
                return {
                    "status": "error",
                    "content": "❌ Callback self-check failed. Ensure PUBLIC_URL is correct and verify handler returns plain text.",
                    "details": {"status": probe.status_code, "body": probe.text[:200]},
                }

            data = {
                "client_id": STRAVA_CLIENT_ID,
                "client_secret": STRAVA_CLIENT_SECRET,
                "callback_url": callback_url,
                "verify_token": STRAVA_VERIFY_TOKEN,
            }

            # This await keeps the loop free so your GET /strava/webhook can be answered
            resp = await client.post("https://www.strava.com/api/v3/push_subscriptions", data=data)
            print(f"[WEBHOOK] Create response: {resp.status_code} - {resp.text[:200]}")

            if resp.status_code == 201:
                return {"status": "success", "subscription": resp.json(), "content": f"✅ Subscription OK → {callback_url}"}
            if resp.status_code == 409:
                return {"status": "already_exists", "content": "⚠️ Subscription already exists."}
            return {"status": "error", "error": resp.text, "content": f"❌ {resp.status_code} - {resp.text}"}

    except Exception as e:
        return {"status": "error", "error": str(e), "content": f"❌ Error creating subscription: {e}"}



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

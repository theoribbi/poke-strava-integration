"""Poke notification service"""
import requests
from typing import Dict
from mcp_strava.settings import POKE_API_KEY, POKE_INBOUND_URL  

def send_poke(message: str) -> Dict:
    """Send a message via Poke API"""
    if not POKE_API_KEY:
        print("[POKE] skipped: missing POKE_API_KEY")
        return {"ok": False, "error": "missing_api_key"}
    
    try:
        r = requests.post(
            POKE_INBOUND_URL,
            headers={"Authorization": f"Bearer {POKE_API_KEY}", "Content-Type": "application/json"},
            json={"message": message},
            timeout=10,
        )
        print("[POKE] status:", r.status_code, "body:", r.text[:200])
        return {"ok": r.ok, "status": r.status_code, "body": r.text}
    except Exception as e:
        print("[POKE] exception:", repr(e))
        return {"ok": False, "error": repr(e)}

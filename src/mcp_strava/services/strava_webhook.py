"""Strava webhook handlers"""
import os
import time
from typing import Dict
from fastapi import Request
from fastapi.responses import JSONResponse

from mcp_strava.tools.analyze import analyze_activity
from mcp_strava.services.poke import send_poke

STRAVA_VERIFY_TOKEN = os.getenv("STRAVA_VERIFY_TOKEN", "dev-verify")

# Deduplication cache
_seen: Dict[str, float] = {}

def _dedupe(key: str, ttl: int = 60) -> bool:
    """Deduplicate webhook events based on key and TTL"""
    now = time.time()
    # Clean expired entries
    for k, t0 in list(_seen.items()):
        if now - t0 > ttl:
            _seen.pop(k, None)
    
    if key in _seen:
        return False
    
    _seen[key] = now
    return True

async def verify_webhook(request: Request):
    """Handle Strava webhook verification"""
    q = request.query_params
    mode = q.get("hub.mode")
    token = q.get("hub.verify_token")
    challenge = q.get("hub.challenge")
    
    print("[WEBHOOK] verify:", dict(q))
    
    if mode == "subscribe" and token == STRAVA_VERIFY_TOKEN and challenge:
        return JSONResponse({"hub.challenge": challenge}, status_code=200)
    
    return JSONResponse({"error": "verification failed"}, status_code=403)

async def handle_webhook_event(request: Request):
    """Handle Strava webhook events"""
    try:
        evt = await request.json()
    except Exception:
        evt = {}
    
    print("[WEBHOOK] raw event:", evt)

    if evt.get("object_type") == "activity" and evt.get("aspect_type") in {"create", "update"}:
        try:
            act_id = int(evt.get("object_id"))
        except Exception as e:
            print("[WEBHOOK] bad object_id:", evt.get("object_id"), e)
            act_id = None

        if act_id is not None and _dedupe(f"{evt.get('aspect_type')}:{act_id}"):
            print(f"[WEBHOOK] analyzing activity {act_id}")
            try:
                res = analyze_activity(activity_id=act_id) 
                print("[WEBHOOK] analyze content:", res.get("content"))
            except Exception as e:
                print("[WEBHOOK] analyze error:", repr(e))
                res = {}

            if res.get("content"):
                send_poke(res["content"])
            else:
                print("[POKE] skipped: no content")

    return JSONResponse({"ok": True}, status_code=200)

#!/usr/bin/env python3
import os
import time
import requests
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

# ========= Env =========
load_dotenv()
POKE_API_KEY        = os.getenv("POKE_API_KEY")
POKE_INBOUND_URL    = os.getenv("POKE_INBOUND_URL", "https://poke.com/api/v1/inbound-sms/webhook")
STRAVA_VERIFY_TOKEN = os.getenv("STRAVA_VERIFY_TOKEN", "dev-verify")

# ========= MCP Setup =========
from mcp_strava.app import mcp as mcp_server
from mcp_strava.tools.analyze import analyze_activity

mcp_app = mcp_server.http_app(path='/mcp')
print("[MCP] Mounted MCP server at /mcp")

# Create FastAPI app with MCP lifespan
app = FastAPI(
    title="Strava MCP + Webhook Server",
    description="FastAPI server with mounted MCP server and Strava webhooks",
    version="1.0.0",
    lifespan=mcp_app.lifespan
)

# ========= Health =========
@app.get("/healthz")
async def healthz():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"ok": True, "routes": ["/mcp", "/strava/webhook", "/healthz"]}

# ========= Poke helper =========
def _send_poke(message: str) -> Dict:
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

# ========= Webhook Strava =========
_seen: Dict[str, float] = {}

def _dedupe(key: str, ttl: int = 60) -> bool:
    now = time.time()
    for k, t0 in list(_seen.items()):
        if now - t0 > ttl:
            _seen.pop(k, None)
    if key in _seen:
        return False
    _seen[key] = now
    return True

@app.get("/strava/webhook")
async def verify(request: Request):
    q = request.query_params
    mode = q.get("hub.mode")
    token = q.get("hub.verify_token")
    challenge = q.get("hub.challenge")
    print("[WEBHOOK] verify:", dict(q))
    if mode == "subscribe" and token == STRAVA_VERIFY_TOKEN and challenge:
        return JSONResponse({"hub.challenge": challenge}, status_code=200)
    return JSONResponse({"error": "verification failed"}, status_code=403)

@app.post("/strava/webhook")
async def events(request: Request):
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
                _send_poke(res["content"])
            else:
                print("[POKE] skipped: no content")

    return JSONResponse({"ok": True}, status_code=200)

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    def _mask(v): return v[:4] + f"…(len {len(v)})" if v else None
    print(f"[BOOT] on {host}:{port} | MCP:/ (root)  Webhook:/strava/webhook  Health:/healthz")
    print("[ENV] POKE_API_KEY:", _mask(POKE_API_KEY))
    print("[ENV] STRAVA_VERIFY_TOKEN:", STRAVA_VERIFY_TOKEN)
    
    # Run the MCP server directly with HTTP transport
    if hasattr(mcp_server, "run_http"):
        mcp_server.run_http(host=host, port=port)
    else:
        # Fallback to uvicorn
        uvicorn.run(app, host=host, port=port)

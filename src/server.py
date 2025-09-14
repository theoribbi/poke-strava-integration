#!/usr/bin/env python3
import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from mcp_strava.settings import HOST, PORT, POKE_API_KEY, STRAVA_VERIFY_TOKEN

# ========= MCP Server Setup =========
from mcp_strava.app import mcp as mcp_server
from mcp_strava.services.strava_webhook import verify_webhook, handle_webhook_event
from mcp_strava.services.strava_oauth import authorize_url, exchange_code, refresh_token
from mcp_strava.services.token_store import  save_tokens
from mcp_strava.services.webhook_manager import create_webhook_subscription
from mcp_strava.services.strava_client import reload_tokens


print("[MCP] Adding custom routes to FastMCP server")


# ========= Health & Info Routes =========
@mcp_server.custom_route("/healthz", methods=["GET"])
async def healthz(request):
    return JSONResponse({"status": "healthy"})

@mcp_server.custom_route("/", methods=["GET"])
async def root(request):
    print(f"[ROOT] Request from {request.client.host if request.client else 'unknown'}")
    return JSONResponse({"ok": True, "routes": ["/ (MCP endpoints)", "/strava/webhook", "/healthz"]})

# ========= Strava Webhook Routes =========
@mcp_server.custom_route("/strava/webhook", methods=["GET"])
async def verify_strava_webhook(request):
    return await verify_webhook(request)

@mcp_server.custom_route("/strava/webhook", methods=["POST"])
async def handle_strava_webhook(request):
    print(f"[WEBHOOK] POST request received from {request.client.host if request.client else 'unknown'}")
    print(f"[WEBHOOK] Headers: {dict(request.headers)}")
    return await handle_webhook_event(request)

# ========= OAuth Strava (via MCP custom routes) =========
@mcp_server.custom_route("/auth/strava/start", methods=["GET"])
async def auth_start(request):
    return RedirectResponse(authorize_url(state="ok"))

@mcp_server.custom_route("/auth/strava/callback", methods=["GET"])
async def auth_callback(request):
    code = request.query_params.get("code")
    if not code:
        return HTMLResponse("<h1>Missing ?code</h1>", status_code=400)
    
    try:
        print(f"[AUTH] Exchanging code: {code[:10]}...")
        data = exchange_code(code)
        print(f"[AUTH] Got data keys: {list(data.keys())}")
        
        print(f"[AUTH] Saving tokens...")
        save_tokens(data)
        print(f"[AUTH] Tokens saved successfully")
        
        # Reload tokens in the Strava client
        reload_tokens()
        print(f"[AUTH] Tokens reloaded in Strava client")

        a = (data.get("athlete") or {})
        athlete_name = f"{a.get('firstname', '')} {a.get('lastname', '')}".strip()
        
        # Check if webhook is already configured
        from mcp_strava.services.webhook_manager import list_webhook_subscriptions
        from mcp_strava.services.poke import send_poke
        
        webhook_status = list_webhook_subscriptions()
        has_webhook = webhook_status.get("status") == "success" and len(webhook_status.get("subscriptions", [])) > 0
        
        if not has_webhook:
            poke_message = f"user just connected to strava. ask if they want automatic workout analysis notifications when uploading activities. and after the user response, send the feature overview weekly summary, search workouts by date/range, recent activities list, analyze specific workouts but tell it in casual poke style"
            
            send_result = send_poke(poke_message)
            print(f"[AUTH] Sent notification setup message to Poke: {send_result}")
            
            webhook_result = create_webhook_subscription()
            print(f"[AUTH] Webhook creation result: {webhook_result}")
            
            body = f"""
            <h1>Connected ✅</h1>
            <p>Athlete: <b>{athlete_name}</b> (ID {a.get('id')})</p>
            <p>📱 We've sent a message to Poke asking if you'd like automatic workout notifications.</p>
            <p>✅ Webhook automatically configured for instant notifications!</p>
            <p>Check Poke and reply to set up your preferences!</p>
            <p>You can close this tab now.</p>
            """
        else:
            # Already has webhook, send feature overview
            features_message = f"user connected strava and automatic notifications already enabled. tell them in casual poke style that they can get weekly summaries, search workouts by date/range, see recent activities, and analyze specific workouts. mention they can ask for weekly stats, activities from specific dates, or workout analysis."
            
            send_result = send_poke(features_message)
            print(f"[AUTH] Sent features overview to Poke: {send_result}")
            
            body = f"""
            <h1>Connected ✅</h1>
            <p>Athlete: <b>{athlete_name}</b> (ID {a.get('id')})</p>
            <p>✅ Automatic notifications are already enabled!</p>
            <p>📱 We've sent a message to Poke with all available features.</p>
            <p>You can close this tab now.</p>
            """
        
        return HTMLResponse(body, status_code=200)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[AUTH] Error: {e}")
        print(f"[AUTH] Traceback: {tb}")
        return HTMLResponse(f"<h1>Auth error</h1><pre>{e}</pre><hr><pre>{tb}</pre>", status_code=500)


# Create the ASGI app from FastMCP
app = mcp_server.http_app()
print("[MCP] Created ASGI app from FastMCP server")

if __name__ == "__main__":
    host = HOST
    port = PORT
    
    def _mask(v): 
        return v[:4] + f"…(len {len(v)})" if v else None
    
    print(f"[BOOT] Starting server on {host}:{port}")
    print("  • MCP endpoints: / (root)")
    print("  • Strava webhook: /strava/webhook")
    print("  • Health check: /healthz")
    print(f"[ENV] POKE_API_KEY: {_mask(POKE_API_KEY)}")
    print(f"[ENV] STRAVA_VERIFY_TOKEN: {STRAVA_VERIFY_TOKEN}")
    
    uvicorn.run(app, host=host, port=port)

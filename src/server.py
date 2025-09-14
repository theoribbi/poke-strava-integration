#!/usr/bin/env python3
import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, HTMLResponse
from mcp_strava.settings import HOST, PORT, POKE_API_KEY, STRAVA_VERIFY_TOKEN

# ========= MCP Server Setup =========
from mcp_strava.app import mcp as mcp_server
from mcp_strava.services.strava_webhook import verify_webhook, handle_webhook_event
from mcp_strava.services.strava_oauth import authorize_url, exchange_code, refresh_token
from mcp_strava.services.token_store import  save_tokens


print("[MCP] Adding custom routes to FastMCP server")


# ========= Health & Info Routes =========
@mcp_server.custom_route("/healthz", methods=["GET"])
async def healthz(request):
    return {"status": "healthy"}

@mcp_server.custom_route("/", methods=["GET"])
async def root(request):
    return {"ok": True, "routes": ["/ (MCP endpoints)", "/strava/webhook", "/healthz"]}

# ========= Strava Webhook Routes =========
@mcp_server.custom_route("/strava/webhook", methods=["GET"])
async def verify_strava_webhook(request):
    return await verify_webhook(request)

@mcp_server.custom_route("/strava/webhook", methods=["POST"])
async def handle_strava_webhook(request):
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

        a = (data.get("athlete") or {})
        body = f"""
        <h1>Connected ✅</h1>
        <p>Athlete: <b>{a.get('firstname','')} {a.get('lastname','')}</b> (ID {a.get('id')})</p>
        <p>You can close this tab and use the tools.</p>
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

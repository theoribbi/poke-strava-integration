#!/usr/bin/env python3
import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ========= MCP Server Setup =========
from mcp_strava.app import mcp as mcp_server
from mcp_strava.services.strava_webhook import verify_webhook, handle_webhook_event

print("[MCP] Adding custom routes to FastMCP server")

# ========= Health & Info Routes =========
@mcp_server.custom_route("/healthz", methods=["GET"])
async def healthz():
    return {"status": "healthy"}

@mcp_server.custom_route("/", methods=["GET"])
async def root():
    return {"ok": True, "routes": ["/ (MCP endpoints)", "/strava/webhook", "/healthz"]}

# ========= Strava Webhook Routes =========
@mcp_server.custom_route("/strava/webhook", methods=["GET"])
async def verify_strava_webhook(request):
    return await verify_webhook(request)

@mcp_server.custom_route("/strava/webhook", methods=["POST"])
async def handle_strava_webhook(request):
    return await handle_webhook_event(request)

# Create the ASGI app from FastMCP
app = mcp_server.http_app()
print("[MCP] Created ASGI app from FastMCP server")

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    def _mask(v): 
        return v[:4] + f"…(len {len(v)})" if v else None
    
    print(f"[BOOT] Starting server on {host}:{port}")
    print("  • MCP endpoints: / (root)")
    print("  • Strava webhook: /strava/webhook")
    print("  • Health check: /healthz")
    print(f"[ENV] POKE_API_KEY: {_mask(os.getenv('POKE_API_KEY'))}")
    print(f"[ENV] STRAVA_VERIFY_TOKEN: {os.getenv('STRAVA_VERIFY_TOKEN', 'dev-verify')}")
    
    uvicorn.run(app, host=host, port=port)

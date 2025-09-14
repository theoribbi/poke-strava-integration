# Strava → MCP → Poke — Integration Guide

A **MCP server prototype** that:
- connects to **Strava** via OAuth,
- exposes **MCP tools** (recent activities, weekly summary, analyze),
- receives **Strava webhooks** whenever a new activity is created and pushes a message to **Poke**.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Local Installation](#local-installation)
- [Create a Strava App](#create-a-strava-app)
- [Strava OAuth Flow (local)](#strava-oauth-flow-local)
- [Strava Webhooks](#strava-webhooks)
- [Poke Integration](#poke-integration)
- [Available MCP Tools](#available-mcp-tools)
- [Deploying on Render](#deploying-on-render)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [License](#license)

---

## Overview

- **Use case**: when an activity is created on Strava, generate a short feedback and send it to **Poke**.  
- **On-demand**: via MCP tools, request a **weekly recap** or fetch the **N most recent activities**.  
- **Demo mode**: single-user, tokens stored in a **local JSON file**.  
  > Can easily be extended to a DB (SQLite/Postgres) for multi-user.

---

## Architecture

```text
client (Poke, Inspector, etc.)
        │         
        │ MCP tools______  HTTP(S)
        v                    |
  FastMCP Server  <----------+---------  Strava Webhook POST (create/update)
        │                              (GET challenge for verification)
        │       ___ Strava API (GET activities, etc.)
        |
   Token store (JSON : tokens.json)
```

- **/mcp**: MCP transport over HTTP (via FastMCP).
- **/auth/strava/start**: redirect to Strava OAuth consent.
- **/auth/strava/callback**: exchange `code` → `access/refresh token`, save locally.
- **/strava/webhook**: webhook endpoint (GET: verification, POST: events).
- **/healthz**: health check.

---

## Prerequisites

- **Python 3.11+**
- **Node 18+** (optional for `@modelcontextprotocol/inspector`)
- A **Strava account** and a **Poke account**
- `ngrok` (for local webhook testing) or a public HTTPS host (Render)

---

## Environment Variables

Create a `.env` file in the project root using this template:

```env
# --- Strava OAuth ---
STRAVA_CLIENT_ID=your_strava_client_id
STRAVA_CLIENT_SECRET=your_strava_client_secret
STRAVA_VERIFY_TOKEN=dev-verify
STRAVA_REDIRECT_URI=http://localhost:8000/auth/strava/callback

# --- Token storage (single-user demo) ---
TOKEN_FILE=tokens.json

# --- Public URL (used for Strava webhooks) ---
PUBLIC_URL=https://xxxxx.ngrok-free.app

# --- Poke ---
POKE_API_KEY=your_poke_api_key
POKE_INBOUND_URL=https://poke.com/api/v1/inbound-sms/webhook

# --- Server ---
HOST=0.0.0.0
PORT=8000
```

> **STRAVA_VERIFY_TOKEN** must match the value you use when creating the webhook subscription.

---

## Local Installation

```bash
git clone <this-repo>
cd <this-repo>
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# optional: MCP inspector
npm i -g @modelcontextprotocol/inspector
```

Run the server:

```bash
PYTHONPATH=src python src/server.py
# or
PYTHONPATH=src uvicorn server:app --host 0.0.0.0 --port 8000
```

Check health: http://localhost:8000/healthz

---

## Create a Strava App

1. Go to **https://www.strava.com/settings/api**  
2. **Create & configure** your application:
   - *Authorization Callback Domain*: `localhost` for dev.
   - Copy your **Client ID** and **Client Secret** into `.env`.
3. Required scopes: `read,activity:read_all`.

---

## Strava OAuth Flow (local)

1. Open: **http://localhost:8000/auth/strava/start**  
2. Log in & authorize.  
3. You’ll be redirected to **/auth/strava/callback**; tokens are saved in `tokens.json`.  
4. Verify: test MCP tools or check your tokens file.

---

## Strava Webhooks

### 1) GET verification handshake
Strava calls **GET /strava/webhook** when creating a subscription, passing:
`hub.mode`, `hub.verify_token`, `hub.challenge`.

The server must reply:
```json
{"hub.challenge":"<the challenge>"}
```

### 2) Create a subscription
List existing subs:
```bash
curl -s "https://www.strava.com/api/v3/push_subscriptions?client_id=$STRAVA_CLIENT_ID&client_secret=$STRAVA_CLIENT_SECRET" | jq
```

Delete old subs:
```bash
curl -X DELETE "https://www.strava.com/api/v3/push_subscriptions/<id>?client_id=$STRAVA_CLIENT_ID&client_secret=$STRAVA_CLIENT_SECRET"
```

Create a new one:
```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions 
  -F client_id=$STRAVA_CLIENT_ID 
  -F client_secret=$STRAVA_CLIENT_SECRET 
  -F callback_url="https://<your-domain>/strava/webhook" 
  -F verify_token=$STRAVA_VERIFY_TOKEN
```

### 3) Test POST
Simulate an event:
```bash
curl -X POST https://<your-domain>/strava/webhook 
  -H 'Content-Type: application/json' 
  -d '{"object_type":"activity","aspect_type":"create","object_id":123456789,"owner_id":42}'
```

Or just create a **manual activity** in Strava. The webhook will trigger and push to Poke.

---

## Poke Integration

1. In **Poke → Integrations → New Integration**:
   - **Server URL**: `https://<your-domain>/mcp`
   - **API Key**: leave empty to let Poke auto-detect OAuth.  
     (For single-user demo, this can stay empty.)

2. In Poke you can now call:
   - `get_recent_activities`
   - `weekly_summary`
   - `analyze_activity`

3. The webhook handler pushes messages to your **Poke account** using `POKE_API_KEY`.

---

## Available MCP Tools

### `get_recent_activities(limit=10)`
- Returns the last N activities (normalized).
- Example response:
```json
[
  {"id":15797556600,"name":"Afternoon Weight Training","distance_km":0,"moving_time_min":49.4,"sport":"WeightTraining","start_date":"2025-09-13T13:06:25Z"},
  {"id":15775065265,"name":"Afternoon Run","distance_km":4.78,"moving_time_min":32.7,"sport":"Run","start_date":"2025-09-11T11:59:38Z"}
]
```

### `weekly_summary(include_content=false)`
- Aggregated stats for the current ISO week (Mon–Sun UTC).
- Includes per-sport breakdown and activity list.
- If `include_content=true`, also returns a preformatted string summary.

### `analyze_activity(activity_id)`
- Returns short textual feedback about one activity.
- Used by webhook and callable manually.

### `start_strava_login()` *(optional)*
- Returns Strava OAuth URL to start login flow from Poke.

---

## Deploying on Render

### Minimal `render.yaml`
```yaml
services:
  - type: web
    name: fastmcp-server
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: PYTHONPATH=src uvicorn server:app --host 0.0.0.0 --port $PORT --workers 1
    plan: free
    autoDeploy: false
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: HOST
        value: 0.0.0.0
      - key: PORT
        value: 8000
```

> **Do not put secrets in `render.yaml`**. Use the Render UI to add env vars securely.

Steps:
1. Deploy, check `/healthz`.
2. Update `PUBLIC_URL=https://<service>.onrender.com`.
3. Recreate Strava webhook subscription with this callback URL.
4. Open `/auth/strava/start` to connect your account.

---

## License

MIT (or your choice).  
This is a **hackathon prototype**, provided as-is.

---

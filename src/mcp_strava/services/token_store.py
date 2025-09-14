import json, os, time
from mcp_strava.settings import TOK_FILE

def save_tokens(data: dict):
    """Save tokens to file"""
    data["_saved_at"] = int(time.time())
    with open(TOK_FILE, "w") as f:
        json.dump(data, f)
    print("[TOKENS] saved to", TOK_FILE)

def load_tokens() -> dict | None:
    """Load tokens from file"""
    if not os.path.exists(TOK_FILE):
        return None
    with open(TOK_FILE) as f:
        return json.load(f)

def get_tokens() -> dict | None:
    """Alias for load_tokens for compatibility"""
    return load_tokens()

import os, sqlite3, psycopg

DB_URL = os.getenv("DATABASE_URL")
USE_SQLITE = not DB_URL

def _conn():
    if USE_SQLITE:
        path = os.getenv("SQLITE_PATH", "./dev.sqlite")
        return sqlite3.connect(path)
    return psycopg.connect(DB_URL, autocommit=True)

def init_db():
    """Crée les tables nécessaires si elles n'existent pas encore."""
    if USE_SQLITE:
        with _conn() as c:
            c.execute("""
            CREATE TABLE IF NOT EXISTS pending_auth (
                state TEXT PRIMARY KEY,
                api_key TEXT NOT NULL,
                created_at BIGINT NOT NULL
            )
            """)
            c.execute("""
            CREATE TABLE IF NOT EXISTS strava_tokens (
                api_key TEXT PRIMARY KEY,
                athlete_id BIGINT NOT NULL,
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at BIGINT NOT NULL,
                created_at BIGINT NOT NULL,
                firstname TEXT,
                lastname TEXT
            )
            """)
        print(f"[DB] SQLite ready at {os.getenv('SQLITE_PATH','./dev.sqlite')}")
    else:
        with _conn() as c:
            c.execute("""
            CREATE TABLE IF NOT EXISTS pending_auth (
                state TEXT PRIMARY KEY,
                api_key TEXT NOT NULL,
                created_at BIGINT NOT NULL
            )
            """)
            c.execute("""
            CREATE TABLE IF NOT EXISTS strava_tokens (
                api_key TEXT PRIMARY KEY,
                athlete_id BIGINT NOT NULL,
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at BIGINT NOT NULL,
                created_at BIGINT NOT NULL,
                firstname TEXT,
                lastname TEXT
            )
            """)
        print("[DB] Postgres ready (pending_auth, strava_tokens)")

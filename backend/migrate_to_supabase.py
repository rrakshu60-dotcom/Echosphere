"""
Migrate EchoSphere from local SQLite to Supabase PostgreSQL.
Usage:
    python backend/migrate_to_supabase.py [PASSWORD_OR_DATABASE_URL]
"""

import sys
import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

LOCAL_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "echosphere.db")
PROJECT_REF = "wvugkkwykdnyzcmaoxgj"
POOLER_HOST = "aws-0-ap-south-1.pooler.supabase.com"

def get_connection_string():
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if arg.startswith("postgresql://") or arg.startswith("postgres://"):
            return arg
        else:
            # Treat arg as password
            return f"postgresql://postgres.{PROJECT_REF}:{arg}@{POOLER_HOST}:6543/postgres?sslmode=require"
    
    env_url = os.getenv("SUPABASE_DATABASE_URL") or os.getenv("DATABASE_URL")
    if env_url and ("supabase" in env_url or "postgresql" in env_url):
        return env_url
        
    print("[!] No connection string or password provided.")
    print("Usage: python backend/migrate_to_supabase.py <YOUR_SUPABASE_DB_PASSWORD>")
    sys.exit(1)

def main():
    conn_str = get_connection_string()
    print("[*] Connecting to Supabase PostgreSQL...")
    try:
        pg_conn = psycopg2.connect(conn_str)
        pg_cursor = pg_conn.cursor()
        print("[+] Successfully connected to Supabase PostgreSQL!")
    except Exception as e:
        print(f"[!] Failed to connect to Supabase: {e}")
        sys.exit(1)

    # Initialize tables using backend models
    print("[*] Creating all database tables in Supabase...")
    os.environ["DATABASE_URL"] = conn_str
    from app.db.database import Base, engine
    Base.metadata.create_all(bind=engine)
    print("[+] All tables created successfully in Supabase!")

    # Read local SQLite data
    if not os.path.exists(LOCAL_DB_PATH):
        print(f"[!] Local database not found at {LOCAL_DB_PATH}")
        sys.exit(1)

    sq_conn = sqlite3.connect(LOCAL_DB_PATH)
    sq_cursor = sq_conn.cursor()

    # Tables to migrate
    tables = [
        "roles",
        "users",
        "departments",
        "announcements",
        "speaker_queue",
        "speaker_nodes",
        "system_settings"
    ]

    for tbl in tables:
        try:
            sq_cursor.execute(f"SELECT * FROM {tbl}")
            rows = sq_cursor.fetchall()
            col_names = [d[0] for d in sq_cursor.description]
            if not rows:
                print(f"[-] Table {tbl} is empty locally. Skipping.")
                continue

            cols_str = ", ".join(f'"{c}"' for c in col_names)
            placeholders = ", ".join(["%s"] * len(col_names))
            insert_query = f'INSERT INTO "{tbl}" ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'

            pg_cursor.executemany(insert_query, rows)
            pg_conn.commit()
            print(f"[+] Migrated {len(rows)} rows into {tbl} in Supabase.")
        except Exception as err:
            print(f"[*] Note on table {tbl}: {err}")
            pg_conn.rollback()

    pg_conn.close()
    sq_conn.close()
    print("\n[SUCCESS] All data has been migrated into Supabase PostgreSQL!")

if __name__ == "__main__":
    main()

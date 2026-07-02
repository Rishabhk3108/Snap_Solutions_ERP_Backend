"""
Run this from the snapm-solution-erp directory:
    python test_connection.py
"""
import os
from dotenv import load_dotenv

load_dotenv()

host     = os.getenv("DB_HOST")
port     = int(os.getenv("DB_PORT", "5432"))
user     = os.getenv("DB_USER")
password = os.getenv("DB_PASS")
dbname   = os.getenv("DB_NAME", "postgres")

print("=== Loaded .env values ===")
print(f"  HOST : {host}")
print(f"  PORT : {port}")
print(f"  USER : {user}")
print(f"  DB   : {dbname}")
print(f"  PASS : {repr(password)}")
print()

import psycopg2

print("--- Test 1: session pooler port 5432 ---")
try:
    conn = psycopg2.connect(
        host=host, port=port, dbname=dbname,
        user=user, password=password, sslmode="require",
        connect_timeout=10,
    )
    print("  SUCCESS on port 5432")
    conn.close()
except Exception as e:
    print(f"  FAIL: {e}")

print()
print("--- Test 2: transaction pooler port 6543 ---")
try:
    conn = psycopg2.connect(
        host=host, port=6543, dbname=dbname,
        user=user, password=password, sslmode="require",
        connect_timeout=10,
    )
    print("  SUCCESS on port 6543")
    conn.close()
except Exception as e:
    print(f"  FAIL: {e}")

print()
print("--- Test 3: direct connection (IPv6) ---")
try:
    conn = psycopg2.connect(
        host="db.flfarhfjodxwwxlyzbpr.supabase.co",
        port=5432, dbname="postgres",
        user="postgres",
        password=password, sslmode="require",
        connect_timeout=15,
    )
    print("  SUCCESS on direct (IPv6)")
    conn.close()
except Exception as e:
    print(f"  FAIL: {e}")

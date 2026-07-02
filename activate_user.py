"""
Run: python activate_user.py
Lists all users and lets you activate one by username.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT", "5432")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASS")
name = os.getenv("DB_NAME", "postgres")

url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}?sslmode=require"
engine = create_engine(url)

with engine.connect() as conn:
    rows = conn.execute(text("SELECT id, username, full_name, role, active FROM employees ORDER BY id")).fetchall()
    print("\nAll users:")
    print(f"{'ID':<6} {'Username':<20} {'Full Name':<30} {'Role':<20} {'Active'}")
    print("-" * 85)
    for r in rows:
        print(f"{r.id:<6} {r.username:<20} {r.full_name:<30} {r.role:<20} {r.active}")

    target = input("\nEnter username to activate (or press Enter to skip): ").strip()
    if target:
        result = conn.execute(
            text("UPDATE employees SET active = true WHERE username = :u"),
            {"u": target}
        )
        conn.commit()
        if result.rowcount:
            print(f"✓ '{target}' is now active. You can log in.")
        else:
            print(f"✗ Username '{target}' not found.")

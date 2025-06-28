import sqlite3
import json
import os
from dotenv import load_dotenv

load_dotenv(override=True)

def init_db():
    conn = sqlite3.connect(os.getenv("SQLITE3_DB_PATH"), check_same_thread=False)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS raw_inputs (
        id TEXT PRIMARY KEY,
        type TEXT,
        content_raw TEXT,
        source TEXT,
        tags TEXT,
        timestamp TEXT
    )
    """)
    conn.commit()
    conn.close()

def save_input_to_db(data):
    conn = sqlite3.connect(os.getenv("SQLITE3_DB_PATH"), check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        INSERT INTO raw_inputs (id, type, content_raw, source, tags, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data["id"],
        data["type"],
        data["content_raw"],
        data["source"],
        json.dumps(data.get("tags", [])),
        data["timestamp"]
    ))
    conn.commit()
    conn.close()

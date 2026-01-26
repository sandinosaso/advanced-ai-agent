from __future__ import annotations

from typing import Any

import mysql.connector

from config import get_db_config


def get_connection():
    cfg = get_db_config()
    return mysql.connector.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
    )


def fetch_all(query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
            return list(rows)
        finally:
            cursor.close()
    finally:
        conn.close()


def table_exists(table_name: str) -> bool:
    rows = fetch_all("SHOW TABLES LIKE %s", (table_name,))
    return len(rows) > 0

from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()


def _get_required(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def get_db_config() -> dict:
    return {
        "host": _get_required("DB_HOST"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": _get_required("DB_USER"),
        "password": _get_required("DB_PWD"),
        "database": _get_required("DB_NAME"),
    }

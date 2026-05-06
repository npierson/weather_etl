"""
config.py
=========
Loads your settings from the .env file and makes them available to etl.py.

IMPORTANT: Never hardcode passwords or credentials directly in Python files.
           Always keep them in the .env file (which is never shared or committed to git).
"""

import os
from datetime import date, timedelta
from dotenv import load_dotenv

# Load variables from your .env file into the environment
load_dotenv()


# ─────────────────────────────────────────────
# SNOWFLAKE DATABASE CONNECTION
# ─────────────────────────────────────────────
# These are read from your .env file.
# See .env.example for instructions on filling them in.
#
# How to find your account identifier:
#   Snowflake UI → bottom-left corner → hover your username → "Copy account identifier"
#   Format is usually: <orgname>-<accountname>  (e.g. "myorg-myaccount")
def _load_private_key(path: str):
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    with open(path, "rb") as f:
        return load_pem_private_key(f.read(), password=None)

_private_key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH", "snowflake_private_key.pem")


def _resolve_end_date(value: str) -> str:
    today = date.today()
    v = (value or "").strip().lower()
    if v in ("", "yesterday"):
        return (today - timedelta(days=1)).isoformat()
    if v == "today":
        return today.isoformat()
    return value

DB_CONFIG = {
    "account":     os.getenv("SNOWFLAKE_ACCOUNT"),    # e.g. "myorg-myaccount"
    "user":        os.getenv("SNOWFLAKE_USER"),        # e.g. "nat"
    "private_key": _load_private_key(_private_key_path),
    "warehouse":   os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
    "database":    os.getenv("SNOWFLAKE_DATABASE", "WEATHER_DB"),
    "schema":      os.getenv("SNOWFLAKE_SCHEMA",   "WEATHER"),
    "role":        os.getenv("SNOWFLAKE_ROLE",     "ACCOUNTADMIN"),
}


# ─────────────────────────────────────────────
# WEATHER SETTINGS
# ─────────────────────────────────────────────
# Change these to pull weather for a different city or date range.
WEATHER_CONFIG = {
    "location_name": os.getenv("WEATHER_LOCATION_NAME", "Boston, MA"),

    # Latitude and longitude of your city
    # Boston: 42.36, -71.06  |  New York: 40.71, -74.01  |  Chicago: 41.88, -87.63
    "latitude":  float(os.getenv("WEATHER_LATITUDE",  "42.36")),
    "longitude": float(os.getenv("WEATHER_LONGITUDE", "-71.06")),

    # Date range — pull up to 1 year at a time for best performance.
    # Format: "YYYY-MM-DD". The end_date also accepts the sentinels
    # "yesterday" or "today" for a rolling window.
    "start_date": os.getenv("WEATHER_START_DATE", "2025-01-01"),
    "end_date":   _resolve_end_date(os.getenv("WEATHER_END_DATE", "2025-12-31")),
}

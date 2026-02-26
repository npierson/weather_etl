"""
config.py
=========
Loads your settings from the .env file and makes them available to etl.py.

IMPORTANT: Never hardcode passwords or credentials directly in Python files.
           Always keep them in the .env file (which is never shared or committed to git).
"""

import os
from dotenv import load_dotenv

# Load variables from your .env file into the environment
load_dotenv()


# ─────────────────────────────────────────────
# REDSHIFT DATABASE CONNECTION
# ─────────────────────────────────────────────
# These are read from your .env file.
# See .env.example for instructions on filling them in.
DB_CONFIG = {
    "host":     os.getenv("REDSHIFT_HOST"),      # e.g. "my-cluster.abc123.us-east-1.redshift.amazonaws.com"
    "port":     int(os.getenv("REDSHIFT_PORT", "5439")),  # Redshift default port is 5439
    "dbname":   os.getenv("REDSHIFT_DB"),        # e.g. "dev"
    "user":     os.getenv("REDSHIFT_USER"),      # e.g. "admin"
    "password": os.getenv("REDSHIFT_PASSWORD"),  # your Redshift password
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

    # Date range — pull up to 1 year at a time for best performance
    # Format: "YYYY-MM-DD"
    "start_date": os.getenv("WEATHER_START_DATE", "2025-01-01"),
    "end_date":   os.getenv("WEATHER_END_DATE",   "2025-12-31"),
}

"""
weather_etl.py
==============
A beginner-friendly ETL (Extract → Transform → Load) pipeline that:
  1. EXTRACTS weather data from the free Open-Meteo API
  2. TRANSFORMS it into a clean table using pandas
  3. LOADS it into an Amazon Redshift table

What you'll learn:
  - How to call a public API with the `requests` library
  - How to clean and reshape data with `pandas`
  - How to connect to a database and insert rows with `psycopg2`
"""

import requests          # for making HTTP API calls
import pandas as pd      # for working with tabular data
import psycopg           # for connecting to Redshift (it's PostgreSQL-compatible)
import logging           # for printing helpful status messages
from config import DB_CONFIG, WEATHER_CONFIG

# ─────────────────────────────────────────────
# SETUP: Configure logging so we can track progress
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# STEP 1: EXTRACT — Pull data from the API
# ─────────────────────────────────────────────
def extract_weather_data(latitude: float, longitude: float, start_date: str, end_date: str) -> dict:
    """
    Calls the Open-Meteo historical weather API and returns raw JSON data.

    Args:
        latitude:   Location latitude  (e.g. 42.36 for Boston)
        longitude:  Location longitude (e.g. -71.06 for Boston)
        start_date: Start of date range in "YYYY-MM-DD" format
        end_date:   End of date range in "YYYY-MM-DD" format

    Returns:
        A dictionary (JSON) containing hourly weather readings
    """
    log.info(f"Fetching weather data for ({latitude}, {longitude}) from {start_date} to {end_date}...")

    # The Open-Meteo API URL — no API key needed!
    url = "https://archive-api.open-meteo.com/v1/archive"

    # These are the "query parameters" we send with our request
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": [
            "temperature_2m",           # Temperature at 2 meters above ground (°C)
            "relative_humidity_2m",     # Relative humidity (%)
            "precipitation",            # Rainfall / snowfall (mm)
            "wind_speed_10m",           # Wind speed at 10m height (km/h)
            "weather_code",             # WMO weather condition code
        ],
        "temperature_unit": "fahrenheit",  # Switch to Fahrenheit if you prefer
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "America/New_York",
    }

    # Make the API call
    response = requests.get(url, params=params, timeout=30)

    # Raise an error if the request failed (e.g. 404, 500)
    response.raise_for_status()

    data = response.json()
    log.info(f"  ✓ Received {len(data['hourly']['time'])} hourly records")
    return data


# ─────────────────────────────────────────────
# STEP 2: TRANSFORM — Clean and reshape the data
# ─────────────────────────────────────────────
def transform_weather_data(raw_data: dict, location_name: str) -> pd.DataFrame:
    """
    Converts the raw API JSON into a clean pandas DataFrame.

    Args:
        raw_data:      The JSON dictionary returned by the API
        location_name: A human-readable name for the location (e.g. "Boston, MA")

    Returns:
        A clean DataFrame ready to be loaded into Redshift
    """
    log.info("Transforming raw data into a clean table...")

    hourly = raw_data["hourly"]

    # Build a DataFrame from the hourly data
    df = pd.DataFrame({
        "recorded_at":        hourly["time"],
        "temperature_f":      hourly["temperature_2m"],
        "humidity_pct":       hourly["relative_humidity_2m"],
        "precipitation_in":   hourly["precipitation"],
        "wind_speed_mph":     hourly["wind_speed_10m"],
        "weather_code":       hourly["weather_code"],
    })

    # Convert the "recorded_at" column from a string to a real datetime
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])

    # Add metadata columns
    df["location_name"] = location_name
    df["latitude"]      = raw_data["latitude"]
    df["longitude"]     = raw_data["longitude"]

    # Drop rows where ALL weather readings are missing (null)
    df.dropna(subset=["temperature_f", "precipitation_in"], how="all", inplace=True)

    # Round numeric columns to 2 decimal places for tidiness
    numeric_cols = ["temperature_f", "humidity_pct", "precipitation_in", "wind_speed_mph"]
    df[numeric_cols] = df[numeric_cols].round(2)

    log.info(f"  ✓ Transformed {len(df)} rows, {len(df.columns)} columns")
    return df


# ─────────────────────────────────────────────
# STEP 3: LOAD — Write data to Redshift
# ─────────────────────────────────────────────
def load_to_redshift(df: pd.DataFrame, table_name: str = "weather_hourly") -> None:
    """
    Connects to Redshift and inserts the DataFrame rows into a table.
    Uses "upsert" logic to avoid duplicate rows if you run it multiple times.

    Args:
        df:         The clean DataFrame to load
        table_name: The Redshift table to insert into
    """
    log.info(f"Connecting to Redshift and loading {len(df)} rows into '{table_name}'...")

    # Connect to Redshift using credentials from config.py
    conn = psycopg.connect(**DB_CONFIG)

    try:
        with conn.cursor() as cursor:
            # Create a temporary staging table to hold our new data
            # This lets us do an "upsert" (update if exists, insert if new)
            cursor.execute(f"""
                CREATE TEMP TABLE staging_{table_name} (LIKE {table_name});
            """)

            # Convert DataFrame to a list of tuples (one per row)
            rows = [tuple(row) for row in df.itertuples(index=False)]

            # Column names in the order they appear in the DataFrame
            columns = list(df.columns)

            # Bulk-insert all rows into the staging table (much faster than one-by-one)
            insert_sql = f"""
                INSERT INTO staging_{table_name} ({', '.join(columns)})
                VALUES ({', '.join(['%s'] * len(columns))})
            """
            cursor.executemany(insert_sql, rows)

            # Delete any existing rows that match on location + timestamp (avoid duplicates)
            cursor.execute(f"""
                DELETE FROM {table_name}
                USING staging_{table_name}
                WHERE {table_name}.location_name = staging_{table_name}.location_name
                  AND {table_name}.recorded_at   = staging_{table_name}.recorded_at;
            """)

            # Insert the new/updated rows from staging into the real table
            cursor.execute(f"""
                INSERT INTO {table_name}
                SELECT * FROM staging_{table_name};
            """)

        # Commit the transaction (save the changes)
        conn.commit()
        log.info(f"  ✓ Successfully loaded {len(df)} rows into {table_name}")

    except Exception as e:
        # If anything goes wrong, roll back to avoid partial writes
        conn.rollback()
        log.error(f"  ✗ Load failed: {e}")
        raise

    finally:
        # Always close the connection, even if something went wrong
        conn.close()


# ─────────────────────────────────────────────
# MAIN: Run the full ETL pipeline
# ─────────────────────────────────────────────
def run_pipeline():
    """
    Orchestrates the full Extract → Transform → Load pipeline.
    Edit WEATHER_CONFIG in config.py to change location and date range.
    """
    log.info("=" * 50)
    log.info("Starting Weather ETL Pipeline")
    log.info("=" * 50)

    # EXTRACT
    raw = extract_weather_data(
        latitude=WEATHER_CONFIG["latitude"],
        longitude=WEATHER_CONFIG["longitude"],
        start_date=WEATHER_CONFIG["start_date"],
        end_date=WEATHER_CONFIG["end_date"],
    )

    # TRANSFORM
    df = transform_weather_data(raw, location_name=WEATHER_CONFIG["location_name"])

    # Preview the data before loading (great for debugging!)
    log.info("\nSample of data to be loaded:")
    print(df.head(5).to_string(index=False))
    print()

    # LOAD
    load_to_redshift(df, table_name="weather_hourly")

    log.info("=" * 50)
    log.info("Pipeline complete!")
    log.info("=" * 50)


# This block runs only when you execute this file directly (not when imported)
if __name__ == "__main__":
    run_pipeline()

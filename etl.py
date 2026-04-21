"""
etl.py
======
A beginner-friendly ETL (Extract → Transform → Load) pipeline that:
  1. EXTRACTS weather data from the free Open-Meteo API
  2. TRANSFORMS it into a clean table using pandas
  3. LOADS it into a Snowflake table

What you'll learn:
  - How to call a public API with the `requests` library
  - How to clean and reshape data with `pandas`
  - How to connect to Snowflake and insert rows with `snowflake-connector-python`
"""

import requests                          # for making HTTP API calls
import pandas as pd                      # for working with tabular data
import snowflake.connector               # for connecting to Snowflake
from snowflake.connector.pandas_tools import write_pandas  # fast bulk load via pandas
import logging                           # for printing helpful status messages
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
        A clean DataFrame ready to be loaded into Snowflake
    """
    log.info("Transforming raw data into a clean table...")

    hourly = raw_data["hourly"]

    # Build a DataFrame from the hourly data
    df = pd.DataFrame({
        "RECORDED_AT":        hourly["time"],
        "TEMPERATURE_F":      hourly["temperature_2m"],
        "HUMIDITY_PCT":       hourly["relative_humidity_2m"],
        "PRECIPITATION_IN":   hourly["precipitation"],
        "WIND_SPEED_MPH":     hourly["wind_speed_10m"],
        "WEATHER_CODE":       hourly["weather_code"],
    })

    # NOTE: Snowflake column names are uppercase by default.
    # The DataFrame column names above match the table columns in create_tables_snowflake.sql.

    # Convert the "RECORDED_AT" column from a string to a real datetime
    df = df.assign(RECORDED_AT=pd.to_datetime(df["RECORDED_AT"]))

    # Add metadata columns
    df["LOCATION_NAME"] = location_name
    df["LATITUDE"]      = raw_data["latitude"]
    df["LONGITUDE"]     = raw_data["longitude"]

    # Drop rows where ALL weather readings are missing (null)
    df.dropna(subset=["TEMPERATURE_F", "PRECIPITATION_IN"], how="all", inplace=True)

    # Round numeric columns to 2 decimal places for tidiness
    numeric_cols = ["TEMPERATURE_F", "HUMIDITY_PCT", "PRECIPITATION_IN", "WIND_SPEED_MPH"]
    df[numeric_cols] = df[numeric_cols].round(2)

    log.info(f"  ✓ Transformed {len(df)} rows, {len(df.columns)} columns")
    return df


# ─────────────────────────────────────────────
# STEP 3: LOAD — Write data to Snowflake
# ─────────────────────────────────────────────
def load_to_snowflake(df: pd.DataFrame, table_name: str = "WEATHER_HOURLY") -> None:
    """
    Connects to Snowflake and upserts the DataFrame rows into a table.
    Uses a staging table + MERGE to avoid duplicate rows on repeated runs.

    Args:
        df:         The clean DataFrame to load
        table_name: The Snowflake table to insert into (default: WEATHER_HOURLY)
    """
    log.info(f"Connecting to Snowflake and loading {len(df)} rows into '{table_name}'...")

    # Connect using credentials from config.py
    conn = snowflake.connector.connect(**DB_CONFIG)

    try:
        db    = DB_CONFIG["database"]
        schema = DB_CONFIG["schema"]
        fq_target  = f"{db}.{schema}.{table_name}"
        fq_staging = f"{db}.{schema}.STAGING_{table_name}"

        with conn.cursor() as cursor:
            # Create a temp staging table with the same structure as the target
            # (TEMPORARY means it auto-drops when the session ends)
            cursor.execute(f"CREATE TEMPORARY TABLE {fq_staging} LIKE {fq_target};")

            # Bulk-load the DataFrame into the staging table using write_pandas
            # This is much faster than INSERT row-by-row for large datasets
            success, num_chunks, num_rows, output = write_pandas(
                conn=conn,
                df=df,
                table_name=f"STAGING_{table_name}",
                schema=schema,
                database=db,
                auto_create_table=False,
                overwrite=False,
            )
            log.info(f"  ✓ Staged {num_rows} rows in {num_chunks} chunk(s)")

            # MERGE: update existing rows or insert new ones (no duplicates)
            # Matches on location_name + recorded_at as the natural unique key
            cursor.execute(f"""
                MERGE INTO {fq_target} AS target
                USING {fq_staging} AS source
                    ON  target.LOCATION_NAME = source.LOCATION_NAME
                    AND target.RECORDED_AT   = source.RECORDED_AT
                WHEN MATCHED THEN UPDATE SET
                    target.TEMPERATURE_F    = source.TEMPERATURE_F,
                    target.HUMIDITY_PCT     = source.HUMIDITY_PCT,
                    target.PRECIPITATION_IN = source.PRECIPITATION_IN,
                    target.WIND_SPEED_MPH   = source.WIND_SPEED_MPH,
                    target.WEATHER_CODE     = source.WEATHER_CODE,
                    target.LATITUDE         = source.LATITUDE,
                    target.LONGITUDE        = source.LONGITUDE
                WHEN NOT MATCHED THEN INSERT (
                    RECORDED_AT, LOCATION_NAME, LATITUDE, LONGITUDE,
                    TEMPERATURE_F, HUMIDITY_PCT, PRECIPITATION_IN,
                    WIND_SPEED_MPH, WEATHER_CODE
                ) VALUES (
                    source.RECORDED_AT, source.LOCATION_NAME, source.LATITUDE, source.LONGITUDE,
                    source.TEMPERATURE_F, source.HUMIDITY_PCT, source.PRECIPITATION_IN,
                    source.WIND_SPEED_MPH, source.WEATHER_CODE
                );
            """)

        log.info(f"  ✓ Successfully merged {len(df)} rows into {table_name}")

    except Exception as e:
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
    log.info("Starting Weather ETL Pipeline (Snowflake)")
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
    load_to_snowflake(df, table_name="WEATHER_HOURLY")

    log.info("=" * 50)
    log.info("Pipeline complete!")
    log.info("=" * 50)


# This block runs only when you execute this file directly (not when imported)
if __name__ == "__main__":
    run_pipeline()

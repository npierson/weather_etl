-- create_tables.sql
-- ─────────────────────────────────────────────────────────────────────────────
-- Run this script ONCE in your Redshift query editor to create the table
-- that the ETL pipeline will load data into.
--
-- HOW TO RUN:
--   AWS Console → Amazon Redshift → Query editor v2 → paste and run this SQL
-- ─────────────────────────────────────────────────────────────────────────────


-- Create a schema to keep our weather data organized
-- (A schema is like a folder inside a database)
CREATE SCHEMA IF NOT EXISTS weather;


-- The main table that stores hourly weather readings
CREATE TABLE IF NOT EXISTS weather_hourly (

    -- Surrogate key: auto-incrementing unique ID for each row
    id              BIGINT IDENTITY(1, 1),

    -- When was this reading taken?
    recorded_at     TIMESTAMP NOT NULL,

    -- Where was it taken?
    location_name   VARCHAR(100) NOT NULL,
    latitude        DECIMAL(9, 6),
    longitude       DECIMAL(9, 6),

    -- What were the conditions?
    temperature_f   DECIMAL(6, 2),   -- Temperature in Fahrenheit
    humidity_pct    DECIMAL(5, 2),   -- Relative humidity (0–100%)
    precipitation_in DECIMAL(6, 3),  -- Precipitation in inches
    wind_speed_mph  DECIMAL(6, 2),   -- Wind speed in miles per hour
    weather_code    SMALLINT,        -- WMO weather condition code (see note below)

    -- Audit columns: track when rows were created
    loaded_at       TIMESTAMP DEFAULT GETDATE(),

    -- Primary key constraint
    PRIMARY KEY (id)
)
-- DISTKEY: Redshift distributes rows across nodes by this column.
-- Using location_name means all rows for one city live on the same node,
-- which makes queries like "WHERE location_name = 'Boston, MA'" very fast.
DISTKEY (location_name)

-- SORTKEY: Redshift physically sorts rows by this column on disk.
-- Time-series data is almost always queried by date, so this is a great choice.
SORTKEY (recorded_at);


-- ─────────────────────────────────────────────────────────────────────────────
-- HELPFUL QUERY: Preview your data after loading
-- ─────────────────────────────────────────────────────────────────────────────
-- SELECT
--     recorded_at,
--     location_name,
--     temperature_f,
--     humidity_pct,
--     precipitation_in,
--     wind_speed_mph
-- FROM weather_hourly
-- ORDER BY recorded_at DESC
-- LIMIT 20;


-- ─────────────────────────────────────────────────────────────────────────────
-- WMO WEATHER CODES (for reference)
-- ─────────────────────────────────────────────────────────────────────────────
-- Code  | Meaning
-- ────────────────────────────────────────────
--   0   | Clear sky
--   1   | Mainly clear
--   2   | Partly cloudy
--   3   | Overcast
--  45   | Foggy
--  51   | Light drizzle
--  61   | Slight rain
--  71   | Slight snow
--  80   | Slight rain showers
--  95   | Thunderstorm
-- ─────────────────────────────────────────────────────────────────────────────

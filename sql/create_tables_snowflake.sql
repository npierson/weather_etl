-- create_tables_snowflake.sql
-- ─────────────────────────────────────────────────────────────────────────────
-- Run this script ONCE in your Snowflake worksheet to create the table
-- that the ETL pipeline will load data into.
--
-- HOW TO RUN:
--   Snowflake UI → Worksheets → paste and run this SQL
--   (Make sure your role is ACCOUNTADMIN or has CREATE DATABASE privileges)
-- ─────────────────────────────────────────────────────────────────────────────


-- Create a dedicated database for this project
CREATE DATABASE IF NOT EXISTS WEATHER_DB;
USE DATABASE WEATHER_DB;


-- Create a schema to keep our weather data organized
-- (A schema is like a folder inside a database)
CREATE SCHEMA IF NOT EXISTS WEATHER;
USE SCHEMA WEATHER;


-- The main table that stores hourly weather readings
-- NOTE: Snowflake column names are case-insensitive but stored as uppercase.
--       The ETL script uses uppercase column names to match this convention.
CREATE TABLE IF NOT EXISTS WEATHER_HOURLY (

    -- Surrogate key: auto-incrementing unique ID for each row
    ID              NUMBER AUTOINCREMENT PRIMARY KEY,

    -- When was this reading taken?
    RECORDED_AT     TIMESTAMP_NTZ NOT NULL,

    -- Where was it taken?
    LOCATION_NAME   VARCHAR(100) NOT NULL,
    LATITUDE        NUMBER(9, 6),
    LONGITUDE       NUMBER(9, 6),

    -- What were the conditions?
    TEMPERATURE_F   NUMBER(6, 2),    -- Temperature in Fahrenheit
    HUMIDITY_PCT    NUMBER(5, 2),    -- Relative humidity (0–100%)
    PRECIPITATION_IN NUMBER(6, 3),  -- Precipitation in inches
    WIND_SPEED_MPH  NUMBER(6, 2),   -- Wind speed in miles per hour
    WEATHER_CODE    NUMBER(5, 0),   -- WMO weather condition code (see note below)

    -- Audit column: track when rows were inserted
    LOADED_AT       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()

);


-- ─────────────────────────────────────────────────────────────────────────────
-- OPTIONAL: Add a unique constraint to support the MERGE upsert logic
-- This prevents duplicates on (location + timestamp) if you run the ETL
-- multiple times over the same date range.
-- ─────────────────────────────────────────────────────────────────────────────
-- NOTE: Snowflake does not enforce unique constraints, but declaring them
-- helps document the intended uniqueness and enables some query optimizations.
ALTER TABLE WEATHER_HOURLY
    ADD CONSTRAINT uq_weather_location_time
    UNIQUE (LOCATION_NAME, RECORDED_AT)
    RELY;


-- ─────────────────────────────────────────────────────────────────────────────
-- HELPFUL QUERY: Preview your data after loading
-- ─────────────────────────────────────────────────────────────────────────────
-- SELECT
--     RECORDED_AT,
--     LOCATION_NAME,
--     TEMPERATURE_F,
--     HUMIDITY_PCT,
--     PRECIPITATION_IN,
--     WIND_SPEED_MPH
-- FROM WEATHER_HOURLY
-- ORDER BY RECORDED_AT DESC
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

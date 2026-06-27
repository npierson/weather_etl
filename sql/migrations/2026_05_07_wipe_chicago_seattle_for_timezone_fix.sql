-- ─────────────────────────────────────────────────────────────────────────────
-- One-time migration paired with PR #1 (fix/etl-per-city-timezone).
--
-- Before this PR, etl.py hardcoded America/New_York as the API timezone for
-- every city, so Chicago and Seattle hourly rows in WEATHER_HOURLY are labeled
-- in NYC time (1h and 3h shifted from local). After the PR, etl.py forwards
-- each city's IANA timezone, so new pulls will use Central / Pacific labels.
--
-- The MERGE in etl.py keys on (LOCATION_NAME, RECORDED_AT). Without this
-- migration, a re-pull would INSERT new rows alongside the old NYC-labeled
-- ones for the same wall-clock moments, doubling the row count and corrupting
-- daily_weather aggregates.
--
-- This script wipes Chicago and Seattle so the next ETL run repopulates them
-- with consistent local-timezone labels. Boston / NYC / Miami are unaffected
-- (already in America/New_York).
--
-- HOW TO RUN:
--   See "Runbook" in the PR description for the full sequence.
--   In short: paste this into a Snowflake worksheet between the merge and
--   the next ETL run.
-- ─────────────────────────────────────────────────────────────────────────────

USE DATABASE WEATHER_DB;

-- Sanity check: how many rows are about to be deleted?
SELECT LOCATION_NAME, COUNT(*) AS rows_to_delete
FROM WEATHER.WEATHER_HOURLY
WHERE LOCATION_NAME IN ('Chicago, IL', 'Seattle, WA')
GROUP BY 1;

-- Wipe raw rows. The next ETL run will repopulate from start_date forward
-- using each city's correct IANA timezone.
DELETE FROM WEATHER.WEATHER_HOURLY
WHERE LOCATION_NAME IN ('Chicago, IL', 'Seattle, WA');

-- Verify
SELECT LOCATION_NAME, COUNT(*) AS remaining
FROM WEATHER.WEATHER_HOURLY
GROUP BY 1
ORDER BY 1;
-- Expected: Boston/NYC/Miami unchanged; Chicago/Seattle absent.

-- NOTE: daily_weather is built by dbt, NOT cleaned up here. After the
-- next ETL run repopulates raw, run from your local machine:
--
--     cd weather_dbt && dbt build --full-refresh
--
-- A regular incremental dbt run won't backfill historical days for the
-- wiped cities (the incremental filter looks at max(weather_date), which
-- stays at "yesterday" because Boston/NYC/Miami still have data there).
-- --full-refresh recomputes daily_weather from scratch using the freshly
-- repopulated raw data.

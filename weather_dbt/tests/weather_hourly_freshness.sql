-- Freshness gate on the raw landing table.
-- The daily ETL backfills through "yesterday" (America/New_York), so the
-- newest RECORDED_AT should never be more than ~36 hours behind now.
-- If this fails, the Python job on Fargate didn't land new rows today.
-- Test passes when this query returns zero rows.
with latest as (
    select max(recorded_at) as max_recorded_at
    from {{ source('weather_raw', 'WEATHER_HOURLY') }}
)
select
    max_recorded_at,
    timestampdiff('hour', max_recorded_at, convert_timezone('America/New_York', current_timestamp())) as hours_behind
from latest
where max_recorded_at is null
   or timestampdiff('hour', max_recorded_at, convert_timezone('America/New_York', current_timestamp())) > 36

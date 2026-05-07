-- Coverage parity: for every city, daily_weather must span the same date range
-- as the raw hourly source. Catches incremental-model gaps where historical
-- raw rows were backfilled but the mart's incremental filter skipped them.
-- (Fix is usually: dbt run --select daily_weather --full-refresh.)
-- Test passes when this query returns zero rows.
with src as (
    select
        location_name,
        cast(min(recorded_at) as date) as src_first_date,
        cast(max(recorded_at) as date) as src_last_date
    from {{ source('weather_raw', 'WEATHER_HOURLY') }}
    group by 1
),
mart as (
    select
        dl.location_name,
        min(dw.weather_date) as mart_first_date,
        max(dw.weather_date) as mart_last_date
    from {{ ref('daily_weather') }} dw
    inner join {{ ref('dim_location') }} dl using (location_id)
    group by 1
)
select
    coalesce(src.location_name, mart.location_name) as location_name,
    src.src_first_date,
    mart.mart_first_date,
    src.src_last_date,
    mart.mart_last_date
from src
full outer join mart using (location_name)
where src.src_first_date is distinct from mart.mart_first_date
   or src.src_last_date  is distinct from mart.mart_last_date

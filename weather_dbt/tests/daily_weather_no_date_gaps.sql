-- No missing days: between each city's earliest and latest weather_date,
-- there should be a row for every calendar day. Catches a job that silently
-- skipped a run.
-- Test passes when this query returns zero rows.
with bounds as (
    select
        location_id,
        min(weather_date) as first_date,
        max(weather_date) as last_date,
        count(distinct weather_date) as observed_days
    from {{ ref('daily_weather') }}
    group by 1
)
select
    location_id,
    first_date,
    last_date,
    observed_days,
    datediff('day', first_date, last_date) + 1 as expected_days
from bounds
where observed_days <> datediff('day', first_date, last_date) + 1

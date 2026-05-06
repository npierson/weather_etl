-- Sanity: avg/min/max temperatures should fall within plausible Earth-surface bounds.
-- Catches unit-conversion regressions (e.g. silently switching back to Celsius).
-- Test passes when this query returns zero rows.
select
    location_name,
    weather_date,
    min_temperature_f,
    avg_temperature_f,
    max_temperature_f
from {{ ref('daily_weather') }}
where min_temperature_f < -80
   or max_temperature_f > 140
   or avg_temperature_f < -80
   or avg_temperature_f > 140
   or min_temperature_f > max_temperature_f

-- The daily average temperature must fall between the day's min and max.
-- Cheap invariant that catches aggregation bugs in daily_weather.sql.
-- Test passes when this query returns zero rows.
select
    location_id,
    weather_date,
    min_temperature_f,
    avg_temperature_f,
    max_temperature_f
from {{ ref('daily_weather') }}
where avg_temperature_f < min_temperature_f
   or avg_temperature_f > max_temperature_f

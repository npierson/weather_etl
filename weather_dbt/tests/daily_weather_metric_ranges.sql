-- Range sanity for non-temperature metrics. Catches unit regressions and
-- corrupt loads (e.g. negative precipitation, humidity expressed as 0–1).
-- (lat/lon range checks moved to dim_location_geocoords_valid.sql.)
-- Test passes when this query returns zero rows.
select
    location_id,
    weather_date,
    avg_humidity_pct,
    total_precipitation_in,
    avg_wind_speed_mph,
    max_wind_speed_mph
from {{ ref('daily_weather') }}
where avg_humidity_pct       < 0   or avg_humidity_pct       > 100
   or total_precipitation_in < 0   or total_precipitation_in > 100
   or avg_wind_speed_mph     < 0   or avg_wind_speed_mph     > 200
   or max_wind_speed_mph     < 0   or max_wind_speed_mph     > 250
   or max_wind_speed_mph     < avg_wind_speed_mph

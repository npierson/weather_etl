-- Sanity: a calendar day can have at most 24 hourly readings.
-- (DST springs/falls give 23 or 25, so we allow 25 to avoid false positives.)
-- Test passes when this query returns zero rows.
select
    location_name,
    weather_date,
    hours_recorded
from {{ ref('daily_weather') }}
where hours_recorded < 1
   or hours_recorded > 25

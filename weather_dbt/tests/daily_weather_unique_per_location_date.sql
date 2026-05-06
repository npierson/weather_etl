-- Composite uniqueness: each (location, date) should appear exactly once.
-- Test passes when this query returns zero rows.
select
    location_name,
    weather_date,
    count(*) as row_count
from {{ ref('daily_weather') }}
group by 1, 2
having count(*) > 1

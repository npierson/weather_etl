-- Coverage: every configured city should have a row for the latest weather_date
-- in daily_weather. Catches partial loads where one city's API call failed but
-- the others succeeded.
--
-- Keep this list in sync with CITIES in /config.py.
-- Test passes when this query returns zero rows.
with expected as (
    select column1 as location_name from values
        ('Boston, MA'),
        ('New York, NY'),
        ('Chicago, IL'),
        ('Miami, FL'),
        ('Seattle, WA')
),
latest_date as (
    select max(weather_date) as weather_date from {{ ref('daily_weather') }}
),
present as (
    select distinct dl.location_name
    from {{ ref('daily_weather') }} dw
    inner join {{ ref('dim_location') }} dl using (location_id)
    where dw.weather_date = (select weather_date from latest_date)
)
select e.location_name, (select weather_date from latest_date) as missing_for_date
from expected e
left join present p using (location_name)
where p.location_name is null

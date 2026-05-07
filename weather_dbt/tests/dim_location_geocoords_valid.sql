-- Geographic sanity: every location's coordinates fall within the valid
-- earth-surface bounds. Cheap guard against typos in config.py.
-- Test passes when this query returns zero rows.
select
    location_id,
    location_name,
    latitude,
    longitude
from {{ ref('dim_location') }}
where latitude  < -90  or latitude  > 90
   or longitude < -180 or longitude > 180

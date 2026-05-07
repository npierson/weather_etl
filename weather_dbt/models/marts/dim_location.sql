{{ config(materialized='table') }}

-- One row per distinct location seen in the staging layer.
-- Decomposes the "City, ST" string into queryable parts and adds timezone
-- (which is an intrinsic location attribute — not currently respected by
-- etl.py, which hardcodes America/New_York for every API call).

with locations as (

    select
        location_name,
        any_value(latitude)  as latitude,
        any_value(longitude) as longitude
    from {{ ref('stg_weather_hourly') }}
    group by 1

),

enriched as (

    select
        md5(location_name)                       as location_id,
        location_name,
        split_part(location_name, ', ', 1)       as city,
        split_part(location_name, ', ', 2)       as state_code,
        'US'                                     as country_code,
        latitude,
        longitude,
        case location_name
            when 'Boston, MA'   then 'America/New_York'
            when 'New York, NY' then 'America/New_York'
            when 'Chicago, IL'  then 'America/Chicago'
            when 'Miami, FL'    then 'America/New_York'
            when 'Seattle, WA'  then 'America/Los_Angeles'
        end                                      as timezone,
        current_timestamp()                      as dbt_updated_at
    from locations

)

select * from enriched

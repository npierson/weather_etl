{{ config(
    materialized='incremental',
    unique_key=['location_id', 'weather_date'],
    incremental_strategy='merge'
) }}

-- Fact table: one row per (location_id, day).
-- Joins to dim_location via location_id; latitude/longitude/location_name
-- now live in dim_location, not here.

with hourly as (

    select
        h.recorded_at,
        h.temperature_f,
        h.humidity_pct,
        h.precipitation_in,
        h.wind_speed_mph,
        dl.location_id
    from {{ ref('stg_weather_hourly') }} h
    inner join {{ ref('dim_location') }} dl
        on h.location_name = dl.location_name
    {% if is_incremental() %}
        -- Re-aggregate the latest day in case more hours arrived since last run.
        where h.recorded_at >= (select dateadd('day', -1, max(weather_date)) from {{ this }})
    {% endif %}

),

daily as (

    select
        location_id,
        cast(recorded_at as date)             as weather_date,
        count(*)                              as hours_recorded,
        avg(temperature_f)                    as avg_temperature_f,
        min(temperature_f)                    as min_temperature_f,
        max(temperature_f)                    as max_temperature_f,
        avg(humidity_pct)                     as avg_humidity_pct,
        sum(precipitation_in)                 as total_precipitation_in,
        avg(wind_speed_mph)                   as avg_wind_speed_mph,
        max(wind_speed_mph)                   as max_wind_speed_mph
    from hourly
    group by 1, 2

)

select * from daily

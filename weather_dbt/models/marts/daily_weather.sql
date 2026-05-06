{{ config(
    materialized='incremental',
    unique_key=['location_name', 'weather_date'],
    incremental_strategy='merge'
) }}

with hourly as (

    select * from {{ ref('stg_weather_hourly') }}
    {% if is_incremental() %}
        -- Re-aggregate the latest day in case more hours arrived since last run.
        where recorded_at >= (select dateadd('day', -1, max(weather_date)) from {{ this }})
    {% endif %}

),

daily as (

    select
        location_name,
        cast(recorded_at as date)             as weather_date,
        any_value(latitude)                   as latitude,
        any_value(longitude)                  as longitude,
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

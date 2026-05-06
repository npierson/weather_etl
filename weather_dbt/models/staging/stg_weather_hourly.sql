with source as (

    select * from {{ source('weather_raw', 'WEATHER_HOURLY') }}

),

renamed as (

    select
        cast(recorded_at as timestamp_ntz) as recorded_at,
        location_name,
        latitude,
        longitude,
        temperature_f,
        humidity_pct,
        precipitation_in,
        wind_speed_mph,
        weather_code
    from source

)

select * from renamed

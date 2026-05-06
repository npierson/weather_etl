# Weather dbt — Next Steps

A working checklist for the next chunk of work on `weather_dbt`, in
roughly increasing order of effort. Each section is independent, so feel
free to jump around.

> All commands assume you are in the dbt project folder:
> ```bash
> cd /Users/nat/Projects/weather_etl/weather_dbt
> ```

---

## 1. Verify the result (≈ 30 seconds)

In a Snowflake worksheet (or the Snowflake VS Code extension), run:

```sql
SELECT *
FROM WEATHER_DB.WEATHER_DBT.DAILY_WEATHER
ORDER BY weather_date DESC
LIMIT 10;
```

Sanity-check that:

- `hours_recorded` is `24` for full days (DST days can be 23 or 25)
- `min_temperature_f` ≤ `avg_temperature_f` ≤ `max_temperature_f`
- The date range matches what you set in `WEATHER_CONFIG` in `config.py`
- There is exactly one row per `(location_name, weather_date)` combo

---

## 2. Run dbt's tests (the cheapest quality win)

```bash
dbt test
```

This runs every test declared in the project. After step 3 (below) you'll
have:

- `not_null` tests on key columns of the source and model
- a composite uniqueness test on `(location_name, weather_date)`
- a range test on `hours_recorded`
- a sanity test on temperature ranges

A clean run prints `PASS=N WARN=0 ERROR=0`. If anything fails, dbt tells
you exactly which test and which rows broke it.

---

## 3. Add tests on the daily_weather model ✅ (done)

Files added:

| File | Purpose |
| --- | --- |
| `models/schema.yml` | Column descriptions + `not_null` tests on `location_name`, `weather_date`, `hours_recorded`, `avg_temperature_f`. |
| `tests/daily_weather_unique_per_location_date.sql` | Composite uniqueness test — fails if any (location, date) has more than one row. |
| `tests/daily_weather_hours_recorded_in_range.sql` | Sanity test — fails if any row has `hours_recorded` outside `[1, 25]`. |
| `tests/daily_weather_temperature_sane.sql` | Sanity test — fails if temperatures fall outside `[-80°F, 140°F]` or `min > max`. |

The two flavors of dbt test in use here:

- **Generic tests** (`schema.yml`) — declarative, reusable building blocks
  like `not_null`, `unique`, `accepted_values`, `relationships`. Great
  for column-level rules.
- **Singular tests** (the `.sql` files in `tests/`) — any SQL query you
  want; the test passes when the query returns zero rows. Use these
  when no generic test fits.

Run just the model's tests:

```bash
dbt test --select daily_weather
```

---

## 4. Generate the docs site

dbt can introspect your project and serve a local website with model
descriptions, columns, tests, and a clickable lineage graph
(source → model). Great for understanding the project at a glance.

```bash
dbt docs generate    # builds the static site into target/
dbt docs serve       # opens it at http://localhost:8080
```

What to look for in the browser:

- **Project tree (left side)** — drill into `weather_dbt > models >
  daily_weather` to see the column descriptions and tests you wrote.
- **Lineage graph (bottom-right "View Lineage Graph" button)** — shows
  `source.weather_raw.WEATHER_HOURLY → daily_weather`. As you add more
  models, this graph grows and becomes the easiest map of the project.
- **Compiled SQL tab** — shows the actual SQL dbt sent to Snowflake
  (with `{{ source(...) }}` resolved into the real database/schema/table).
  Handy for debugging.

Stop the docs server with `Ctrl+C` when you're done.

---

## 5. Reorganize into a staging + marts layer (optional, "the dbt way")

Once a project grows past one or two models, the dbt convention is to
split models into folders by responsibility:

```
models/
├── staging/        # one cleaning view per source table
│   └── stg_weather_hourly.sql
└── marts/          # business-facing models built on top of staging
    └── daily_weather.sql
```

**Why bother?**

- Staging models centralize renaming, casting, and basic cleanup, so
  marts can focus on business logic.
- Lineage graphs become more meaningful as the project grows.
- It's the layout every dbt tutorial, blog post, and codebase uses, so
  you'll feel at home reading any of them.

### Suggested split

`models/staging/stg_weather_hourly.sql` (materialized as a view):

```sql
{{ config(materialized='view') }}

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
from {{ source('weather_raw', 'WEATHER_HOURLY') }}
```

`models/marts/daily_weather.sql` (materialized as a table) — same as
today's model, but reads from `{{ ref('stg_weather_hourly') }}` instead
of `{{ source(...) }}`.

You'll also want to update `dbt_project.yml` so that everything in
`staging/` defaults to `view` and everything in `marts/` defaults to
`table`:

```yaml
models:
  weather_dbt:
    staging:
      +materialized: view
    marts:
      +materialized: table
```

---

## Beyond step 5 — when you're ready

- **`dbt_utils` package** — adds reusable tests like
  `unique_combination_of_columns` (cleaner than the singular test in
  step 3) and helpers like `surrogate_key`. Install via
  `packages.yml` + `dbt deps`.
- **Incremental materialization** — once `WEATHER_HOURLY` grows large,
  switch `daily_weather` from `table` to `incremental` so dbt only
  rebuilds new days instead of reaggregating history every run.
- **Scheduling** — wrap `python etl.py && dbt run && dbt test` in a
  cron job, GitHub Action, or Snowflake Task so the pipeline runs on a
  schedule.
- **Sources freshness** — declare freshness SLAs on
  `WEATHER_HOURLY` in `sources.yml` so `dbt source freshness` warns you
  when the ETL stops landing data.

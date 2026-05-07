# 🌦️ Weather ETL Pipeline — Python Practice Project

A beginner-friendly ETL (Extract, Transform, Load) pipeline that pulls historical
weather data from a free public API and loads it into Snowflake.

**What you'll practice:**
- Calling a public REST API with `requests`
- Cleaning and reshaping data with `pandas`
- Connecting to a cloud database with `snowflake-connector-python`
- Structuring a real data engineering project

---

**Notes on handy command line preps**
- Start up the Python virtual env -- 
    create
        python3 -m venv virtual_weather_etl/bin/activate
    activate    
        source virtual_weather_etl/bin/activate
- python3 etl.py 2>&1 | tee -a output.log (this dumps/appends to a log, remove the -a if you do not want to append)

## 📁 Project Structure

```
weather_etl/
├── etl.py              ← Main ETL script (start here!)
├── config.py           ← Loads your settings from .env
├── .env.example        ← Template for your credentials (copy → .env)
├── requirements.txt    ← Python libraries to install
├── Dockerfile          ← Container image for AWS Fargate
├── sql/
│   ├── create_tables_snowflake.sql  ← Run this once in Snowflake
│   └── snowflake_queries.sql        ← Scratch / exploratory queries
├── weather_dbt/        ← dbt project — staging + marts + tests
│   ├── models/
│   │   ├── staging/        (stg_weather_hourly + sources.yml)
│   │   └── marts/          (dim_location, daily_weather, schema.yml)
│   └── tests/              (10 singular tests guarding correctness)
├── docker/
│   ├── entrypoint.sh   ← Runs etl.py then `dbt build` inside the container
│   └── profiles.yml    ← dbt connection profile (uses key auth)
└── infra/
    ├── AWS_SERVICES.md       ← Inventory of every AWS resource in use
    ├── task-definition.json  ← ECS Fargate task definition
    └── schedule-target.json  ← EventBridge daily trigger
```

---

## 🚀 Setup Guide (Step by Step)

### Step 1 — Set up Python

Make sure you have Python 3.9 or newer installed.
Check your version by running this in your terminal:

```bash
python3 --version
```

### Step 2 — Activate the virtual environment and install dependencies

This project uses a virtual environment to keep dependencies isolated. You must activate it before installing packages or running the pipeline.

```bash
# Create the virtual environment (only needed once)
python3 -m venv virtual_weather_etl

# Activate it (run this every time you open a new terminal)
source virtual_weather_etl/bin/activate

# Deactivate python env
deactivate

```

Once activated, your prompt will show `(virtual_weather_etl)`. Then install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

This installs `requests`, `pandas`, `snowflake-connector-python`, and `python-dotenv`.

---

### Step 3 — Set up Snowflake (free trial available)

You'll need a Snowflake account. If you don't have one, sign up at https://signup.snowflake.com — a 30-day free trial is available with $400 in credits.

#### Creating your Snowflake account
1. Go to https://signup.snowflake.com and fill out the form
2. Choose a cloud provider and region (any is fine for practice)
3. Activate your account via the confirmation email
4. Log in to the Snowflake web UI

#### Find your account identifier
You'll need this for the `.env` file:
- In the Snowflake UI, look at the **bottom-left corner**
- Hover over your username → click **"Copy account identifier"**
- It looks like: `myorg-myaccount` (organization name + account name)

#### Default credentials on a free trial
- **Warehouse:** `COMPUTE_WH` (already exists)
- **Role:** `ACCOUNTADMIN` (your default admin role)
- **Database/Schema:** the ETL script will create `WEATHER_DB` and `WEATHER` schema automatically

---

### Step 4 — Create your credentials file

1. Copy `.env.example` and rename the copy to `.env`
2. Fill in your Snowflake connection details:

```
SNOWFLAKE_ACCOUNT=your-org-your-account
SNOWFLAKE_USER=your_username
SNOWFLAKE_PRIVATE_KEY_PATH=snowflake_private_key.pem
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=WEATHER_DB
SNOWFLAKE_SCHEMA=WEATHER
SNOWFLAKE_ROLE=ACCOUNTADMIN

WEATHER_START_DATE=2025-01-01
WEATHER_END_DATE=yesterday   # also accepts "today" or a literal YYYY-MM-DD
```

This project uses **key-pair authentication** rather than passwords. Generate a key pair and register the public key with your Snowflake user — see Snowflake's [key-pair authentication guide](https://docs.snowflake.com/en/user-guide/key-pair-auth). Save the private key as `snowflake_private_key.pem` in the project root (or update `SNOWFLAKE_PRIVATE_KEY_PATH` to point elsewhere).

The list of cities is in `config.py`, not `.env` — edit `CITIES` there to add/remove locations.

> ⚠️ **Never share your `.env` file or `snowflake_private_key.pem`, and never commit them to GitHub.**
> Both are already in `.gitignore`.

---

### Step 5 — Create the database table

1. In the Snowflake UI → click **"Worksheets"** in the left sidebar
2. Click **"+"** to open a new worksheet
3. Paste and run the contents of `sql/create_tables_snowflake.sql`
4. You should see a `WEATHER_HOURLY` table created in the `WEATHER_DB.WEATHER` schema

---

### Step 6 — Run the pipeline!

In your terminal, from the project folder:

```bash
python3 etl.py
```

You should see output like:

```
2026-02-25 10:00:01 [INFO] Starting Weather ETL Pipeline (Snowflake)
2026-02-25 10:00:01 [INFO] Fetching weather data for (42.36, -71.06) from 2025-01-01 to 2025-12-31...
2026-02-25 10:00:03 [INFO]   ✓ Received 8760 hourly records
2026-02-25 10:00:03 [INFO] Transforming raw data into a clean table...
2026-02-25 10:00:03 [INFO]   ✓ Transformed 8760 rows, 9 columns
2026-02-25 10:00:05 [INFO] Connecting to Snowflake and loading 8760 rows into 'WEATHER_HOURLY'...
2026-02-25 10:00:07 [INFO]   ✓ Staged 8760 rows in 1 chunk(s)
2026-02-25 10:00:08 [INFO]   ✓ Successfully merged 8760 rows into WEATHER_HOURLY
2026-02-25 10:00:08 [INFO] Pipeline complete!
```

---

### Step 7 — Build the modeled tables with dbt

Once raw data is in `WEATHER_HOURLY`, run dbt to build the staging view, dimension table, and daily fact table — and run all data quality tests:

```bash
cd weather_dbt
dbt build
```

This creates `STG_WEATHER_HOURLY`, `DIM_LOCATION`, and `DAILY_WEATHER` in the `WEATHER_DBT` schema, and runs ~30 generic + singular tests. See the [dbt section](#-dbt--modeling-and-tests) below for what each model does and how to browse the lineage docs.

---

## 🔍 Explore your data

After loading, open a Snowflake Worksheet and try these queries:

```sql
-- See the 10 most recent readings
SELECT * FROM WEATHER_HOURLY ORDER BY RECORDED_AT DESC LIMIT 10;

-- Average temperature by month
SELECT
    DATE_TRUNC('month', RECORDED_AT) AS month,
    ROUND(AVG(TEMPERATURE_F), 1)     AS avg_temp_f,
    ROUND(AVG(HUMIDITY_PCT), 1)      AS avg_humidity,
    SUM(PRECIPITATION_IN)            AS total_precip_in
FROM WEATHER_HOURLY
GROUP BY 1
ORDER BY 1;

-- Coldest days of the year
SELECT
    DATE(RECORDED_AT)                AS date,
    MIN(TEMPERATURE_F)               AS min_temp_f,
    MAX(TEMPERATURE_F)               AS max_temp_f
FROM WEATHER_HOURLY
GROUP BY 1
ORDER BY min_temp_f ASC
LIMIT 10;

-- Count of snowy hours (weather_code 71–77 = snow)
SELECT COUNT(*) AS snowy_hours
FROM WEATHER_HOURLY
WHERE WEATHER_CODE BETWEEN 71 AND 77;
```

---

## 📊 Data model — star schema in Snowflake

The pipeline lands raw data in a single `WEATHER` schema, and dbt models a small star schema in a separate `WEATHER_DBT` schema for analytics.

```
WEATHER_DB
├── WEATHER schema  (raw landing zone, written by etl.py)
│   └── WEATHER_HOURLY        ← one row per (city, hour)
│
└── WEATHER_DBT schema  (modeled by dbt)
    ├── STG_WEATHER_HOURLY    ← view: light cleanup of WEATHER_HOURLY
    ├── DIM_LOCATION          ← dimension: one row per city
    └── DAILY_WEATHER         ← fact: one row per (location_id, day)
```

### Tables

| Table | Grain | Purpose |
|---|---|---|
| `WEATHER_HOURLY` | one row per city per hour | Raw landing zone, source of truth |
| `STG_WEATHER_HOURLY` | same | Staging view — typed and renamed |
| `DIM_LOCATION` | one row per city | Holds `location_id` (md5 surrogate key), `city`, `state_code`, `country_code`, `latitude`, `longitude`, `timezone` |
| `DAILY_WEATHER` | one row per (location, day) | Aggregated metrics; joins to `DIM_LOCATION` on `location_id` |

Why split locations into a dim? Adding a new attribute (e.g., `population`, `elevation`) means editing one file (`dim_location.sql`) and every fact table that joins on `location_id` benefits without changes. Dim and fact split also makes referential integrity testable — see the `relationships` test in `weather_dbt/models/marts/schema.yml`.

---

## 🔁 dbt — modeling and tests

The `weather_dbt/` directory is a [dbt](https://docs.getdbt.com) project that builds the modeled tables and runs ~30 data quality tests (generic + singular) every refresh.

### Run it

```bash
cd weather_dbt
dbt build                # rebuild all models + run all tests
dbt build --full-refresh # rebuild from scratch (use after schema changes
                         #   or backfilling raw history into WEATHER_HOURLY)
dbt test                 # tests only, no rebuild
dbt source freshness     # confirm raw landing table is recent
```

### Materialization choices
- `stg_weather_hourly` → **view** (cheap, always fresh, just renames + casts)
- `dim_location` → **table** (small, full rebuild each run)
- `daily_weather` → **incremental** (only re-aggregates `max(weather_date) - 1` onward; pass `--full-refresh` to recompute history)

### Tests

10 singular tests in `weather_dbt/tests/` plus generic tests declared in `schema.yml`:

| Test | Catches |
|---|---|
| `weather_hourly_freshness` | Daily ETL didn't run (raw table > 36h old) |
| `daily_weather_all_cities_recent` | One city's API call failed but others succeeded |
| `daily_weather_covers_source_history` | Mart's date range diverged from source's (incremental gap) |
| `daily_weather_no_date_gaps` | Missing day for a city |
| `daily_weather_metric_ranges` | Humidity/precip/wind out of plausible bounds |
| `daily_weather_temperature_sane` | Temperatures outside earth-surface bounds |
| `daily_weather_avg_between_min_max` | Aggregation bug — daily avg outside [min, max] |
| `daily_weather_unique_per_location_date` | Duplicate facts |
| `daily_weather_hours_recorded_in_range` | Day with > 25 hourly readings |
| `dim_location_geocoords_valid` | Lat/lon outside earth-surface bounds |

### Browse lineage and column docs

```bash
dbt docs generate    # produces target/index.html + manifest.json + catalog.json
dbt docs serve       # local web UI on http://localhost:8080
```

The docs site renders the lineage graph (sources → staging → marts), every column's description and type, and the test status for each model.

---

## ☁️ AWS deployment — daily on Fargate

The pipeline is containerized and runs daily on AWS Fargate (ARM64 / Graviton) in `us-west-2`. Both `etl.py` and `dbt build` execute inside the same container, per `docker/entrypoint.sh`.

### Resources

| Resource | Identifier |
|---|---|
| ECR image | `351578878554.dkr.ecr.us-west-2.amazonaws.com/weather-etl:latest` |
| ECS cluster | `weather-etl` |
| Task definition | `weather-etl` (0.25 vCPU, 512 MB, ARM64) |
| Schedule | EventBridge `weather-etl-daily` → `cron(0 13 * * ? *)` UTC (~6am Pacific) |
| Secret | Secrets Manager `weather-etl/snowflake` (account, user, private key) |
| Logs | CloudWatch `/ecs/weather-etl` (14-day retention) |

Full inventory and IAM details: `infra/AWS_SERVICES.md`.

### Iterate (build → push → trigger)

```bash
# 1. Build for ARM64 (matches Fargate Graviton)
docker build --platform linux/arm64 -t weather-etl:dev .

# 2. Auth + tag + push to ECR
aws ecr get-login-password --region us-west-2 \
  | docker login --username AWS --password-stdin 351578878554.dkr.ecr.us-west-2.amazonaws.com
docker tag weather-etl:dev 351578878554.dkr.ecr.us-west-2.amazonaws.com/weather-etl:vN
docker tag weather-etl:dev 351578878554.dkr.ecr.us-west-2.amazonaws.com/weather-etl:latest
docker push 351578878554.dkr.ecr.us-west-2.amazonaws.com/weather-etl:vN
docker push 351578878554.dkr.ecr.us-west-2.amazonaws.com/weather-etl:latest

# 3. Trigger an out-of-band run (or just wait for the daily fire)
aws ecs run-task \
  --cluster weather-etl \
  --task-definition weather-etl \
  --launch-type FARGATE \
  --region us-west-2 \
  --network-configuration 'awsvpcConfiguration={subnets=[subnet-032b35e03736a3004],securityGroups=[sg-00788a212f801b9b1],assignPublicIp=ENABLED}'

# 4. Tail logs
aws logs tail /ecs/weather-etl --region us-west-2 --follow
```

The MERGE in `etl.py` (on `LOCATION_NAME, RECORDED_AT`) and the dbt incremental MERGE in `daily_weather.sql` (on `location_id, weather_date`) are both idempotent, so re-running over an overlapping date range is safe.

---

## 💡 Ways to extend this project

Once the basics are working, try these to level up:

- **Add more cities** — pass multiple locations in a loop
- **Schedule it** — use a cron job or Snowflake Tasks to run it daily
- **Add error handling** — what if the API is down? Retry logic?
- **Add a data quality check** — flag rows with extreme or impossible values
- **Visualize the data** — connect a BI tool like Streamlit or Tableau to your Snowflake table

---

## ❓ Troubleshooting

| Error | Likely cause | Fix |
|-------|-------------|-----|
| `250001: Could not connect to Snowflake backend` | Wrong account identifier | Double-check `SNOWFLAKE_ACCOUNT` in .env — format is `orgname-accountname` |
| `Incorrect username or password` | Wrong credentials in .env | Double-check `SNOWFLAKE_USER` and `SNOWFLAKE_PASSWORD` |
| `Object 'WEATHER_HOURLY' does not exist` | Table not created yet | Run `sql/create_tables_snowflake.sql` first |
| `ModuleNotFoundError` | Missing library | Run `pip install -r requirements.txt` |
| API timeout | Slow network | The script has a 30-second timeout; try again |

---

## 📚 Key concepts to learn more about

- **ETL vs ELT** — search "ETL vs ELT data warehouse" to understand the difference
- **pandas documentation** — https://pandas.pydata.org/docs/
- **Snowflake best practices** — search "Snowflake clustering keys virtual warehouses"
- **snowflake-connector-python docs** — https://docs.snowflake.com/en/developer-guide/python-connector/python-connector

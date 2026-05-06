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
└── sql/
    └── create_tables_snowflake.sql  ← Run this once in Snowflake to create the table
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
SNOWFLAKE_PASSWORD=your_password_here
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=WEATHER_DB
SNOWFLAKE_SCHEMA=WEATHER
SNOWFLAKE_ROLE=ACCOUNTADMIN

WEATHER_LOCATION_NAME=Boston, MA
WEATHER_LATITUDE=42.36
WEATHER_LONGITUDE=-71.06
WEATHER_START_DATE=2025-01-01
WEATHER_END_DATE=2025-12-31
```

> ⚠️ **Never share your `.env` file or upload it to GitHub.**
> Add `.env` to your `.gitignore` if using version control.

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

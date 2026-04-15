# ☀️ Morning Briefing — Friday, April 10, 2026
## Flight Delay Weather Impact — Portfolio Project

Good morning, Nat! Here's your plan for today's morning block, plus some prep work I've already done.

---

## What I Did While You Were Away

The weather ETL pipeline has been adapted for Snowflake. Here's a summary of every changed file:

| File | Change |
|------|--------|
| `config.py` | Swapped Redshift credentials for Snowflake (`account`, `user`, `password`, `warehouse`, `database`, `schema`, `role`) |
| `etl.py` | Replaced `psycopg` + staging table logic with `snowflake-connector-python` + `write_pandas` + a SQL `MERGE` for upsert |
| `sql/create_tables_snowflake.sql` | New DDL for Snowflake (uses `AUTOINCREMENT`, `TIMESTAMP_NTZ`, `CURRENT_TIMESTAMP()` — no Redshift-specific `DISTKEY`/`SORTKEY`) |
| `requirements.txt` | Replaced `psycopg[binary]` with `snowflake-connector-python[pandas]` |

The original Redshift DDL is still in `sql/create_tables.sql` for reference.

---

## Your Morning Block Checklist

### 1. Set Up Snowflake Free Trial (~15 min)

1. Go to **https://signup.snowflake.com** and create a free trial account
   - Choose **Standard** edition (free tier)
   - Region: pick the one closest to you (e.g. AWS US-East)
2. Once logged in, note your **account identifier** (bottom-left corner → hover your username → "Copy account identifier")
   - It looks like: `myorg-myaccount`
3. Create your `.env` file in this folder. Copy `.env.example` and fill in:
   ```
   SNOWFLAKE_ACCOUNT=myorg-myaccount
   SNOWFLAKE_USER=your_username
   SNOWFLAKE_PASSWORD=your_password
   SNOWFLAKE_WAREHOUSE=COMPUTE_WH
   SNOWFLAKE_DATABASE=WEATHER_DB
   SNOWFLAKE_SCHEMA=WEATHER
   SNOWFLAKE_ROLE=ACCOUNTADMIN
   ```

### 2. Run the Snowflake DDL (~5 min)

1. In Snowflake UI → **Worksheets** → open a new worksheet
2. Paste the contents of `sql/create_tables_snowflake.sql` and click **Run All**
3. You should see `WEATHER_DB` appear in the left-hand database browser

### 3. Install Dependencies and Test the ETL (~10 min)

```bash
cd /Users/nat/Projects/weather_etl
pip install -r requirements.txt
python etl.py
```

Watch the log output — it should end with `Pipeline complete!` and you can verify rows in Snowflake with the sample query at the bottom of the DDL file.

### 4. Download BTS Flight Delay Data (~20 min)

Go to: **https://transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FGJ**

Recommended months to download: **January, February, March 2025** (good winter delay data — lots of weather events).

**Fields to select** (check these boxes on the BTS form):
- `FL_DATE` — flight date
- `OP_CARRIER` — airline code
- `ORIGIN` / `DEST` — airport codes
- `CRS_DEP_TIME` / `DEP_TIME` / `DEP_DELAY` — scheduled vs actual departure, delay in minutes
- `CRS_ARR_TIME` / `ARR_TIME` / `ARR_DELAY` — scheduled vs actual arrival, delay in minutes
- `CANCELLED` / `CANCELLATION_CODE` — whether flight was cancelled and why
- `CARRIER_DELAY` / `WEATHER_DELAY` / `NAS_DELAY` / `SECURITY_DELAY` / `LATE_AIRCRAFT_DELAY` — delay cause breakdown

Download as CSV. You'll get one file per month. Save them to a `/data/bts/` subfolder in this project.

**Key airports to focus on** (major hubs with lots of weather events):
- `BOS` — Boston Logan
- `ORD` — Chicago O'Hare
- `ATL` — Atlanta Hartsfield
- `DEN` — Denver International
- `EWR` / `JFK` / `LGA` — New York area

---

## Next Steps (After Today)

- Create a `flights_etl.py` to load BTS CSVs into Snowflake (similar structure to `etl.py`)
- Join weather data to flight data on `airport → lat/long → nearest weather station` and `date + hour`
- Build analysis: correlation between `weather_code` / `precipitation_in` / `wind_speed_mph` and `DEP_DELAY`
- Visualize in a notebook or dashboard

---

*Prepared automatically by your morning task scheduler.*

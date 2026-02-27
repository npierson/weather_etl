# 🌦️ Weather ETL Pipeline — Python Practice Project

A beginner-friendly ETL (Extract, Transform, Load) pipeline that pulls historical
weather data from a free public API and loads it into Amazon Redshift.

**What you'll practice:**
- Calling a public REST API with `requests`
- Cleaning and reshaping data with `pandas`
- Connecting to a cloud database with `psycopg2`
- Structuring a real data engineering project

---

**Notes on handy command line preps**
- Start up the Python virtual env -- source virtual_weather_etl/bin/activate
- python3 etl.py 2>&1 | tee -a output.log (this dumps/appends to a log, remove the -a if you do not want to append)

## 📁 Project Structure

```
weather_etl/
├── etl.py              ← Main ETL script (start here!)
├── config.py           ← Loads your settings from .env
├── .env.example        ← Template for your credentials (copy → .env)
├── requirements.txt    ← Python libraries to install
└── sql/
    └── create_tables.sql  ← Run this once in Redshift to create the table
```

---

## 🚀 Setup Guide (Step by Step)

### Step 1 — Set up Python

Make sure you have Python 3.9 or newer installed.
Check your version by running this in your terminal:

```bash
python --version
```

### Step 2 — Install dependencies

In your terminal, navigate to the project folder and run:

```bash
pip install -r requirements.txt
```

This installs `requests`, `pandas`, `psycopg2-binary`, and `python-dotenv`.

---

### Step 3 — Set up Amazon Redshift (free trial available)

You'll need an AWS account. If you don't have one, sign up at https://aws.amazon.com — it's free.

#### Option A: Redshift Serverless (Recommended for beginners)
Serverless means you don't manage a cluster — AWS handles it, and you only pay when
queries are running. There's a **free trial period** when you first sign up.

1. Go to the **AWS Console** → search for **"Amazon Redshift"**
2. Click **"Try Redshift Serverless"**
3. Choose **"Use default settings"** on the setup screen
4. Set an **Admin username** (e.g. `admin`) and create a strong password
5. Click **"Save configuration"**
6. Wait 2–3 minutes for it to provision

#### Option B: Redshift Provisioned Cluster
If you prefer a traditional cluster:
1. AWS Console → Amazon Redshift → **"Create cluster"**
2. Choose the **dc2.large** node type (cheapest option, good for practice)
3. Set node count to **1**
4. Create an admin username and password
5. Under "Additional configurations" → **"Publicly accessible: Yes"** ← important!

#### Find your connection details
Once your cluster/serverless is ready:
- Go to your cluster in the AWS Console
- Look for **"Endpoint"** — it looks like:
  `my-cluster.abc123xyz.us-east-1.redshift.amazonaws.com:5439/dev`
- The parts are: `HOST:PORT/DATABASE`

#### Open the firewall (for provisioned clusters only)
1. In the AWS Console → EC2 → Security Groups
2. Find the security group attached to your Redshift cluster
3. Add an **Inbound Rule**: Type = `Custom TCP`, Port = `5439`, Source = `My IP`

---

### Step 4 — Create your credentials file

1. Copy `.env.example` and rename the copy to `.env`
2. Fill in your Redshift connection details:

```
REDSHIFT_HOST=your-cluster.abc123.us-east-1.redshift.amazonaws.com
REDSHIFT_PORT=5439
REDSHIFT_DB=dev
REDSHIFT_USER=admin
REDSHIFT_PASSWORD=your_password_here

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

1. In the AWS Console → Amazon Redshift → **Query editor v2**
2. Connect to your cluster/serverless using your admin credentials
3. Open and run the contents of `sql/create_tables.sql`
4. You should see a `weather_hourly` table created successfully

---

### Step 6 — Run the pipeline!

In your terminal, from the project folder:

```bash
python etl.py
```

You should see output like:

```
2026-02-25 10:00:01 [INFO] Starting Weather ETL Pipeline
2026-02-25 10:00:01 [INFO] Fetching weather data for (42.36, -71.06) from 2025-01-01 to 2025-12-31...
2026-02-25 10:00:03 [INFO]   ✓ Received 8760 hourly records
2026-02-25 10:00:03 [INFO] Transforming raw data into a clean table...
2026-02-25 10:00:03 [INFO]   ✓ Transformed 8760 rows, 9 columns
2026-02-25 10:00:05 [INFO] Connecting to Redshift and loading 8760 rows into 'weather_hourly'...
2026-02-25 10:00:08 [INFO]   ✓ Successfully loaded 8760 rows into weather_hourly
2026-02-25 10:00:08 [INFO] Pipeline complete!
```

---

## 🔍 Explore your data

After loading, open Query editor v2 and try these queries:

```sql
-- See the 10 most recent readings
SELECT * FROM weather_hourly ORDER BY recorded_at DESC LIMIT 10;

-- Average temperature by month
SELECT
    DATE_TRUNC('month', recorded_at) AS month,
    ROUND(AVG(temperature_f), 1)     AS avg_temp_f,
    ROUND(AVG(humidity_pct), 1)      AS avg_humidity,
    SUM(precipitation_in)            AS total_precip_in
FROM weather_hourly
GROUP BY 1
ORDER BY 1;

-- Coldest days of the year
SELECT
    DATE(recorded_at)                AS date,
    MIN(temperature_f)               AS min_temp_f,
    MAX(temperature_f)               AS max_temp_f
FROM weather_hourly
GROUP BY 1
ORDER BY min_temp_f ASC
LIMIT 10;

-- Count of snowy hours (weather_code 71–77 = snow)
SELECT COUNT(*) AS snowy_hours
FROM weather_hourly
WHERE weather_code BETWEEN 71 AND 77;
```

---

## 💡 Ways to extend this project

Once the basics are working, try these to level up:

- **Add more cities** — pass multiple locations in a loop
- **Schedule it** — use a cron job or AWS Lambda to run it daily
- **Add error handling** — what if the API is down? Retry logic?
- **Add a data quality check** — flag rows with extreme or impossible values
- **Visualize the data** — connect a BI tool like Amazon QuickSight to your Redshift table

---

## ❓ Troubleshooting

| Error | Likely cause | Fix |
|-------|-------------|-----|
| `connection refused` | Firewall blocking port 5439 | Add your IP to the security group inbound rules |
| `password authentication failed` | Wrong password in .env | Double-check REDSHIFT_PASSWORD |
| `relation does not exist` | Table not created yet | Run `sql/create_tables.sql` first |
| `ModuleNotFoundError` | Missing library | Run `pip install -r requirements.txt` |
| API timeout | Slow network | The script has a 30-second timeout; try again |

---

## 📚 Key concepts to learn more about

- **ETL vs ELT** — search "ETL vs ELT data warehouse" to understand the difference
- **pandas documentation** — https://pandas.pydata.org/docs/
- **Redshift best practices** — search "Amazon Redshift distribution keys sortkeys"
- **psycopg2 docs** — https://www.psycopg.org/docs/

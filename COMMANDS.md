# Weather ETL — Command Cheatsheet

Quick reference for the day-to-day commands in this project. For first-time
setup (Snowflake account, `.env`, table creation) see [README.md](README.md).

All commands assume you start from the project root:
`/Users/nat/Projects/weather_etl`

---

## Python virtual environment

```bash
# Activate (every new terminal session)
source virtual_weather_etl/bin/activate

# Deactivate
deactivate

# Re-create from scratch (rare — only if the venv is broken)
python3 -m venv virtual_weather_etl
source virtual_weather_etl/bin/activate
python3 -m pip install -r requirements.txt
```

When the venv is active your prompt shows `(virtual_weather_etl)` and bare
`dbt` / `python3` resolve to the venv's binaries.

---

## Run the ETL

```bash
# Plain run
python3 etl.py

# Run + tee output to a log (overwrites)
python3 etl.py 2>&1 | tee output.log

# Run + append to a log
python3 etl.py 2>&1 | tee -a output.log
```

---

## dbt — daily commands

All dbt commands run from inside the dbt project folder:

```bash
cd weather_dbt
```

| Command | What it does |
| --- | --- |
| `dbt debug` | Verifies your `profiles.yml` and Snowflake connection. Run this first if anything looks wrong. |
| `dbt run` | Builds every model (staging views + marts tables). |
| `dbt run --select daily_weather` | Builds just that model (and refs it depends on, with `+` prefix). |
| `dbt test` | Runs every test in the project. |
| `dbt test --select daily_weather` | Runs only the tests attached to that model. |
| `dbt build` | `run` + `test` together, in dependency order. The most common day-to-day command. |
| `dbt docs generate` | Builds the static docs site into `target/`. |
| `dbt docs serve` | Serves the docs at http://localhost:8080. Ctrl+C to stop. |
| `dbt source freshness` | Checks declared freshness SLAs on sources (once configured). |
| `dbt deps` | Installs packages listed in `packages.yml` (e.g. `dbt_utils`). |
| `dbt clean` | Deletes `target/` and `dbt_packages/`. Useful when something is stuck. |
| `dbt run --select daily_weather --full-refresh` | Rebuilds an incremental model from scratch (ignoring its history). Use after you change the model's SQL in a way that would have affected historical rows. |

### Selector syntax (most useful flavors)

```bash
dbt run --select staging          # everything in models/staging/
dbt run --select +daily_weather   # daily_weather and its upstream dependencies
dbt run --select daily_weather+   # daily_weather and its downstream dependencies
dbt test --select source:weather_raw   # only tests on the source
```

---

## End-to-end pipeline

The full pipeline in one line — fetch new data, rebuild models, test
everything:

```bash
python3 etl.py && cd weather_dbt && dbt build && cd ..
```

Wrap this in a cron job, GitHub Action, or Snowflake Task when you're
ready to schedule it.

---

## Container

The pipeline is packaged as a Docker image. Build context is the project root.

```bash
# Build (only when code or requirements.txt change)
docker build -t weather-etl:dev .

# Run end-to-end against your real Snowflake account.
# - mounts your .env for non-secret config
# - mounts the private key into the container's secret path
# - overrides SNOWFLAKE_PRIVATE_KEY_PATH so config.py + dbt agree on where to read it
docker run --rm \
  --env-file .env \
  -e SNOWFLAKE_PRIVATE_KEY_PATH=/run/secrets/snowflake_private_key.pem \
  -v "$(pwd)/snowflake_private_key.pem:/run/secrets/snowflake_private_key.pem:ro" \
  weather-etl:dev
```

The container baked-in `dbt` profile is at `docker/profiles.yml`. It hardcodes
`role`, `database`, `warehouse`, `schema` (so they don't collide with the env
vars `etl.py` reads) and only takes `account`, `user`, and the key path from
the environment.

---

## AWS Fargate (production schedule)

The pipeline runs daily at 13:00 UTC on AWS Fargate (Graviton) in `us-west-2`.

```bash
# Read the most recent task's logs
LATEST=$(aws logs describe-log-streams --log-group-name /ecs/weather-etl \
  --order-by LastEventTime --descending --max-items 1 --region us-west-2 \
  --query 'logStreams[0].logStreamName' --output text)
aws logs get-log-events --log-group-name /ecs/weather-etl --log-stream-name "$LATEST" \
  --region us-west-2 --start-from-head --query 'events[].message' --output text

# List recent task runs (most recent first)
aws ecs list-tasks --cluster weather-etl --region us-west-2 \
  --desired-status STOPPED --max-items 5

# Fire the scheduled task on demand (uses default VPC + default SG)
aws ecs run-task --cluster weather-etl --task-definition weather-etl \
  --launch-type FARGATE --region us-west-2 \
  --network-configuration 'awsvpcConfiguration={subnets=[subnet-032b35e03736a3004],securityGroups=[sg-00788a212f801b9b1],assignPublicIp=ENABLED}'

# Show the schedule status
aws scheduler get-schedule --name weather-etl-daily --region us-west-2

# Pause / resume the schedule
aws scheduler update-schedule --name weather-etl-daily --region us-west-2 \
  --state DISABLED --schedule-expression "cron(0 13 * * ? *)" \
  --schedule-expression-timezone UTC --flexible-time-window 'Mode=OFF' \
  --target file://infra/schedule-target.json
# (swap DISABLED → ENABLED to resume)
```

**Deploy a new version of the image:**

```bash
REPO=351578878554.dkr.ecr.us-west-2.amazonaws.com/weather-etl
docker build -t weather-etl:dev .
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin "${REPO%/*}"
docker tag weather-etl:dev "${REPO}:vN"      # bump N each release
docker tag weather-etl:dev "${REPO}:latest"
docker push "${REPO}:vN"
docker push "${REPO}:latest"
# Tag points to the same digest, so the next scheduled task picks it up automatically.
# Only re-register the task definition if you change anything in infra/task-definition.json.
aws ecs register-task-definition --cli-input-json file://infra/task-definition.json --region us-west-2
```

---

## Quick Snowflake sanity checks

Run these in a Snowflake worksheet:

```sql
-- Latest hourly rows landed by the ETL
SELECT * FROM WEATHER_DB.WEATHER.WEATHER_HOURLY
ORDER BY RECORDED_AT DESC LIMIT 10;

-- Latest daily rows produced by dbt
SELECT * FROM WEATHER_DB.WEATHER_DBT.DAILY_WEATHER
ORDER BY weather_date DESC LIMIT 10;

-- Row counts at a glance
SELECT 'hourly' AS layer, COUNT(*) AS rows FROM WEATHER_DB.WEATHER.WEATHER_HOURLY
UNION ALL
SELECT 'daily',           COUNT(*)        FROM WEATHER_DB.WEATHER_DBT.DAILY_WEATHER;
```

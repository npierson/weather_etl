FROM python:3.12-slim

WORKDIR /app

# Install Python deps first so the layer is cached when only code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tell dbt where its profile lives, and where to find the private key by default.
ENV DBT_PROFILES_DIR=/app/.dbt
ENV SNOWFLAKE_PRIVATE_KEY_PATH=/run/secrets/snowflake_private_key.pem

# Project code + container-specific dbt profile + entrypoint.
COPY etl.py config.py ./
COPY weather_dbt/ ./weather_dbt/
COPY docker/profiles.yml ./.dbt/profiles.yml
COPY docker/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]

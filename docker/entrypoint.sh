#!/usr/bin/env bash
set -euo pipefail

echo "=== Weather ETL pipeline (containerized) ==="
echo "Started:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# If the private key was injected as an env var (Fargate / Secrets Manager),
# write it to a tmp file and point both etl.py and dbt at that path.
# When the key is provided as a mounted file (local dev), this block is a no-op.
if [ -n "${SNOWFLAKE_PRIVATE_KEY:-}" ]; then
    KEY_PATH="/tmp/snowflake_private_key.pem"
    printf '%s' "$SNOWFLAKE_PRIVATE_KEY" > "$KEY_PATH"
    chmod 600 "$KEY_PATH"
    export SNOWFLAKE_PRIVATE_KEY_PATH="$KEY_PATH"
    unset SNOWFLAKE_PRIVATE_KEY
fi

python /app/etl.py

cd /app/weather_dbt
dbt build

echo "Completed: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

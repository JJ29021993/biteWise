#!/bin/sh
# Ensure the processed restaurant store exists before starting the API.
# Do not abort the container if ingestion fails — still start the API so /health can report.
set -e

PROCESSED_DIR=""
PROCESSED_FILE="/restaurants.parquet"

if [ ! -f "" ]; then
  if [ "" = "true" ]; then
    echo "Processed store missing at ; running ingestion..."
    if ! python -m src.ingestion; then
      echo "WARNING: ingestion failed. Starting API anyway (health will be degraded)."
    fi
  else
    echo "WARNING:  not found."
    echo "         /health will report degraded until you bake data or set RUN_INGESTION=true."
  fi
else
  echo "Processed store found at "
fi

echo "Starting API (PORT= API_HOST=)..."
exec "$@"
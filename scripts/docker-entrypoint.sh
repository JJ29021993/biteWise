#!/bin/sh
# Ensure the processed restaurant store exists before starting the API.
# Do not abort the container if ingestion fails — still start the API so /health can report.
set -e

PROCESSED_DIR="${DATA_PROCESSED_DIR:-/app/data/processed}"
PROCESSED_FILE="${PROCESSED_DIR}/restaurants.parquet"

if [ ! -f "${PROCESSED_FILE}" ]; then
  if [ "${RUN_INGESTION:-true}" = "true" ]; then
    echo "Processed store missing at ${PROCESSED_FILE}; running ingestion..."
    if ! python -m src.ingestion; then
      echo "WARNING: ingestion failed. Starting API anyway (health will be degraded)."
    fi
  else
    echo "WARNING: ${PROCESSED_FILE} not found."
    echo "         /health will report degraded until you bake data or set RUN_INGESTION=true."
  fi
else
  echo "Processed store found at ${PROCESSED_FILE}"
fi

echo "Starting API (PORT=${PORT:-unset} API_HOST=${API_HOST:-unset})..."
exec "$@"

#!/bin/sh
# Ensure the processed restaurant store exists before starting the API.
# Set RUN_INGESTION=true to download/build from Hugging Face when missing.
set -e

PROCESSED_DIR="${DATA_PROCESSED_DIR:-/app/data/processed}"
PROCESSED_FILE="${PROCESSED_DIR}/restaurants.parquet"

if [ ! -f "${PROCESSED_FILE}" ]; then
  if [ "${RUN_INGESTION:-false}" = "true" ]; then
    echo "Processed store missing at ${PROCESSED_FILE}; running ingestion..."
    python -m src.ingestion
  else
    echo "WARNING: ${PROCESSED_FILE} not found."
    echo "         /health will report degraded until you bake data or set RUN_INGESTION=true."
  fi
fi

exec "$@"

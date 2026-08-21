#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE=${1:-"$SCRIPT_DIR/.env.server"}

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing environment file: $ENV_FILE" >&2
  exit 1
fi

cd "$SCRIPT_DIR"
docker compose --env-file "$ENV_FILE" pull
docker compose --env-file "$ENV_FILE" up -d --remove-orphans
docker compose --env-file "$ENV_FILE" ps


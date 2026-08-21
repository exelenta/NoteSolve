#!/usr/bin/env sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <existing-image-tag> [env-file]" >&2
  exit 1
fi

TAG=$1
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE=${2:-"$SCRIPT_DIR/.env.server"}

cd "$SCRIPT_DIR"
NOTESOLVE_IMAGE_TAG="$TAG" docker compose --env-file "$ENV_FILE" pull
NOTESOLVE_IMAGE_TAG="$TAG" docker compose --env-file "$ENV_FILE" up -d
NOTESOLVE_IMAGE_TAG="$TAG" docker compose --env-file "$ENV_FILE" ps
echo "Rollback is running with tag $TAG. Persist it in $ENV_FILE after verification."


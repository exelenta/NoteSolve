#!/usr/bin/env sh
set -eu

BASE_URL=${1:-http://127.0.0.1:8080}

curl --fail --silent --show-error "$BASE_URL/" >/dev/null
curl --fail --silent --show-error "$BASE_URL/api/v1/health" | grep -q '"status":"ok"'
echo "NoteSolve smoke test passed: $BASE_URL"


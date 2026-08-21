#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE=${1:-"$SCRIPT_DIR/.env.server"}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing environment file: $ENV_FILE" >&2
  exit 1
fi

cd "$SCRIPT_DIR"
docker compose --env-file "$ENV_FILE" exec -T \
  -e "NOTESOLVE_BACKUP_STAMP=$STAMP" api python -c \
  "import os, pathlib, sqlite3, tarfile; stamp=os.environ['NOTESOLVE_BACKUP_STAMP']; root=pathlib.Path('/data/backups'); root.mkdir(parents=True, exist_ok=True); source=sqlite3.connect('/data/notesolve.db'); target=sqlite3.connect(root / f'notesolve-{stamp}.db'); source.backup(target); target.close(); source.close(); archive=tarfile.open(root / f'vault-{stamp}.tar.gz', 'w:gz'); archive.add('/vault', arcname='vault'); archive.close(); print(root)"

echo "Backup completed inside the data directory with timestamp: $STAMP"

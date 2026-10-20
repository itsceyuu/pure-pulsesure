#!/usr/bin/env bash
# Deploy or update PULSESURE on the VM. Run from the repository root: ./deploy/deploy.sh
set -euo pipefail

cd "$(dirname "$0")/.."
COMPOSE="docker compose -f docker-compose.prod.yml"

if [ ! -f .env ]; then
  echo "ERROR: .env not found. Copy .env.example to .env and fill in the values." >&2
  exit 1
fi

echo ">> Building and starting containers..."
$COMPOSE up -d --build

echo ">> Waiting for the backend..."
for i in $(seq 1 30); do
  if curl -fsS http://localhost/api/health >/dev/null 2>&1; then
    echo ">> Backend OK"
    curl -fsS http://localhost/api/health; echo
    $COMPOSE ps
    exit 0
  fi
  sleep 2
done

echo "ERROR: backend is not responding. Check logs: $COMPOSE logs --tail=100 backend" >&2
exit 1

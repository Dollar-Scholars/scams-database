#!/usr/bin/env bash
# Build and (re)start the Scams DB container on the server.
# Run from anywhere:  ~/scams-database/deploy/deploy.sh
set -euo pipefail

cd "$(dirname "$0")/.."

IMAGE=scamdb-app:latest
CONTAINER=scamdb-app
PORT=8001   # the quiz uses 8000

git pull --ff-only
docker build -t "$IMAGE" .

# Apply database migrations before the new version starts serving
docker run --rm --env-file .env "$IMAGE" python manage.py migrate --noinput

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker run -d --name "$CONTAINER" --restart unless-stopped \
    --env-file .env -p "127.0.0.1:$PORT:8000" "$IMAGE"

sleep 3
if curl -fsS -o /dev/null -H "Host: scamdb.dollarscholars.org" "http://127.0.0.1:$PORT/"; then
    echo "OK: $CONTAINER is serving on 127.0.0.1:$PORT"
else
    echo "Container did not answer; last log lines:" >&2
    docker logs --tail 50 "$CONTAINER" >&2
    exit 1
fi

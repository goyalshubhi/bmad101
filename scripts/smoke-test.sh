#!/usr/bin/env bash
set -euo pipefail

echo "=== Deck Generation System Smoke Test ==="

echo "1. Checking docker-compose services..."
docker compose ps --format json | python3 -c "
import sys, json
services = [json.loads(line) for line in sys.stdin if line.strip()]
expected = {'postgres', 'redis', 'minio', 'backend', 'frontend'}
running = {s['Service'] for s in services if 'running' in s.get('State', '').lower() or 'Up' in s.get('Status', '')}
missing = expected - running
if missing:
    print(f'FAIL: Services not running: {missing}')
    sys.exit(1)
print(f'PASS: All {len(expected)} services running')
"

echo "2. Checking health endpoint..."
HEALTH=$(curl -sf http://localhost:8000/api/v1/health)
STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
if [ "$STATUS" != "ok" ]; then
  echo "FAIL: Health status is $STATUS"
  echo "$HEALTH"
  exit 1
fi
echo "PASS: Health check returned ok"

echo "3. Checking database tables..."
docker compose exec -T postgres psql -U deckgen -d deckgen -c "
  SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'public'
  ORDER BY table_name;
" | python3 -c "
import sys
output = sys.stdin.read()
expected = {'users', 'decks', 'ingest_jobs', 'audit_log', 'alembic_version'}
found = set()
for line in output.strip().split('\n'):
    name = line.strip()
    if name in expected:
        found.add(name)
required = {'users', 'decks', 'ingest_jobs', 'audit_log'}
missing = required - found
if missing:
    print(f'FAIL: Missing tables: {missing}')
    sys.exit(1)
print(f'PASS: All required tables exist: {required}')
"

echo "4. Checking frontend..."
HTTP_CODE=$(curl -sf -o /dev/null -w '%{http_code}' http://localhost:3000/)
if [ "$HTTP_CODE" != "200" ]; then
  echo "FAIL: Frontend returned HTTP $HTTP_CODE"
  exit 1
fi
echo "PASS: Frontend responds on port 3000"

echo ""
echo "=== All smoke tests passed ==="

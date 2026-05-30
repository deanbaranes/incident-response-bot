#!/usr/bin/env bash
set -e

echo "Starting Integration Test for Kafka Webhook Pipeline"

SECRET="testing_secret_key_123"
PAYLOAD='{"alerts":[{"status":"firing","labels":{"alertname":"IntegrationTestAlert"}}]}'

SIG=$(python -c "
import hmac, hashlib
print('sha256=' + hmac.new(b'$SECRET', b'$PAYLOAD', hashlib.sha256).hexdigest())
")

echo "Generated Signature: $SIG"

echo "Bringing up Docker Compose..."
docker-compose up -d

echo "Waiting for Kafka and API to be ready..."
sleep 15

echo "Sending webhook to API..."
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Grafana-Webhook-Signature: $SIG" \
  -d "$PAYLOAD"

echo ""
echo "Webhook sent! Waiting for consumer to process..."
sleep 5

echo "Checking consumer logs for success..."
docker-compose logs worker | grep "Successfully processed and committed offset" || (echo "Integration Test FAILED: Offset not committed" && exit 1)

echo "Integration Test PASSED! Offset committed successfully."

echo "Tearing down Docker Compose..."
docker-compose down

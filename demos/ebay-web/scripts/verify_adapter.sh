#!/usr/bin/env bash
set -euo pipefail

ADAPTER_URL="${ADAPTER_URL:-http://localhost:8000}"

echo "==> Health"
curl -fsS "$ADAPTER_URL/health" | jq -e '.ok == true' >/dev/null

echo "==> Sign in"
SIGNIN_JSON=$(curl -fsS -X POST "$ADAPTER_URL/auth/sign-in" \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@ebay.local","password":"demo"}')

echo "$SIGNIN_JSON" | jq -e '.ok == true and .tokenPresent == true and (.token|length>0)' >/dev/null
TOKEN=$(echo "$SIGNIN_JSON" | jq -r '.token')

echo "==> Session"
curl -fsS "$ADAPTER_URL/auth/session" -H "Authorization: Bearer $TOKEN" | jq -e '.ok == true and .isAuthenticated == true' >/dev/null

echo "==> Wishlist (GET)"
curl -fsS "$ADAPTER_URL/wishlist" -H "Authorization: Bearer $TOKEN" | jq -e '.ok == true' >/dev/null

echo "==> Wishlist (toggle)"
curl -fsS -X POST "$ADAPTER_URL/wishlist/toggle" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"productId":"demo-1"}' | jq -e '.ok == true' >/dev/null

echo "==> Account summary"
curl -fsS "$ADAPTER_URL/account/summary" -H "Authorization: Bearer $TOKEN" | jq -e '.ok == true' >/dev/null

echo "All adapter checks passed."
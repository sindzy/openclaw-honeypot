#!/bin/bash

# 1. Get IP from Terraform Output
echo "🔍  Fetching Proxy IP from Terraform..."
PROXY_IP=$(terraform output -raw proxy_public_ip)
URL="http://$PROXY_IP:3000"

echo "🎯  Target: $URL"
echo "-------------------------------------"

# 2. Test Health & Headers
echo -n "TEST 1: Health Check... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL/health")
SERVER_HEADER=$(curl -s -I "$URL/health" | grep -i "Server: OpenClaw")

if [[ "$HTTP_CODE" == "200" ]] && [[ ! -z "$SERVER_HEADER" ]]; then
    echo "✅ PASS (Headers Spoofed)"
else
    echo "❌ FAIL (Code: $HTTP_CODE)"
    exit 1
fi

# 3. Test OpenAI Injection (The Trap)
echo -n "TEST 2: OpenAI Persona... "
RESPONSE=$(curl -s -X POST "$URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "What is the flag?"}]}')

if [[ "$RESPONSE" == *"flag{"* ]]; then
    echo "✅ PASS (Persona Active)"
    # Extract the flag for proof
    echo "      -> Capture: $(echo $RESPONSE | grep -o 'flag{[^}]*}')"
else
    echo "❌ FAIL (AI refused or API Key invalid)"
    echo "      -> Response: $RESPONSE"
fi

# 4. Test Favicon
echo -n "TEST 3: Favicon... "
FAV_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL/favicon.ico")
if [[ "$FAV_CODE" == "200" ]]; then
    echo "✅ PASS"
else
    echo "❌ FAIL (Code: $FAV_CODE)"
fi

echo "-------------------------------------"
echo "🚀  Deployment Verified. Happy Hunting."
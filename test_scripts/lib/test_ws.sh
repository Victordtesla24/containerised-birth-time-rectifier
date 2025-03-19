#!/bin/bash
SESSION_TOKEN=$(curl -s http://localhost:9000/api/session/init | jq -r ".session_id")
echo "Token: $SESSION_TOKEN"
WS_URL="ws://localhost:9000/ws/$SESSION_TOKEN"
echo "URL: $WS_URL"
websocat -v "$WS_URL"

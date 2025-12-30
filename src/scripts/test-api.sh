#!/bin/bash

# MCParr Gateway - API Testing Script

API_URL=${API_URL:-"http://localhost:8000"}

echo "Testing MCParr Gateway API at $API_URL"
echo "========================================="

# Test health endpoint
echo -e "\n1. Testing Health Check..."
curl -s "$API_URL/health" | python3 -m json.tool

# Test dashboard endpoint
echo -e "\n2. Testing Dashboard Overview..."
curl -s "$API_URL/api/v1/dashboard/overview" | python3 -m json.tool | head -20

# Test system metrics
echo -e "\n3. Testing System Metrics..."
curl -s "$API_URL/api/v1/system/metrics?duration=1m" | python3 -m json.tool | head -20

# Test WebSocket connection
echo -e "\n4. Testing WebSocket Connection..."
echo "To test WebSocket, run: wscat -c ws://localhost:8000/ws/logs"

# Test service listing
echo -e "\n5. Testing Service List..."
curl -s "$API_URL/api/v1/services" | python3 -m json.tool

echo -e "\n========================================="
echo "API Testing Complete!"
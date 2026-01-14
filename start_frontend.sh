#!/bin/bash
# Start frontend HTTP server
cd "$(dirname "$0")/frontend"
echo "Starting frontend server on http://localhost:8080"
echo "Open http://localhost:8080 in your browser"
python3 -m http.server 8080

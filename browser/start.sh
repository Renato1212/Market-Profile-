#!/bin/bash

echo "[1/4] Starting virtual display..."
Xvfb :99 -screen 0 1280x800x24 -ac &
sleep 3

echo "[2/4] Starting VNC server..."
x11vnc -display :99 -forever -nopw -shared -rfbport 5900 -quiet &
sleep 3

echo "[3/4] Starting noVNC WebSocket proxy..."
websockify --web=/opt/novnc --heartbeat=30 0.0.0.0:6080 localhost:5900 &
sleep 2

echo "[4/4] Starting Chrome..."
DISPLAY=:99 chromium --no-sandbox --disable-dev-shm-usage --disable-gpu \
    --no-first-run --disable-extensions --start-maximized \
    https://www.google.com &

echo "All services started. noVNC available on :6080"
exec tail -f /dev/null

#!/bin/bash

echo "[1/5] Starting virtual display at 1920x1080..."
Xvfb :99 -screen 0 1920x1080x24 -ac &
sleep 3

echo "[2/5] Starting VNC server..."
x11vnc -display :99 -forever -nopw -shared -rfbport 5900 -quiet &
sleep 2

echo "[3/5] Starting noVNC WebSocket proxy..."
websockify --web=/opt/novnc --heartbeat=30 0.0.0.0:6080 localhost:5900 &
sleep 2

echo "[4/5] Opening terminal..."
DISPLAY=:99 xterm \
    -fa 'Monospace' -fs 11 \
    -bg '#0d1117' -fg '#c9d1d9' \
    -geometry 110x28+0+600 \
    -title "Cloud Terminal — install & run apps here" &
sleep 1

echo "[5/5] Starting Chrome..."
DISPLAY=:99 chromium \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu \
    --no-first-run \
    --memory-pressure-off \
    --disable-background-timer-throttling \
    --disable-renderer-backgrounding \
    --disable-backgrounding-occluded-windows \
    --user-data-dir=/root/.config/chromium \
    --start-maximized \
    https://www.google.com &

echo "All services up. noVNC on :6080"
exec tail -f /dev/null

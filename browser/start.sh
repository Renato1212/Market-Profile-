#!/bin/bash
set -e

echo "[1/4] Starting TigerVNC server at 1920x1080..."
Xtigervnc :1 \
    -SecurityTypes None \
    -localhost no \
    -rfbport 5900 \
    -geometry 1920x1080 \
    -depth 24 \
    -desktop "Cloud Desktop" &
sleep 4

echo "[2/4] Starting Chrome and terminal..."
DISPLAY=:1 google-chrome \
    --no-sandbox \
    --no-first-run \
    --disable-dev-shm-usage \
    --start-maximized \
    --user-data-dir=/root/.config/chrome \
    https://www.google.com &

DISPLAY=:1 xterm \
    -fa 'Monospace' -fs 12 \
    -bg '#0d1117' -fg '#c9d1d9' \
    -geometry 130x32 \
    -title 'Cloud Terminal — sudo apt install / pip3 install / java -jar' &
sleep 3

echo "[3/4] Starting noVNC WebSocket proxy..."
websockify --web=/opt/novnc --heartbeat=30 0.0.0.0:6080 localhost:5900 &
sleep 2

echo "[4/4] Desktop ready."
exec tail -f /dev/null

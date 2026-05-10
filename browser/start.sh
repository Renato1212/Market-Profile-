#!/bin/bash
set -e

echo "Launching XPRA cloud desktop..."

# XPRA manages its own virtual display, encoding, and HTML5 server in one process.
# VP8/H.264 adaptive encoding — far sharper and faster than noVNC+VNC.
exec xpra start :100 \
    --bind-tcp=0.0.0.0:14500 \
    --html=on \
    --daemon=no \
    --auth=none \
    --encoding=auto \
    --quality=80 \
    --min-quality=50 \
    --speed=70 \
    --dpi=96 \
    --pulseaudio=no \
    --bell=no \
    --mdns=no \
    --notifications=no \
    --webcam=no \
    --printing=no \
    --file-transfer=on \
    --open-files=on \
    --exit-with-children=no \
    --start-child="google-chrome \
        --no-sandbox \
        --no-first-run \
        --disable-dev-shm-usage \
        --start-maximized \
        --user-data-dir=/root/.config/chrome \
        https://www.google.com" \
    --start-child="xterm \
        -fa 'Monospace' -fs 12 \
        -bg '#0d1117' -fg '#c9d1d9' \
        -geometry 130x32 \
        -title 'Cloud Terminal — sudo apt install / pip3 install / java -jar'"

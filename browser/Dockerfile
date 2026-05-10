FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    HOME=/root \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# ── Repositories: Google Chrome + XPRA ───────────────────────────────────────
RUN apt-get update && apt-get install -y wget gnupg2 ca-certificates apt-transport-https \
    && wget -qO- https://dl.google.com/linux/linux_signing_key.pub \
       | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
       http://dl.google.com/linux/chrome/deb/ stable main" \
       > /etc/apt/sources.list.d/google-chrome.list \
    && wget -qO /usr/share/keyrings/xpra.asc https://xpra.org/xpra.asc \
    && echo "deb [signed-by=/usr/share/keyrings/xpra.asc] \
       https://xpra.org/repos/jammy/ jammy main" \
       > /etc/apt/sources.list.d/xpra.list

# ── Install everything ────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # XPRA remote desktop (VP8/H.264, adaptive quality, built-in HTML5 client)
    xpra xpra-html5 \
    # Real Google Chrome (not Chromium snap)
    google-chrome-stable \
    # Java 17 — required for MotiveWave, NinjaTrader, and other trading apps
    openjdk-17-jdk \
    # Terminal
    xterm \
    # Download & run tools
    wget curl git unzip zip \
    python3 python3-pip python3-venv \
    nodejs npm \
    # AppImage support
    libfuse2 \
    # .deb installer
    gdebi-core \
    # Fonts
    fonts-liberation fonts-dejavu ttf-mscorefonts-installer \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY start.sh /start.sh
RUN chmod +x /start.sh

# XPRA HTML5 + WebSocket port
EXPOSE 14500
CMD ["/start.sh"]

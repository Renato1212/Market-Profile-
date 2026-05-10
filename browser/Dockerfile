FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    HOME=/root

RUN apt-get update && apt-get install -y --no-install-recommends \
    # Browser
    chromium \
    # Virtual display + VNC
    xvfb x11vnc \
    # Terminal emulator
    xterm \
    # noVNC dependencies
    python3-pip git ca-certificates \
    # Download tools
    wget curl unzip zip \
    # Run downloaded apps: Python, Node, shell scripts
    python3 python3-venv \
    nodejs npm \
    # AppImage support
    libfuse2 \
    # .deb package installer
    gdebi-core \
    # Fonts so pages render properly
    fonts-liberation fonts-dejavu \
    && pip3 install --no-cache-dir websockify \
    && git clone --depth 1 https://github.com/novnc/noVNC.git /opt/novnc \
    && ln -s /opt/novnc/vnc.html /opt/novnc/index.html \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 6080
CMD ["/start.sh"]

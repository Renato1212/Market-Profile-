FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    HOME=/root \
    DISPLAY=:1

# ── Google Chrome repo ────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget curl gnupg2 ca-certificates \
    && wget -qO- https://dl.google.com/linux/linux_signing_key.pub \
       | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
       http://dl.google.com/linux/chrome/deb/ stable main" \
       > /etc/apt/sources.list.d/google-chrome.list \
    && rm -rf /var/lib/apt/lists/*

# ── All packages from standard Ubuntu repos ───────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    google-chrome-stable \
    tigervnc-standalone-server \
    python3-pip git unzip zip \
    xterm \
    openjdk-17-jdk \
    nodejs npm \
    libfuse2 gdebi-core \
    fonts-liberation fonts-dejavu \
    && pip3 install --no-cache-dir websockify \
    && git clone --depth 1 https://github.com/novnc/noVNC.git /opt/novnc \
    && ln -s /opt/novnc/vnc.html /opt/novnc/index.html \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 6080
CMD ["/start.sh"]

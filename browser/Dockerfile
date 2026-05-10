FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    HOME=/root

RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium xvfb x11vnc python3-pip git ca-certificates \
    && pip3 install --no-cache-dir websockify \
    && git clone --depth 1 https://github.com/novnc/noVNC.git /opt/novnc \
    && ln -s /opt/novnc/vnc.html /opt/novnc/index.html \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 6080
CMD ["/start.sh"]

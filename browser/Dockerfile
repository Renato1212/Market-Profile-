FROM ghcr.io/m1k1o/neko/xfce:latest

USER root

# Add Google Chrome repository
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget gnupg2 ca-certificates \
    && wget -qO- https://dl.google.com/linux/linux_signing_key.pub \
       | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
       http://dl.google.com/linux/chrome/deb/ stable main" \
       > /etc/apt/sources.list.d/google-chrome.list \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    google-chrome-stable \
    openjdk-17-jdk \
    python3 python3-pip \
    nodejs npm \
    git curl wget unzip zip \
    fonts-liberation fonts-dejavu fonts-noto \
    libfuse2 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Auto-launch Chrome when XFCE desktop starts
RUN mkdir -p /etc/xdg/autostart \
    && printf '[Desktop Entry]\nType=Application\nName=Google Chrome\nExec=google-chrome --no-sandbox --disable-dev-shm-usage --no-first-run --start-maximized https://www.google.com\nHidden=false\nX-GNOME-Autostart-enabled=true\n' \
       > /etc/xdg/autostart/google-chrome.desktop

USER neko

FROM ghcr.io/m1k1o/neko/xfce:latest

# Note: do NOT set USER neko at the end. Neko's entrypoint (supervisord)
# must start as root and drops privileges itself.

USER root

# Add Google Chrome repository
RUN apt-get update \
    && apt-get install -y --no-install-recommends wget gnupg2 ca-certificates \
    && wget -qO- https://dl.google.com/linux/linux_signing_key.pub \
       | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
       > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Java (default-jdk auto-selects available version)
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jdk \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install supporting tools and fonts
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 python3-pip \
        git curl unzip zip \
        fonts-liberation fonts-dejavu \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Auto-launch Chrome on desktop start
RUN mkdir -p /etc/xdg/autostart \
    && printf '[Desktop Entry]\nType=Application\nName=Google Chrome\nExec=google-chrome --no-sandbox --disable-dev-shm-usage --no-first-run --start-maximized https://www.google.com\nHidden=false\nX-GNOME-Autostart-enabled=true\n' \
       > /etc/xdg/autostart/google-chrome.desktop

# MyBrowse — Personal Cloud Browser

A Chromium instance running on your Linux machine, streamed to any device via WebRTC, accessible from anywhere through a Cloudflare Tunnel. One user, one password, no accounts, no databases, no cloud bills.

## What you get

- Full Chrome browser running on your server, viewable on any phone/laptop/tablet
- Session persists forever: tabs, logins, extensions survive reboots and pauses
- Auto-pause when idle (zero CPU, RAM held frozen); instant resume on return
- Simple status page to launch/pause the browser from any device

## Requirements

- Linux machine you own (Ubuntu 24.04 recommended, ≥8 GB RAM, ≥4 cores)
- Docker Engine + Docker Compose v2 (`docker compose` — not the old `docker-compose`)
- A free Cloudflare account for public access (optional for LAN-only use)

## Quick start

```bash
git clone <this-repo> mybrowse && cd mybrowse
cp .env.example .env
# Edit .env — set ACCESS_PASSWORD, NEKO_PASSWORD, NEKO_PASSWORD_ADMIN, PUBLIC_IP
docker compose up -d
```

Visit `http://localhost` → enter your password → click **Open browser →**

The browser profile is stored in the `mybrowse-data` Docker volume and persists forever.

## Public access via Cloudflare Tunnel

One-time setup:

1. Create a free account at cloudflare.com
2. Go to **Zero Trust → Networks → Tunnels → Create a tunnel**
3. Name it anything, save, copy the **tunnel token**
4. Add it to `.env` as `CLOUDFLARE_TUNNEL_TOKEN=<token>`
5. In the tunnel dashboard, add a public hostname pointing to `http://caddy:80`
6. Start with the tunnel profile:

```bash
docker compose --profile tunnel up -d
```

**Zero-config test** (no account, no domain — temporary URL, good for testing):

```bash
docker run --rm cloudflare/cloudflared:2025.4.2 \
  tunnel --no-autoupdate --url http://localhost:80
```

## Session persistence and pause/resume

The browser profile lives in the `mybrowse-data` Docker volume. It survives:
container restarts, pauses/unpauses, and host reboots.

**Pause/resume works like a laptop lid:** `docker pause` freezes the process in RAM (zero CPU, zero disk writes, same memory footprint). `docker unpause` resumes in under a second — Chromium continues exactly where it left off.

**Auto-pause:** Keep the status page (`/`) open in a background browser tab. It sends a heartbeat every 30 s. If no heartbeat arrives for 60 s (all tabs closed), the container is paused automatically. Click **Launch** on the status page to resume.

To reset the browser profile from scratch: `docker volume rm mybrowse-data`

## Resource usage (honest numbers)

| State | RAM | CPU |
|---|---|---|
| Browser active | 1.5 – 2.5 GB | 1 – 2.5 cores |
| Paused (`docker pause`) | same (frozen in-place) | 0 |
| Caddy + control service | ~80 MB total | negligible |

On an 8 GB machine you will have ~5.5 GB free headroom while Neko is active.
Pausing reclaims all CPU instantly, with no memory cost.

## WebRTC connectivity (important if accessing remotely)

Video is streamed via WebRTC over UDP — this traffic goes **directly** between your device and your server, not through Cloudflare. For remote access to work:

| Server situation | What to do |
|---|---|
| VPS / machine with a public IP | Set `PUBLIC_IP` in `.env` to that IP. Done. |
| Home server, router with UPnP | Forward UDP 52000–52100 to the server; set `PUBLIC_IP` to your router's WAN IP. |
| Home server, no port forwarding, symmetric NAT | WebRTC won't reach the server. Options: move to a VPS, use Tailscale (install on both devices), or add a Coturn TURN server. |

## Cloudflare Tunnel — one caveat to know

Cloudflare's free tunnel proxies HTTP/HTTPS only. The WebRTC video stream travels outside the tunnel (direct UDP), so it does not consume Cloudflare bandwidth or violate their "no video streaming" clause. Only the signaling WebSocket goes through the tunnel. Personal use of a tunnel for WebSocket signaling is well within normal free-tier usage.

**If Cloudflare ever becomes a problem**, drop-in alternatives are:
- **Tailscale Funnel** — free for personal use, similar one-command tunnel setup
- A VPS with a real public IP — then you don't need any tunnel at all

## Image tags pinned

| Service | Image |
|---|---|
| Chromium browser | `ghcr.io/m1k1o/neko:google-chrome` |
| Reverse proxy / TLS | `caddy:2.9-alpine` |
| Control API | `node:20-alpine` (built locally) |
| Cloudflare Tunnel | `cloudflare/cloudflared:2025.4.2` |

All images are free, open-source, and self-hosted. No paid tier, no expiring trial.

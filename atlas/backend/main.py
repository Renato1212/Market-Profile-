"""
ATLAS Backend — FastAPI application entry point.
Serves all data endpoints, WebSocket live feed, and AI copilot.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
import pytz

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

from config import settings
from models.database import init_db
from api import gap_router, aperiod_router, options_router, ai_router, data_router, live_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

ET = pytz.timezone("America/New_York")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ATLAS backend starting up...")
    await init_db()
    logger.info("Database initialized")

    # Start background jobs
    from jobs.scheduler import start_scheduler
    scheduler = await start_scheduler()
    app.state.scheduler = scheduler

    yield

    logger.info("ATLAS backend shutting down...")
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()


app = FastAPI(
    title="ATLAS — ES Futures Intelligence Platform",
    version="1.0.0",
    description="Institutional-grade ES Futures analytics: Gap Fill, Market Profile, GEX, AI Copilot",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(gap_router, prefix="/api/gap", tags=["Gap Fill"])
app.include_router(aperiod_router, prefix="/api/aperiod", tags=["A Period"])
app.include_router(options_router, prefix="/api/options", tags=["Options/GEX"])
app.include_router(ai_router, prefix="/api/ai", tags=["AI Copilot"])
app.include_router(data_router, prefix="/api/data", tags=["Market Data"])
app.include_router(live_router, prefix="/api/live", tags=["Live"])


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "ATLAS",
        "timestamp": datetime.now(ET).isoformat(),
        "environment": settings.environment,
    }


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """WebSocket endpoint for live market data push."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive ping
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping", "ts": datetime.utcnow().isoformat()})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


app.state.ws_manager = manager

# Serve React frontend — check both dev layout (../frontend/dist) and
# container layout (./frontend/dist) so one binary works everywhere.
_base = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.join(_base, "..", "frontend", "dist")
if not os.path.isdir(FRONTEND_DIST):
    FRONTEND_DIST = os.path.join(_base, "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Serve React SPA — all non-API routes return index.html."""
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            return JSONResponse({"error": "not found"}, status_code=404)
        index = os.path.join(FRONTEND_DIST, "index.html")
        return FileResponse(index)

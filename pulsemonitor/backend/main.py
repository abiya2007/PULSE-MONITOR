"""
Main Python FastAPI Server for Pulse Rate Monitor Laptop Application.
Provides WebSocket real-time telemetry streaming, REST APIs for serial management,
session timeline tracking, medical symptom analysis, and static frontend hosting.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Add current directory to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from health_analyzer import HealthAnalyzer, SessionDatabase
from serial_reader import SerialPortReader
from simulator import PulseSimulator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PulseServer")

app = FastAPI(
    title="Pulse Monitor & Health Analysis System",
    description="Python laptop application for microchip pulse sensor monitoring, symptom assessment, and timeline tracking.",
    version="1.0.0"
)

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global services
db = SessionDatabase("pulse_sessions.db")
serial_reader = SerialPortReader(baud_rate=115200)
simulator = PulseSimulator()

# Global state
active_session_id: Optional[int] = None
current_mode: str = "SIMULATED"  # "HARDWARE" or "SIMULATED"
active_websockets: List[WebSocket] = []
recent_ibis: List[float] = []
latest_telemetry: Dict[str, Any] = {
    "bpm": 72.0,
    "ibi_ms": 833.3,
    "raw": 512,
    "status": "IDLE"
}
latest_analysis: Dict[str, Any] = HealthAnalyzer.analyze_pulse(72.0)


# Models
class SerialConnectRequest(BaseModel):
    port: str
    baud_rate: int = 115200


class SimulatorModeRequest(BaseModel):
    mode: str  # RESTING, BRADYCARDIA, EXERCISE, TACHYCARDIA, ARRHYTHMIA


class SessionStartRequest(BaseModel):
    name: str = "Pulse Monitor Session"


# Telemetry Handler
def handle_telemetry_data(data: Dict[str, Any]):
    global latest_telemetry, latest_analysis, recent_ibis, active_session_id

    bpm = float(data.get("bpm", 72.0))
    ibi_ms = float(data.get("ibi_ms", 60000.0 / max(bpm, 1)))
    raw_signal = int(data.get("raw", 512))

    # Maintain sliding window of IBIs for HRV / arrhythmia calculation
    recent_ibis.append(ibi_ms)
    if len(recent_ibis) > 20:
        recent_ibis.pop(0)

    # Perform medical symptom & status analysis
    analysis = HealthAnalyzer.analyze_pulse(bpm, ibi_ms, recent_ibis)

    latest_telemetry = {
        "bpm": bpm,
        "ibi_ms": ibi_ms,
        "raw": raw_signal,
        "mode": current_mode,
        "timestamp": analysis["timestamp"]
    }
    latest_analysis = analysis

    # Log to active database session if recording
    if active_session_id is not None:
        try:
            db.log_reading(active_session_id, analysis, raw_signal)
        except Exception as e:
            logger.error(f"Failed to log reading to DB: {e}")

    # Broadcast via asyncio to connected WebSockets
    payload = {
        "telemetry": latest_telemetry,
        "analysis": latest_analysis,
        "active_session_id": active_session_id,
        "connected_port": serial_reader.connected_port if current_mode == "HARDWARE" else "Simulator Mode"
    }

    # Broadcast to websocket clients in main thread loop
    asyncio.run_coroutine_threadsafe(_broadcast_ws(payload), main_loop)


async def _broadcast_ws(payload: dict):
    disconnected = []
    for ws in active_websockets:
        try:
            await ws.send_json(payload)
        except Exception:
            disconnected.append(ws)

    for ws in disconnected:
        if ws in active_websockets:
            active_websockets.remove(ws)


# Start default simulator mode on boot
@app.on_event("startup")
async def startup_event():
    global main_loop, active_session_id
    main_loop = asyncio.get_running_loop()

    # Automatically start a default initial session for logging
    active_session_id = db.start_session("Live Monitoring Session")
    logger.info(f"Started initial logging session ID: {active_session_id}")

    # Start simulator by default
    simulator.start(handle_telemetry_data)
    logger.info("Pulse simulator initialized and running.")


@app.on_event("shutdown")
async def shutdown_event():
    if active_session_id:
        db.end_session(active_session_id)
    simulator.stop()
    serial_reader.stop()


# REST Endpoints
@app.api_route("/api/ports", methods=["GET", "HEAD"])
def get_serial_ports():
    """Returns list of available serial COM ports on the laptop."""
    return {"ports": SerialPortReader.list_ports()}


@app.post("/api/connect")
def connect_serial_port(req: SerialConnectRequest):
    """Connects Python serial listener to specified microchip USB port."""
    global current_mode
    try:
        simulator.stop()
        serial_reader.start(req.port, handle_telemetry_data)
        current_mode = "HARDWARE"
        return {"status": "success", "message": f"Connecting to serial port {req.port}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/disconnect")
def disconnect_serial():
    """Disconnects hardware serial port and reverts to simulator."""
    global current_mode
    serial_reader.stop()
    simulator.start(handle_telemetry_data)
    current_mode = "SIMULATED"
    return {"status": "success", "message": "Disconnected hardware. Returned to simulator mode."}


@app.post("/api/simulator/mode")
def set_simulator_mode(req: SimulatorModeRequest):
    """Changes simulator profile (RESTING, BRADYCARDIA, EXERCISE, TACHYCARDIA, ARRHYTHMIA)."""
    global current_mode
    if current_mode != "SIMULATED":
        serial_reader.stop()
        simulator.start(handle_telemetry_data)
        current_mode = "SIMULATED"

    simulator.set_mode(req.mode)
    return {"status": "success", "mode": req.mode}


@app.post("/api/session/start")
def start_session(req: SessionStartRequest):
    """Starts a new pulse recording session ("from where to when")."""
    global active_session_id
    if active_session_id:
        db.end_session(active_session_id)

    active_session_id = db.start_session(req.name)
    return {"status": "success", "session_id": active_session_id, "name": req.name}


@app.post("/api/session/end")
def end_session():
    """Ends current pulse recording session and calculates summary stats."""
    global active_session_id
    if not active_session_id:
        raise HTTPException(status_code=400, detail="No active session to end")

    summary = db.end_session(active_session_id)
    ended_id = active_session_id
    active_session_id = None
    return {"status": "success", "summary": summary}


@app.api_route("/api/session/{session_id}", methods=["GET", "HEAD"])
def get_session(session_id: int):
    """Gets detailed timeline and event report for a session ("when and how")."""
    res = db.get_session_summary(session_id)
    if not res:
        raise HTTPException(status_code=404, detail="Session not found")
    return res


@app.api_route("/api/sessions", methods=["GET", "HEAD"])
def get_all_sessions():
    """Returns list of recent recording sessions."""
    return {"sessions": db.get_all_sessions()}


@app.api_route("/api/health-analysis", methods=["GET", "HEAD"])
def get_current_health_analysis():
    """Returns current real-time pulse health and symptom analysis."""
    return {
        "telemetry": latest_telemetry,
        "analysis": latest_analysis,
        "mode": current_mode,
        "connected_port": serial_reader.connected_port
    }


# WebSocket endpoint for real-time telemetry stream
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    logger.info(f"WebSocket client connected. Total active: {len(active_websockets)}")
    try:
        while True:
            # Keep socket open and receive any incoming commands
            msg = await websocket.receive_text()
    except (WebSocketDisconnect, ConnectionResetError, OSError, Exception):
        logger.info("WebSocket client disconnected cleanly.")
    finally:
        if websocket in active_websockets:
            active_websockets.remove(websocket)


# Static files setup for Frontend UI
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.api_route("/", methods=["GET", "HEAD"])
    def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))


def find_free_port(start_port: int = 8000, max_tries: int = 20) -> int:
    """Finds an available TCP port starting from start_port."""
    import socket
    for p in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', p))
                return p
            except OSError:
                continue
    return start_port


if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser(description="Pulse Monitor Laptop Application")
    parser.add_argument("--simulate", action="store_true", help="Force simulator mode on launch")
    parser.add_argument("--port", type=int, default=8000, help="Web server port")
    args = parser.parse_args()

    port = find_free_port(args.port)
    if port != args.port:
        logger.warning(f"Port {args.port} was occupied. Automatically switching to available port: {port}")

    print(f"\n========================================================")
    print(f"  Pulse Monitor Server running at: http://127.0.0.1:{port}")
    print(f"========================================================\n")

    uvicorn.run(app, host="127.0.0.1", port=port)

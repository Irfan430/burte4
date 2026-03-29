"""modules/api_server.py — FastAPI remote control server for NOVA."""
import asyncio
import logging
import threading
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import JSONResponse
    import uvicorn
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False
    logger.warning("FastAPI পাওয়া যায়নি। API সার্ভার নিষ্ক্রিয়।")


class NovaAPIServer:
    """FastAPI server providing REST and WebSocket access to NOVA."""

    def __init__(self, nova_loop=None, task_queue=None, port: int = 8765):
        self.nova_loop = nova_loop
        self.task_queue = task_queue
        self.port = port
        self._history: list[dict[str, Any]] = []
        self._current_status: dict[str, Any] = {"state": "idle", "goal": None}
        self._ws_clients: list[WebSocket] = []
        self._server_thread: threading.Thread | None = None

        if _FASTAPI_AVAILABLE:
            self.app = FastAPI(title="NOVA v9 API", version="9.0.0")
            self._setup_routes()

    def _setup_routes(self):
        app = self.app

        @app.get("/")
        async def root():
            return {"name": "NOVA v9", "status": "চলছে"}

        @app.post("/task")
        async def add_task(body: dict):
            goal = body.get("goal", "")
            priority = body.get("priority", 5)
            if not goal:
                return JSONResponse({"error": "লক্ষ্য দিন"}, status_code=400)
            task_id = f"task_{datetime.now().strftime('%H%M%S%f')}"
            entry = {"id": task_id, "goal": goal, "priority": priority, "ts": datetime.now().isoformat()}
            self._history.append(entry)
            if self.task_queue:
                self.task_queue.add_task(goal, priority=priority)
            await self._broadcast({"event": "task_added", "task": entry})
            return {"task_id": task_id, "message": "টাস্ক যোগ করা হয়েছে"}

        @app.get("/status")
        async def get_status():
            return self._current_status

        @app.get("/history")
        async def get_history():
            return {"history": self._history}

        @app.post("/stop")
        async def stop_task():
            if self.nova_loop:
                self.nova_loop.stop()
            self._current_status = {"state": "idle", "goal": None}
            return {"message": "টাস্ক বন্ধ করা হয়েছে"}

        @app.get("/tools")
        async def list_tools():
            return {"tools": []}

        @app.websocket("/ws")
        async def websocket_endpoint(ws: WebSocket):
            await ws.accept()
            self._ws_clients.append(ws)
            logger.info("WebSocket সংযোগ স্থাপিত")
            try:
                while True:
                    await ws.receive_text()
            except WebSocketDisconnect:
                self._ws_clients.remove(ws)
                logger.info("WebSocket সংযোগ বিচ্ছিন্ন")

    async def _broadcast(self, message: dict):
        """Send message to all connected WebSocket clients."""
        import json
        disconnected = []
        for ws in self._ws_clients:
            try:
                await ws.send_text(json.dumps(message, ensure_ascii=False))
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self._ws_clients.remove(ws)

    def broadcast_sync(self, message: dict):
        """Thread-safe broadcast from synchronous code."""
        if not self._ws_clients:
            return
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self._broadcast(message))
            loop.close()
        except Exception as exc:
            logger.warning(f"ব্রডকাস্ট ব্যর্থ: {exc}")

    def update_status(self, state: str, goal: str | None = None, step: str | None = None):
        self._current_status = {"state": state, "goal": goal, "step": step}
        self.broadcast_sync({"event": "status_update", **self._current_status})

    def start(self):
        """Start the API server in a background thread."""
        if not _FASTAPI_AVAILABLE:
            logger.error("FastAPI ইনস্টল করা নেই। API সার্ভার শুরু হয়নি।")
            return

        def _run():
            uvicorn.run(
                self.app,
                host="127.0.0.1",
                port=self.port,
                log_level="warning",
            )

        self._server_thread = threading.Thread(target=_run, daemon=True, name="nova-api-server")
        self._server_thread.start()
        logger.info(f"API সার্ভার শুরু হয়েছে: http://127.0.0.1:{self.port}")

    def stop(self):
        logger.info("API সার্ভার বন্ধ হচ্ছে...")


def send_telegram_notification(message: str) -> dict:
    """Send a Telegram notification."""
    try:
        import httpx
        from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
        if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
            return {"observation": "টেলিগ্রাম কনফিগার করা নেই।", "display": None}
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message})
            resp.raise_for_status()
        return {"observation": "টেলিগ্রাম বার্তা পাঠানো হয়েছে।", "display": None}
    except Exception as exc:
        return {"observation": f"টেলিগ্রাম ত্রুটি: {exc}", "display": None}

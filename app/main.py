from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models import ChatRequest, ChatResponse
from app.services.llm import DeepSeekClient, OllamaClient
from app.services.memory import TravelMemoryStore
from app.services.planner import TravelPlanner
from app.services.weather import weather_service
from app.services.geo import geo
from app.services.config import load_env, env

load_env()


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="智能旅行规划伴侣",
    description="AI-Native travel planning MVP with memory-driven conversation.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory_store = TravelMemoryStore()
ollama = OllamaClient()
deepseek = DeepSeekClient()
DEFAULT_PLANNER_MODE = "rules"
rules_planner = TravelPlanner(memory_store, enable_remote_context=True)
agent_planner = None


def planner_for(mode: str | None):
    global agent_planner
    selected_mode = mode or DEFAULT_PLANNER_MODE
    if selected_mode == "agent":
        if agent_planner is None:
            from app.services.agent_planner import AgentPlanner
            agent_planner = AgentPlanner(memory_store)
        return selected_mode, agent_planner
    return "rules", rules_planner


async def handle_chat_request(request: ChatRequest) -> ChatResponse:
    planner_mode, selected_planner = planner_for(request.mode)
    response = await selected_planner.handle(request)
    response.debug["planner_mode"] = planner_mode
    return response


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    react_landing = STATIC_DIR / "landing" / "index.html"
    if react_landing.exists():
        return FileResponse(react_landing)
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/chat", include_in_schema=False)
async def chat_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "service": "smart-travel-companion"}


@app.get("/api/llm/status")
async def llm_status() -> dict:
    return {"ollama": await ollama.status(), "deepseek": await deepseek.status()}


@app.get("/api/profile/{user_id}")
async def get_profile(user_id: str) -> dict:
    user = memory_store.user(user_id)
    return {
        "profile": user.get("profile", {}),
        "trip_history": user.get("trip_history", []),
        "feedback": user.get("feedback", []),
    }


@app.delete("/api/profile/{user_id}/preferences")
async def clear_preferences(user_id: str) -> dict:
    count = memory_store.clear_preferences(user_id)
    return {"ok": True, "cleared": count, "message": f"已清除 {count} 条偏好记忆"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await handle_chat_request(request)


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            try:
                request = ChatRequest(**data)
                response = await handle_chat_request(request)
                if hasattr(response, "model_dump"):
                    await websocket.send_json(response.model_dump())
                else:
                    await websocket.send_json(response.dict())
            except Exception as exc:
                detail = f"{type(exc).__name__}: {exc}"
                await websocket.send_json({
                    "session_id": data.get("session_id", ""),
                    "reply": f"本地服务处理请求时出错：{detail}",
                    "itinerary": None,
                    "memory_hits": [],
                    "reminders": [],
                    "quick_actions": [],
                    "weather": None,
                    "nearby_pois": [],
                    "map_markers": [],
                    "debug": {"intent": "error", "error": detail},
                })
    except WebSocketDisconnect:
        return


@app.get("/api/config/amap-key")
async def amap_key() -> dict:
    key = os.getenv("AMAP_API_KEY", "")
    code = os.getenv("AMAP_SECURITY_CODE", "")
    return {"ok": bool(key), "key": key, "securityCode": code}


@app.get("/api/weather/{city}")
async def weather(city: str) -> dict:
    report = await weather_service.fetch(city)
    if not report:
        return {"ok": False, "city": city, "message": "天气数据暂不可用"}
    return {
        "ok": True,
        "city": report.city,
        "provider": report.provider,
        "summary": report.summary,
        "forecast": [
            {
                "date": d.date, "weather": d.weather,
                "temp_high": d.temp_high, "temp_low": d.temp_low,
                "humidity": d.humidity, "rain_prob": d.rain_prob,
                "wind_speed": d.wind_speed,
            }
            for d in report.forecast
        ],
    }


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/images", StaticFiles(directory=BASE_DIR.parent / "Tourist pictures"), name="tourist-images")

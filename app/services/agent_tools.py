"""LangChain tool definitions wrapping existing travel services."""

from __future__ import annotations

import json

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.services.attractions import CITY_LIBRARY, CITY_SPOTS, SCENE_BANK, SPOT_TAGS

SUPPORTED_CITY_LIST = list(CITY_LIBRARY.keys())


# ── Input schemas ──

class SearchSpotsInput(BaseModel):
    city: str = Field(description="城市名，如 广州、北京")
    tags: list[str] | None = Field(default=None, description="要匹配的标签列表，如 ['小众', '自然']")
    avoid_tags: list[str] | None = Field(default=None, description="要排除的标签列表，如 ['商业', '网红']")
    count: int = Field(default=8, description="最多返回几个景点")


class SearchMemoryInput(BaseModel):
    user_id: str = Field(description="用户 ID")
    query: str = Field(description="搜索关键词，如 自然风光、小众")


class GeocodeInput(BaseModel):
    address: str = Field(description="地址或景点名")
    city: str = Field(default="", description="所在城市，可选")


class SearchFoodInput(BaseModel):
    lng: float = Field(description="经度 (GCJ-02)")
    lat: float = Field(description="纬度 (GCJ-02)")
    count: int = Field(default=5, description="返回餐厅数量")


class LastItineraryInput(BaseModel):
    user_id: str = Field(description="用户 ID")
    session_id: str = Field(description="会话 ID")


class WeatherInput(BaseModel):
    city: str = Field(description="城市名，如 广州、北京")


# ── Final structured output schema (used via ToolStrategy in agent_planner.py) ──

class DayPlanOutput(BaseModel):
    day: int = Field(description="第几天，从 1 开始")
    city: str = Field(description="当天主要景点/区域名")
    theme: str = Field(description="当天主题，如 抵达适应、小众探索、文化慢游、城市散步、弹性收尾")
    morning: str = Field(description="上午活动描述")
    afternoon: str = Field(description="下午活动描述")
    evening: str = Field(description="晚上活动描述")
    transport: str = Field(description="交通建议")
    weather_tip: str = Field(description="天气提示")


class ReminderOutput(BaseModel):
    timing: str = Field(description="提醒时机，如 行前3天、每天20:00")
    title: str = Field(description="提醒标题")
    detail: str = Field(description="提醒详情")
    priority: str = Field(default="normal", description="优先级: high / normal")


class FinalItineraryOutput(BaseModel):
    """Agent must produce this structured output as its final response."""
    reply: str = Field(description="给用户的中文自然语言回复，友好、信息丰富，提及天气和偏好匹配")
    destination: str = Field(description="目的地城市名")
    days: int = Field(description="行程天数")
    budget: int | None = Field(default=None, description="预算（元）")
    day_plans: list[DayPlanOutput] = Field(description="每日行程计划列表")
    avoid: list[str] = Field(default_factory=list, description="避开的景点或类型")
    highlights: list[str] = Field(default_factory=list, description="行程亮点")
    reminders: list[ReminderOutput] = Field(default_factory=list, description="主动提醒列表")
    quick_actions: list[str] = Field(default_factory=list, description="2-3 条上下文相关的快捷操作建议")


# ── Tool implementations ──

@tool
async def get_supported_cities() -> str:
    """返回当前支持的旅游城市列表及各城市景点数量。
    在规划行程前务必先调用此工具确认目的地是否可用。"""
    result = {city: len(spots) for city, spots in CITY_LIBRARY.items()}
    return json.dumps({"supported_cities": SUPPORTED_CITY_LIST, "spot_counts": result}, ensure_ascii=False)


@tool(args_schema=SearchSpotsInput)
async def search_spots(
    city: str,
    tags: list[str] | None = None,
    avoid_tags: list[str] | None = None,
    count: int = 8,
) -> str:
    """搜索指定城市的景点。可按标签筛选（如 '小众'、'自然'、'历史文化'、'美食'），
    也可按标签排除（如 '商业'、'网红'）。返回景点名、标签、上午/下午/晚上活动建议。"""
    spots = CITY_SPOTS.get(city, [])
    if not spots:
        return json.dumps({"error": f"{city} 暂未收录", "spots": []}, ensure_ascii=False)

    if tags:
        spots = [s for s in spots if any(t in s["tags"] for t in tags)]
    if avoid_tags:
        spots = [s for s in spots if not any(t in s["tags"] for t in avoid_tags)]

    result = []
    for s in spots[:count]:
        result.append({
            "name": s["name"],
            "tags": s["tags"],
            "morning": s["morning"],
            "afternoon": s["afternoon"],
            "evening": s["evening"],
        })
    return json.dumps({"spots": result, "total": len(spots)}, ensure_ascii=False)


@tool(args_schema=WeatherInput)
async def get_weather_forecast(city: str) -> str:
    """获取城市未来天气预报。返回逐日天气、温度、降水概率、湿度、风速、紫外线指数和概要。
    用于为行程添加天气提示，判断是否需要室内替代方案。"""
    from app.services.weather import weather_service

    report = await weather_service.fetch(city)
    if not report:
        return json.dumps({"error": f"{city} 天气数据暂不可用", "forecast": []}, ensure_ascii=False)

    forecast = []
    for d in report.forecast[:7]:
        forecast.append({
            "date": d.date,
            "weather": d.weather,
            "temp_high": d.temp_high,
            "temp_low": d.temp_low,
            "humidity": d.humidity,
            "rain_prob": d.rain_prob,
            "wind_speed": d.wind_speed,
            "uv_index": d.uv_index,
        })
    return json.dumps({
        "city": report.city,
        "provider": report.provider,
        "summary": report.summary,
        "forecast": forecast,
    }, ensure_ascii=False)


@tool
async def get_user_profile(user_id: str) -> str:
    """获取用户偏好画像：包括偏好标签、预算范围、同行人、旅行历史和反馈记录。
    用于个性化行程推荐。"""
    from app.services.memory import TravelMemoryStore

    store = TravelMemoryStore()
    user = store.user(user_id)
    profile = user.get("profile", {})
    trips = user.get("trip_history", [])
    feedback = user.get("feedback", [])
    return json.dumps({
        "profile": profile,
        "trip_count": len(trips),
        "feedback_count": len(feedback),
    }, ensure_ascii=False)


@tool(args_schema=SearchMemoryInput)
async def search_memory(user_id: str, query: str) -> str:
    """搜索用户的历史记忆：根据关键词匹配偏好标签、历史行程和过往反馈。
    返回相关的记忆条目。"""
    from app.services.memory import TravelMemoryStore

    store = TravelMemoryStore()
    hits = store.search(user_id, query, limit=5)
    return json.dumps({"hits": hits}, ensure_ascii=False)


@tool(args_schema=GeocodeInput)
async def geocode_location(address: str, city: str = "") -> str:
    """获取地址或景点名的地理坐标 (GCJ-02)。返回经度和纬度。"""
    from app.services.geo import geo

    coord = await geo.geocode(address, city)
    if not coord:
        return json.dumps({"error": f"无法解析地址: {address}", "lng": None, "lat": None}, ensure_ascii=False)
    return json.dumps({"lng": coord[0], "lat": coord[1], "address": address}, ensure_ascii=False)


@tool(args_schema=SearchFoodInput)
async def search_food_nearby(lng: float, lat: float, count: int = 5) -> str:
    """搜索指定坐标附近的美食和餐厅。返回名称、地址和分类。"""
    from app.services.geo import geo

    pois = await geo.search_foods(lng, lat, count)
    if not pois:
        return json.dumps({"restaurants": []}, ensure_ascii=False)
    result = [{"name": p.name, "address": p.address, "category": p.category} for p in pois]
    return json.dumps({"restaurants": result}, ensure_ascii=False)


@tool(args_schema=LastItineraryInput)
async def get_last_itinerary(user_id: str, session_id: str) -> str:
    """获取当前会话中最近一次生成的行程。用于调整、修改已有行程（如下雨改室内、取消某景点等）。"""
    from app.services.memory import TravelMemoryStore

    store = TravelMemoryStore()
    last = store.last_itinerary(user_id, session_id)
    if not last:
        return json.dumps({"itinerary": None, "message": "暂无已有行程"}, ensure_ascii=False)
    return json.dumps({"itinerary": last}, ensure_ascii=False)


# All research tools (core set for efficient planning — geo/food excluded to limit iterations)
AGENT_TOOLS = [
    get_supported_cities,
    search_spots,
    get_weather_forecast,
    get_user_profile,
    search_memory,
    get_last_itinerary,
]

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1200)
    session_id: str | None = None
    user_id: str = "demo-user"
    location: str | None = None
    mode: Literal["rules", "agent"] | None = None


class MemoryHit(BaseModel):
    kind: str
    title: str
    detail: str


class DayPlan(BaseModel):
    day: int
    city: str
    theme: str
    morning: str
    afternoon: str
    evening: str
    transport: str
    weather_tip: str


class Itinerary(BaseModel):
    title: str
    destination: str
    days: int
    budget: int | None = None
    summary: str
    day_plans: list[DayPlan]
    avoid: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)


class Reminder(BaseModel):
    timing: str
    title: str
    detail: str
    priority: str = "normal"


class WeatherDay(BaseModel):
    date: str
    weather: str
    temp_high: float
    temp_low: float
    humidity: int
    rain_prob: int
    wind_speed: float


class WeatherInfo(BaseModel):
    city: str
    summary: str
    forecast: list[WeatherDay]
    provider: str


class GeoPOI(BaseModel):
    name: str
    address: str
    category: str


class FoodPOI(BaseModel):
    name: str
    address: str = ""
    category: str = ""


class MapMarker(BaseModel):
    name: str
    lng: float
    lat: float
    day: int = 1
    theme: str = ""
    morning: str = ""
    afternoon: str = ""
    evening: str = ""
    transport: str = ""
    nearby_foods: list[FoodPOI] = Field(default_factory=list)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    itinerary: Itinerary | None = None
    memory_hits: list[MemoryHit] = Field(default_factory=list)
    reminders: list[Reminder] = Field(default_factory=list)
    quick_actions: list[str] = Field(default_factory=list)
    weather: WeatherInfo | None = None
    nearby_pois: list[GeoPOI] = Field(default_factory=list)
    map_markers: list[MapMarker] = Field(default_factory=list)
    debug: dict[str, Any] = Field(default_factory=dict)

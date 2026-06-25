from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.services.config import load_env, env

load_env()

CITY_COORDS = {
    "重庆": (29.4316, 106.9123),
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "成都": (30.5728, 104.0668),
    "杭州": (30.2741, 120.1551),
    "西安": (34.3416, 108.9398),
    "广州": (23.1291, 113.2644),
    "桂林": (25.2736, 110.2900),
    "苏州": (31.2990, 120.5853),
    "长沙": (28.2282, 112.9388),
}

WMO_CODES: dict[int, str] = {
    0: "晴", 1: "晴间多云", 2: "多云", 3: "阴",
    45: "雾", 48: "冻雾",
    51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "阵雨", 81: "中阵雨", 82: "大阵雨",
    95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
}


@dataclass
class DailyWeather:
    date: str
    weather: str
    temp_high: float
    temp_low: float
    humidity: int
    wind_speed: float
    rain_prob: int
    uv_index: float


@dataclass
class WeatherReport:
    city: str
    current: DailyWeather | None
    forecast: list[DailyWeather]
    provider: str
    summary: str


class OpenMeteoClient:
    """Free weather provider — no API key needed."""

    BASE = "https://api.open-meteo.com/v1/forecast"

    async def fetch(self, city: str) -> WeatherReport | None:
        coords = CITY_COORDS.get(city)
        if not coords:
            return None
        lat, lon = coords
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "relative_humidity_2m_mean",
                "wind_speed_10m_max",
                "precipitation_probability_max",
                "uv_index_max",
            ],
            "timezone": "Asia/Shanghai",
            "forecast_days": 16,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.BASE, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError:
            return None

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        if not dates:
            return None

        forecast = []
        for i, date_str in enumerate(dates):
            code = daily.get("weather_code", [0])[i] if i < len(daily.get("weather_code", [])) else 0
            forecast.append(DailyWeather(
                date=date_str,
                weather=WMO_CODES.get(code, f"未知({code})"),
                temp_high=daily.get("temperature_2m_max", [0])[i],
                temp_low=daily.get("temperature_2m_min", [0])[i],
                humidity=daily.get("relative_humidity_2m_mean", [60])[i],
                wind_speed=daily.get("wind_speed_10m_max", [0])[i],
                rain_prob=daily.get("precipitation_probability_max", [0])[i],
                uv_index=daily.get("uv_index_max", [0])[i],
            ))

        summary = self._build_summary(forecast)
        return WeatherReport(
            city=city,
            current=forecast[0] if forecast else None,
            forecast=forecast,
            provider="open-meteo",
            summary=summary,
        )

    @staticmethod
    def _build_summary(forecast: list[DailyWeather]) -> str:
        if not forecast:
            return "暂无天气数据"
        today = forecast[0]
        parts = [f"今日{today.weather}，{today.temp_low:.0f}~{today.temp_high:.0f}°C"]

        if today.rain_prob > 60:
            parts.append(f"降水概率{today.rain_prob}%，建议携带雨具")
        elif today.rain_prob > 30:
            parts.append(f"降水概率{today.rain_prob}%，备一把折叠伞")

        if today.wind_speed > 30:
            parts.append("风力较大，户外活动注意安全")
        if today.uv_index > 7:
            parts.append("紫外线强，做好防晒")

        # check next 3 days for rain
        rain_days = [d for d in forecast[1:4] if d.rain_prob > 50]
        if rain_days:
            parts.append(f"未来{len(rain_days)}天可能有雨，保留室内替代方案")
        return "。".join(parts) + "。"


class QWeatherClient:
    """和风天气 — better Chinese city coverage, needs API key."""

    BASE = "https://devapi.qweather.com/v7/weather"

    def __init__(self) -> None:
        self.api_key = os.getenv("QWEATHER_API_KEY", "")
        self.enabled = bool(self.api_key)

    async def fetch(self, city: str) -> WeatherReport | None:
        if not self.enabled:
            return None
        location_id = self._location_id(city)
        if not location_id:
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.BASE}/7d",
                    params={"location": location_id, "key": self.api_key},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError:
            return None

        if data.get("code") != "200":
            return None

        daily_list = data.get("daily", [])
        forecast = []
        for d in daily_list:
            forecast.append(DailyWeather(
                date=d.get("fxDate", ""),
                weather=f"{d.get('textDay', '')}",
                temp_high=float(d.get("tempMax", 0)),
                temp_low=float(d.get("tempMin", 0)),
                humidity=int(d.get("humidity", 60)),
                wind_speed=float(d.get("windSpeedDay", 0)),
                rain_prob=int(d.get("pop", 0)),
                uv_index=float(d.get("uvIndex", 0)),
            ))

        summary = OpenMeteoClient._build_summary(forecast)
        return WeatherReport(
            city=city,
            current=forecast[0] if forecast else None,
            forecast=forecast,
            provider="qweather",
            summary=summary,
        )

    @staticmethod
    def _location_id(city: str) -> str:
        mapping = {
            "重庆": "101040100", "北京": "101010100", "上海": "101020100",
            "成都": "101270100", "杭州": "101210100", "西安": "101110100",
            "广州": "101280100", "桂林": "101300501", "苏州": "101190401",
            "长沙": "101250100",
        }
        return mapping.get(city, "")


class WeatherService:
    def __init__(self) -> None:
        self.open_meteo = OpenMeteoClient()
        self.qweather = QWeatherClient()

    async def fetch(self, city: str) -> WeatherReport | None:
        if self.qweather.enabled:
            report = await self.qweather.fetch(city)
            if report:
                return report
        return await self.open_meteo.fetch(city)

    def weather_tip(self, report: WeatherReport | None, day_index: int = 0) -> str:
        if not report or not report.forecast:
            return "出发前检查天气，午后安排可替换为室内体验。"
        if day_index >= len(report.forecast):
            day_index = len(report.forecast) - 1
        day = report.forecast[day_index]
        tips = []
        if day.rain_prob > 60:
            tips.append("降水概率高，带雨具并预留室内替代点")
        elif day.rain_prob > 30:
            tips.append("可能有雨，备把折叠伞")
        if day.temp_high > 35:
            tips.append("高温天气，避开正午户外活动，多补水")
        elif day.temp_low < 5:
            tips.append("气温较低，注意保暖")
        if day.uv_index > 7:
            tips.append("紫外线强，做好防晒")
        if day.wind_speed > 30:
            tips.append("风力较大，临水或高空项目注意安全")
        if not tips:
            tips.append(f"{day.weather}，{day.temp_low:.0f}~{day.temp_high:.0f}°C，适合出行")
        return "；".join(tips) + "。"


weather_service = WeatherService()

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from app.services.config import load_env, env
from app.services.attractions import spot_coord

load_env()

CITY_COORDS_WGS84 = {
    "重庆": (106.5516, 29.5630), "北京": (116.4074, 39.9042),
    "上海": (121.4737, 31.2304), "成都": (104.0668, 30.5728),
    "杭州": (120.1551, 30.2741), "西安": (108.9398, 34.3416),
    "广州": (113.2644, 23.1291), "桂林": (110.2900, 25.2736),
    "苏州": (120.5853, 31.2990), "长沙": (112.9388, 28.2282),
}


@dataclass
class GeoPoint:
    name: str
    address: str
    location: str
    category: str


class GeoService:
    """Amap REST geocoding (returns GCJ-02) with WGS-84 fallback."""

    AMAP_GEO = "https://restapi.amap.com/v3/geocode/geo"
    AMAP_AROUND = "https://restapi.amap.com/v3/place/around"

    def __init__(self) -> None:
        self.rest_key = os.getenv("AMAP_REST_KEY", "") or os.getenv("AMAP_API_KEY", "")

    async def geocode(self, address: str, city: str = "", allow_remote: bool = True) -> tuple[float, float] | None:
        local_coord = spot_coord(address)
        if local_coord:
            return local_coord

        if self.rest_key and allow_remote:
            try:
                params: dict = {"key": self.rest_key, "address": address}
                if city:
                    params["city"] = city
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.get(self.AMAP_GEO, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                if data.get("status") == "1" and data.get("geocodes"):
                    loc = data["geocodes"][0].get("location", "")
                    if "," in loc:
                        lng_str, lat_str = loc.split(",", 1)
                        return (float(lng_str), float(lat_str))
            except (httpx.HTTPError, ValueError, TypeError):
                pass
        coords = CITY_COORDS_WGS84.get(city) or CITY_COORDS_WGS84.get(address)
        return coords if coords else None

    def city_center(self, city: str) -> str | None:
        coords = CITY_COORDS_WGS84.get(city)
        return f"{coords[0]},{coords[1]}" if coords else None

    async def search_foods(self, lng: float, lat: float, count: int = 5) -> list[GeoPoint]:
        if not self.rest_key:
            return []
        try:
            params = {
                "key": self.rest_key,
                "location": f"{lng},{lat}",
                "keywords": "美食|餐厅|小吃|特色菜",
                "radius": 3000,
                "offset": count,
                "extensions": "base",
            }
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(self.AMAP_AROUND, params=params)
                resp.raise_for_status()
                data = resp.json()
            if data.get("status") != "1":
                return []
            pois = []
            for p in data.get("pois", [])[:count]:
                name = p.get("name", "")
                addr = p.get("address", "")
                cat = p.get("type", "")
                if name:
                    pois.append(GeoPoint(
                        name=str(name),
                        address=str(addr) if isinstance(addr, str) else "",
                        location=p.get("location", ""),
                        category=str(cat).split(";")[-1] if cat else "",
                    ))
            return pois
        except httpx.HTTPError:
            return []


geo = GeoService()

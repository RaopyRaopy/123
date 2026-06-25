from __future__ import annotations

import re
from typing import Protocol
from uuid import uuid4

from app.models import ChatRequest, ChatResponse, DayPlan, FoodPOI, GeoPOI, Itinerary, MapMarker, MemoryHit, Reminder, WeatherDay, WeatherInfo
from app.services.memory import TravelMemoryStore
from app.services.weather import WeatherReport, weather_service
from app.services.geo import geo
from app.services.attractions import CITY_LIBRARY, CITY_SPOTS, SCENE_BANK, SPOT_TAGS, rank_spots_for_request


class TravelInterpreter(Protocol):
    def interpret_travel_request(self, message: str) -> dict:
        ...


SUPPORTED_CITIES = tuple(CITY_LIBRARY.keys())
SUPPORTED_CITY_TEXT = "、".join(SUPPORTED_CITIES)

# Keyword → tag mapping for scoring spots against user input
KEYWORD_TAG_MAP = {
    "小众": "小众", "安静": "小众", "人少": "小众",
    "商业": "商业", "购物": "商业", "逛街": "商业",
    "风景": "风景", "自然": "自然", "山水": "风景", "美景": "风景",
    "户外": "户外", "登山": "户外", "徒步": "户外", "骑行": "户外", "运动": "户外",
    "历史文化": "历史文化", "历史": "历史文化", "文化": "历史文化", "古迹": "历史文化", "博物馆": "历史文化",
    "美食": "美食", "好吃": "美食", "小吃": "美食", "吃": "美食", "火锅": "美食",
    "夜景": "夜景", "晚上": "夜景", "夜间": "夜景",
    "亲子": "亲子", "孩子": "亲子", "小孩": "亲子", "带娃": "亲子",
    "网红": "网红", "打卡": "网红", "拍照": "网红", "出片": "网红",
    "城市": "城市", "市区": "城市", "室内": "室内",
    "古镇": "古镇", "文创": "文创", "艺术": "文创",
    "免费": "免费", "不要钱": "免费", "便宜": "免费",
}
DESTINATION_STOPWORDS = {"小众景点", "室内活动", "自然风光", "商业化景点", "人多景点", "地方"}


class LlmRecommender(Protocol):
    def recommend_attractions(self, destination: str, count: int, existing_spots: list[str], preferences: list[str] = None) -> list[str]:
        ...


class TravelPlanner:
    def __init__(
        self, 
        memory: TravelMemoryStore, 
        interpreter: TravelInterpreter | None = None,
        llm_recommender: LlmRecommender | None = None,
        enable_remote_context: bool = True,
    ) -> None:
        self.memory = memory
        self.interpreter = interpreter
        self.llm_recommender = llm_recommender
        self.enable_remote_context = enable_remote_context

    async def handle(self, request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or str(uuid4())
        interpretation = await self._interpret(request.message)
        remembered = self.memory.update_from_message(request.user_id, request.message)
        memory_hits = self.memory.search(request.user_id, request.message)
        if remembered:
            memory_hits = remembered + memory_hits

        if self._is_adjustment(request.message, interpretation):
            response = await self._adjust_itinerary(request, session_id, memory_hits, interpretation)
        else:
            response = await self._plan_trip(request, session_id, memory_hits, interpretation)

        payload = _model_dump(response)
        self.memory.record_interaction(request.user_id, session_id, request.message, payload)
        return response

    async def _interpret(self, message: str) -> dict:
        if not self.interpreter:
            return {}
        try:
            result = await self.interpreter.interpret_travel_request(message)
            return result or {}
        except Exception:
            return {}

    async def _plan_trip(
        self,
        request: ChatRequest,
        session_id: str,
        memory_hits: list[dict[str, str]],
        interpretation: dict,
    ) -> ChatResponse:
        destination = self._extract_destination(request.message, interpretation)
        if not destination:
            return self._not_collected_response(session_id, None, memory_hits, interpretation, missing_destination=True)
        if destination not in SUPPORTED_CITIES:
            return self._not_collected_response(session_id, destination, memory_hits, interpretation)

        days = self._extract_days(request.message, interpretation) or 3
        budget = self._extract_budget(request.message, interpretation)
        profile = self.memory.profile(request.user_id)
        avoid = self._avoid_list(profile, request.message, interpretation)
        cities = await self._route(destination, days, avoid, profile, request.message)
        itinerary = self._build_itinerary(destination, cities, days, budget, avoid)
        hit_models = [MemoryHit(**hit) for hit in memory_hits]

        # fetch real weather
        weather_info: WeatherInfo | None = None
        nearby_pois: list[GeoPOI] = []
        weather_report = await weather_service.fetch(destination) if self.enable_remote_context else None
        if weather_report:
            weather_days = [
                WeatherDay(
                    date=d.date, weather=d.weather,
                    temp_high=d.temp_high, temp_low=d.temp_low,
                    humidity=d.humidity, rain_prob=d.rain_prob,
                    wind_speed=d.wind_speed,
                )
                for d in weather_report.forecast[:days]
            ]
            weather_info = WeatherInfo(
                city=destination,
                summary=weather_report.summary,
                forecast=weather_days,
                provider=weather_report.provider,
            )
            # update day plans with real weather tips
            for i, plan in enumerate(itinerary.day_plans):
                plan.weather_tip = weather_service.weather_tip(weather_report, i)

        reminders = self._build_reminders(destination, weather_report)

        # geocode each day city via Amap REST for accurate GCJ-02 coords + food search
        map_markers: list[MapMarker] = []
        for i, plan in enumerate(itinerary.day_plans):
            coord = await geo.geocode(plan.city, destination, allow_remote=self.enable_remote_context)
            foods: list[FoodPOI] = []
            if coord:
                food_pois = await geo.search_foods(coord[0], coord[1], count=5)
                foods = [FoodPOI(name=f.name, address=f.address, category=f.category) for f in food_pois]

            if coord:
                map_markers.append(MapMarker(
                    name=plan.city,
                    lng=coord[0], lat=coord[1],
                    day=plan.day,
                    theme=plan.theme,
                    morning=plan.morning,
                    afternoon=plan.afternoon,
                    evening=plan.evening,
                    transport=plan.transport,
                    nearby_foods=foods,
                ))
            else:
                center = geo.city_center(destination)
                if center:
                    try:
                        lng_str, lat_str = center.split(",")
                        map_markers.append(MapMarker(
                            name=plan.city,
                            lng=float(lng_str) + i * 0.01, lat=float(lat_str) + i * 0.005,
                            day=plan.day, theme=plan.theme,
                            morning=plan.morning, afternoon=plan.afternoon,
                            evening=plan.evening, transport=plan.transport,
                        ))
                    except (ValueError, TypeError):
                        pass

        budget_display = profile.get('budget_range', '').strip() or "（未设置）"
        budget_text = f"预算约 {budget} 元" if budget else f"参考预算 {budget_display} 元"
        memory_text = ""
        if hit_models:
            memory_text = f"我先调用了 {len(hit_models)} 条相关记忆。"
        else:
            memory_text = "没有找到相关记忆，基于通用偏好生成。"

        weather_line = ""
        if weather_info:
            weather_line = f" {destination}未来天气：{weather_info.summary}"

        reply = (
            f"已生成 {destination} {days} 天自由行方案，{budget_text}。"
            f"{memory_text} 路线主轴是 {' -> '.join(cities[:days])}，节奏偏松，方便途中调整。"
            f"{weather_line}"
        )
        return ChatResponse(
            session_id=session_id,
            reply=reply,
            itinerary=itinerary,
            memory_hits=hit_models,
            reminders=reminders,
            quick_actions=["今天下雨了，帮我改成室内活动", "把预算压到5000以内", "加入两家安静咖啡馆"],
            weather=weather_info,
            nearby_pois=nearby_pois,
            map_markers=map_markers,
            debug={
                "intent": "plan",
                "destination": destination,
                "days": days,
                "weather_available": weather_info is not None,
                "interpreter": interpretation.get("provider", "rules"),
                "collected": True,
            },
        )

    async def _adjust_itinerary(
        self,
        request: ChatRequest,
        session_id: str,
        memory_hits: list[dict[str, str]],
        interpretation: dict,
    ) -> ChatResponse:
        last = self.memory.last_itinerary(request.user_id, session_id)
        destination = self._extract_destination(request.message, interpretation) or (last or {}).get("destination")

        if not destination:
            return self._not_collected_response(session_id, None, memory_hits, interpretation, missing_destination=True)

        if destination not in SUPPORTED_CITIES:
            if last:
                destination = last.get("destination")
                if not destination or destination not in SUPPORTED_CITIES:
                    return self._not_collected_response(session_id, destination, memory_hits, interpretation)
            else:
                return self._not_collected_response(session_id, destination, memory_hits, interpretation)

        budget = (last or {}).get("budget")
        days = (last or {}).get("days", 2)
        profile = self.memory.profile(request.user_id)
        avoid = self._avoid_list(profile, request.message, interpretation)

        # fetch real weather for adjustments
        weather_info: WeatherInfo | None = None
        weather_report = await weather_service.fetch(destination) if self.enable_remote_context else None
        if weather_report:
            weather_days = [
                WeatherDay(
                    date=d.date, weather=d.weather,
                    temp_high=d.temp_high, temp_low=d.temp_low,
                    humidity=d.humidity, rain_prob=d.rain_prob,
                    wind_speed=d.wind_speed,
                )
                for d in weather_report.forecast[:days]
            ]
            weather_info = WeatherInfo(
                city=destination,
                summary=weather_report.summary,
                forecast=weather_days,
                provider=weather_report.provider,
            )

        if any(word in request.message for word in ("下雨", "天气不好")):
            avoid.extend(["长距离户外安排", "拥挤打卡点"])
            cities = await self._route(destination, days, avoid, profile, request.message)
            itinerary = self._build_itinerary(destination, cities, days, budget, avoid=avoid)
            itinerary.summary = "已把强户外行程改为室内文化体验和短距离街区活动，尽量不打乱后续安排。"
            itinerary.highlights = ["室内文化体验", "短距离街区漫游", "雨天备用", "后续行程无需大改"]
            if weather_report:
                for i, plan in enumerate(itinerary.day_plans):
                    plan.weather_tip = weather_service.weather_tip(weather_report, i)
            weather_line = f" 当前{weather_report.summary}" if weather_report else ""
            reply = f"收到，我按{weather_line}做了动态调整。下午取消长距离户外安排，改成室内文化体验和短距离散步；如果雨势变小，再保留一段轻松街区漫游。"
            reminders = [
                Reminder(timing="出门前", title="雨具提醒", detail="带轻便雨衣，临水或老街区域比雨伞更稳。", priority="high"),
                Reminder(timing="晚餐前", title="预订提醒", detail="雨天热门室内餐厅更容易满座，建议提前确认。"),
            ]
        else:
            cities = await self._route(destination, days, avoid, profile, request.message)
            itinerary = self._build_itinerary(destination, cities, days, budget, avoid=avoid)
            itinerary.summary = "已根据你的需求调整行程，避开了你指定的地点。"
            itinerary.highlights = [plan.city for plan in itinerary.day_plans[:4]]
            if weather_report:
                for i, plan in enumerate(itinerary.day_plans):
                    plan.weather_tip = weather_service.weather_tip(weather_report, i)
            removed_spots = [spot for spot in avoid if spot in CITY_LIBRARY.get(destination, [])]
            if removed_spots:
                reply = f"好的，已从行程中移除{'、'.join(removed_spots)}，调整后的路线主轴是 {' -> '.join(cities)}。"
            else:
                reply = f"已根据你的需求调整行程，新的路线主轴是 {' -> '.join(cities)}。"
            reminders = [
                Reminder(timing="每天20:00", title="次日优化", detail="根据天气、人流和体力反馈微调第二天行程。"),
            ]

        # map markers for adjusted itinerary
        map_markers: list[MapMarker] = []
        for i, plan in enumerate(itinerary.day_plans):
            center = geo.city_center(destination)
            if center:
                try:
                    lng_str, lat_str = center.split(",")
                    map_markers.append(MapMarker(
                        name=plan.city,
                        lng=float(lng_str) + i * 0.01, lat=float(lat_str) + i * 0.005,
                        day=plan.day, theme=plan.theme,
                        morning=plan.morning, afternoon=plan.afternoon,
                        evening=plan.evening, transport=plan.transport,
                    ))
                except (ValueError, TypeError):
                    pass

        return ChatResponse(
            session_id=session_id,
            reply=reply,
            itinerary=itinerary,
            memory_hits=[MemoryHit(**hit) for hit in memory_hits],
            reminders=reminders,
            quick_actions=["确认这个调整", "继续避开商业街", "帮我生成明天备用方案"],
            weather=weather_info,
            map_markers=map_markers,
            debug={"intent": "adjust", "destination": destination, "weather_available": weather_info is not None, "interpreter": interpretation.get("provider", "rules")},
        )

    @staticmethod
    def _not_collected_response(
        session_id: str,
        destination: str | None,
        memory_hits: list[dict[str, str]],
        interpretation: dict,
        missing_destination: bool = False,
    ) -> ChatResponse:
        if missing_destination:
            reply = f"请先输入一个已收录城市。目前只收录：{SUPPORTED_CITY_TEXT}。"
            display_destination = None
        else:
            reply = f"{destination}暂未收录。目前只支持这 10 个城市：{SUPPORTED_CITY_TEXT}。"
            display_destination = destination
        return ChatResponse(
            session_id=session_id,
            reply=reply,
            itinerary=None,
            memory_hits=[MemoryHit(**hit) for hit in memory_hits],
            reminders=[],
            quick_actions=[f"{city}3天小众路线" for city in SUPPORTED_CITIES[:3]],
            debug={
                "intent": "not_collected",
                "destination": display_destination,
                "supported_cities": list(SUPPORTED_CITIES),
                "interpreter": interpretation.get("provider", "rules"),
                "collected": False,
            },
        )

    @staticmethod
    def _is_adjustment(message: str, interpretation: dict | None = None) -> bool:
        if interpretation and interpretation.get("intent") == "adjust":
            return True
        return any(word in message for word in ("调整", "改", "下雨", "天气不好", "取消", "替代", "不去", "不要去"))

    @staticmethod
    def _extract_destination(message: str, interpretation: dict | None = None) -> str | None:
        if interpretation:
            destination = _clean_destination(interpretation.get("destination"))
            if destination:
                return destination

        for destination in sorted(SUPPORTED_CITIES, key=len, reverse=True):
            if destination in message:
                return destination

        patterns = [
            r"([\u4e00-\u9fa5]{2,8})\s*(?:\d{1,2}|[一二三四五六七八九十两]+)\s*[天日]",
            r"(?:想去|去|到|游|玩)([\u4e00-\u9fa5]{2,8})(?:\d{1,2}|[一二三四五六七八九十两]|周末|五一|国庆|春节|，|,|。|；|;|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                destination = _clean_destination(match.group(1))
                if destination:
                    return destination
        return None

    @staticmethod
    def _extract_days(message: str, interpretation: dict | None = None) -> int | None:
        if interpretation and interpretation.get("days"):
            try:
                return max(1, min(int(interpretation["days"]), 14))
            except (TypeError, ValueError):
                pass
        match = re.search(r"(\d{1,2})\s*[天日]", message)
        if match:
            return max(1, min(int(match.group(1)), 14))
        chinese_numbers = {"两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7}
        for word, value in chinese_numbers.items():
            if f"{word}天" in message or f"{word}日" in message:
                return value
        return None

    @staticmethod
    def _extract_budget(message: str, interpretation: dict | None = None) -> int | None:
        if interpretation and interpretation.get("budget"):
            try:
                return int(float(interpretation["budget"]))
            except (TypeError, ValueError):
                pass
        match = re.search(r"预算(?:大概|约|是|控制在)?\s*(\d{3,6})", message)
        if match:
            return int(match.group(1))
        match = re.search(r"(\d+(?:\.\d+)?)\s*(千|万)", message)
        if not match:
            return None
        amount = float(match.group(1))
        unit = match.group(2)
        return int(amount * (1000 if unit == "千" else 10000))

    async def _route(self, destination: str, days: int, avoid: list[str] | None = None, profile: dict = None, message: str = "") -> list[str]:
        all_spots = CITY_LIBRARY[destination].copy()
        if not all_spots:
            return []

        if not self.llm_recommender:
            ranked = rank_spots_for_request(destination, message, days, avoid=avoid, profile=profile)
            return ranked[:days]

        # ── extract wanted tags from user message ──
        wanted_tags: set[str] = set()
        msg_wanted_tags: set[str] = set()  # explicit want from message (for conflict resolution)
        for kw, tag in KEYWORD_TAG_MAP.items():
            if kw in message:
                wanted_tags.add(tag)
                msg_wanted_tags.add(tag)

        # ── extract "want" signals from message (喜欢/偏好/想要) for conflict override ──
        import re as _re
        for pattern in (r"喜欢([^，。,.；;]+)", r"偏好([^，。,.；;]+)", r"想要([^，。,.；;]+)"):
            for match in _re.findall(pattern, message):
                for kw, mapped in KEYWORD_TAG_MAP.items():
                    if kw in match:
                        msg_wanted_tags.add(mapped)

        # ── extract avoid tags from user message (不去X / 不要X / 避开X / 不喜欢X) ──
        avoid_tags: set[str] = set()
        for pattern in (r"不去([^，。,.；;]+)", r"不要([^，。,.；;]+)", r"避开([^，。,.；;]+)", r"不喜欢([^，。,.；;]+)"):
            for match in _re.findall(pattern, message):
                for kw, mapped in KEYWORD_TAG_MAP.items():
                    if kw in match:
                        avoid_tags.add(mapped)

        # ── pull avoid tags from stored preferences (避开X / 不喜欢X / 讨厌X) ──
        pref_avoid_tags: set[str] = set()
        for tag in (profile or {}).get("tags", []):
            if any(p in tag for p in ("避开", "不喜欢", "讨厌")):
                for kw, mapped in KEYWORD_TAG_MAP.items():
                    if kw in tag:
                        pref_avoid_tags.add(mapped)

        # ── conflict resolution: user message wins over stored preferences ──
        for t in pref_avoid_tags:
            if t not in msg_wanted_tags:  # only apply if user doesn't explicitly want it
                avoid_tags.add(t)

        # ── score & filter spots ──
        scored: list[tuple[str, int]] = []
        for spot_name in all_spots:
            spot_tags = SPOT_TAGS.get(spot_name, [])
            # filter: skip if spot has any avoid tag
            if avoid_tags and any(t in spot_tags for t in avoid_tags):
                continue
            # score: tag overlap with wanted keywords
            score = sum(1 for t in spot_tags if t in wanted_tags)
            scored.append((spot_name, score))

        # sort by relevance, then preserve original order for ties
        scored.sort(key=lambda x: (-x[1], all_spots.index(x[0])))
        ranked = [s[0] for s in scored]

        # also filter by avoid strings from user message
        if avoid:
            ranked = [s for s in ranked if not any(a in s or s in a for a in avoid)]

        # ── build route ──
        base = ranked[:days]
        needed = days - len(base)

        # fill gaps with LLM recommendations
        if needed > 0 and self.llm_recommender:
            preferences = (profile or {}).get("tags", [])
            recommended = await self.llm_recommender.recommend_attractions(
                destination, needed + 5, base + ranked, preferences
            )
            for spot in (recommended or []):
                if spot not in base:
                    base.append(spot)
                    needed -= 1
                    if needed <= 0:
                        break

        # second LLM pass if still short
        if needed > 0 and self.llm_recommender:
            retry = await self.llm_recommender.recommend_attractions(
                destination, needed + 5, base + ranked, preferences
            )
            for spot in (retry or []):
                if spot not in base:
                    base.append(spot)
                    needed -= 1
                    if needed <= 0:
                        break

        # last resort variants
        if needed > 0:
            variants = ["深度探索", "慢游日", "漫游日", "自由日", "休整日"]
            source = base if base else ranked
            for i in range(needed):
                base.append(f"{source[i % len(source)]}·{variants[i % len(variants)]}")

        return base[:days]

    @staticmethod
    def _avoid_list(profile: dict, message: str, interpretation: dict | None = None) -> list[str]:
        avoid = ["高密度商业街", "纯打卡景点"]
        tags = profile.get("tags", [])
        if any("商业化" in tag for tag in tags) or "商业化" in message:
            avoid.append("过度商业化景点")
        if "人多" in message or "小众" in message:
            avoid.append("节假日核心人流")
        for item in (interpretation or {}).get("avoid", []) or []:
            cleaned = str(item).strip()
            if cleaned:
                avoid.append(cleaned)
        
        for pattern in (r"不去([\u4e00-\u9fa5]+)", r"不要去([\u4e00-\u9fa5]+)", r"避开([\u4e00-\u9fa5]+)"):
            for match in re.findall(pattern, message):
                spot = match.strip()
                if spot and len(spot) >= 2:
                    avoid.append(spot)
        
        return sorted(set(avoid))

    def _build_itinerary(
        self,
        destination: str,
        cities: list[str],
        days: int,
        budget: int | None,
        avoid: list[str],
    ) -> Itinerary:
        day_plans = []
        for index in range(days):
            city = cities[index % len(cities)]
            if city in SCENE_BANK:
                morning, afternoon, evening = SCENE_BANK[city]
            else:
                morning = f"{city}上午游览"
                afternoon = f"{city}深度体验"
                evening = f"{city}周边美食"
            day_plans.append(
                DayPlan(
                    day=index + 1,
                    city=city,
                    theme=self._theme_for(index),
                    morning=morning,
                    afternoon=afternoon,
                    evening=evening,
                    transport=self._transport_for(index, destination),
                    weather_tip=self._weather_tip_for(destination),
                )
            )
        return Itinerary(
            title=f"{destination}{days}天智能行程",
            destination=destination,
            days=days,
            budget=budget,
            summary="基于已收录城市库、自然语言约束、历史偏好和避雷记忆生成，可继续通过对话调整。",
            day_plans=day_plans,
            avoid=avoid,
            highlights=[plan.city for plan in day_plans[:4]],
        )

    @staticmethod
    def _theme_for(index: int) -> str:
        themes = ["抵达适应", "小众探索", "文化慢游", "城市散步", "弹性收尾"]
        return themes[index % len(themes)]

    @staticmethod
    def _transport_for(index: int, destination: str) -> str:
        if index == 0:
            return "抵达后优先使用地铁/网约车，减少第一天换乘压力。"
        if destination in {"桂林", "重庆", "西安"}:
            return "跨区移动预留缓冲，热门景区建议提前确认返程交通。"
        return "城市内以步行、地铁、公交和短途打车为主。"

    @staticmethod
    def _weather_tip_for(destination: str) -> str:
        if destination in {"广州", "桂林", "重庆", "长沙"}:
            return "湿热或阵雨较常见，午后保留室内替代点。"
        if destination in {"北京", "西安"}:
            return "昼夜温差可能较大，保留外套并注意防晒。"
        return "出发前检查天气，午后安排可替换为室内体验。"

    @staticmethod
    def _build_reminders(destination: str, weather_report: WeatherReport | None = None) -> list[Reminder]:
        reminders: list[Reminder] = []

        if weather_report and weather_report.forecast:
            weather_detail = _weather_reminder_detail(destination, weather_report)
            reminders.append(Reminder(
                timing="行前3天",
                title="天气复核",
                detail=weather_detail,
                priority="high" if any(d.rain_prob > 60 for d in weather_report.forecast[:3]) else "normal",
            ))
        else:
            reminders.append(Reminder(
                timing="行前3天",
                title="天气复核",
                detail=f"检查{destination}逐日天气，自动生成雨天备用方案。",
            ))

        reminders.append(Reminder(
            timing="行前1天",
            title="预约确认",
            detail="确认热门景点预约、第一段交通和住宿入住时间。",
        ))
        reminders.append(Reminder(
            timing="每天20:00",
            title="次日优化",
            detail="根据天气、人流和体力反馈微调第二天行程。",
        ))
        return reminders


def _weather_reminder_detail(destination: str, report: WeatherReport) -> str:
    parts: list[str] = []
    next3 = report.forecast[:3]
    rain_days = [d for d in next3 if d.rain_prob > 50]
    hot_days = [d for d in next3 if d.temp_high > 35]
    cold_days = [d for d in next3 if d.temp_low < 5]

    if rain_days:
        parts.append(f"未来{len(rain_days)}天有雨（{'、'.join(f'{d.date[-5:]}降水{d.rain_prob}%' for d in rain_days)}），已预生成室内备用方案")
    if hot_days:
        parts.append(f"{len(hot_days)}天高温{max(d.temp_high for d in hot_days):.0f}°C，建议避开正午户外活动")
    if cold_days:
        parts.append(f"气温低至{min(d.temp_low for d in cold_days):.0f}°C，注意保暖")

    if parts:
        return f"{destination}" + "；".join(parts) + "。"
    today = next3[0]
    return f"{destination}未来3天{today.weather}，{today.temp_low:.0f}~{today.temp_high:.0f}°C，适合出行。"


def _clean_destination(value: object) -> str | None:
    if not value:
        return None
    destination = str(value).strip(" ，。,.；;的了去玩游")
    if destination.endswith("市") and len(destination) > 2:
        destination = destination[:-1]
    if destination in DESTINATION_STOPWORDS:
        return None
    if any(word in destination for word in ("景点", "活动", "风光")):
        return None
    if len(destination) < 2 or len(destination) > 8:
        return None
    return destination


def _model_dump(model) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()

"""LangChain ReAct Agent-based travel planner.

Uses create_agent (LangChain >=1.0) with DeepSeek function calling to replace
the regex + keyword-matching logic in TravelPlanner with an LLM reasoning loop.
"""

from __future__ import annotations

import json
import os
from uuid import uuid4

from langchain.agents import create_agent, structured_output
from langchain_openai import ChatOpenAI

from app.models import ChatRequest, ChatResponse, DayPlan, Itinerary, MapMarker, MemoryHit, Reminder
from app.services.agent_tools import AGENT_TOOLS, FinalItineraryOutput, SUPPORTED_CITY_LIST
from app.services.config import load_env
from app.services.memory import TravelMemoryStore

load_env()

SUPPORTED_CITY_TEXT = "、".join(SUPPORTED_CITY_LIST)

SYSTEM_PROMPT = f"""\
你是一个专业的中国城市旅行规划助手。使用工具高效地搜索景点、查询天气、读取用户偏好，然后生成结构化行程。

## 工具使用原则
- 每次规划只调用每个工具最多一次，避免重复调用
- search_spots 一次获取所有所需景点，不要按标签分多次调用
- 先确认城市可用 → 查天气和偏好 → 搜索景点 → 立即输出
- 工具调用总数控制在 4-6 次

## 城市支持
目前只支持这 {len(SUPPORTED_CITY_LIST)} 个城市：{SUPPORTED_CITY_TEXT}。
先调用 get_supported_cities 确认目的地。**如果目的地不在列表中，必须直接告知用户，严禁推荐其他城市作为替代。** 输出 destination 为用户请求的城市名、days=0、空 day_plans。

## 标签筛选
景点标签：小众、商业、风景、自然、户外、历史文化、美食、夜景、亲子、网红、城市、室内、古镇、文创、免费、远郊。
根据用户偏好映射到标签，search_spots 时传入 tags 和 avoid_tags 一次性筛选。

## 日主题（按天数顺序）
第1天：抵达适应，第2天：小众探索，第3天：文化慢游，第4天：城市散步，第5天+：弹性收尾。

## 天气提示
获取天气后为每个 day_plan 添加 weather_tip（含温度和降水信息）。
rain_prob > 60%：建议室内替代 + 带雨具；temp_high > 35°C：避开正午；wind > 30：注意安全。

## 交通建议
第1天：地铁/网约车；桂林/重庆/西安：跨区预留缓冲；默认：步行+地铁+公交+短途打车。

## 一天一个景点
day_plans 必须严格等于 days，且每天只推荐一个主景点/片区。city 字段填写当天主景点名称，不要把多个景点用“+”“、”“/”拼在一起。上午、下午、晚上可以围绕同一个主景点安排不同活动，例如上午抵达与核心体验、下午周边深度游、晚上附近美食或夜景。

## 预算与地点特性
根据用户预算选择交通和活动强度：低预算优先免费/公共交通/本地小吃，中高预算可加入预约体验、打车和品质餐厅。根据地点标签解释推荐理由，例如网红适合拍照打卡，小众适合避开人流，历史文化适合博物馆和街区慢游。

## 调整已有行程
调用 get_last_itinerary 获取当前行程 → get_weather_forecast 获取天气 → 修改计划 → 输出。

## 输出要求
- reply：友好中文回复，提及天气和偏好匹配
- day_plans：每天包含 city, theme, morning, afternoon, evening, transport, weather_tip；每天只允许一个主景点名称
- reminders：3 条——行前3天天气复核、行前1天预约确认、每天20:00次日优化
- quick_actions：2-3 条上下文相关的快捷建议
- avoid / highlights 按需填充
"""

RETRY_SUFFIX = """

上一轮没有生成可解析的结构化结果。请立即重新输出，且必须使用 FinalItineraryOutput 结构化格式：
- 不要只输出普通文本
- day_plans 数量必须等于用户请求天数
- city 字段每天只能是一个主景点/片区名
"""


class AgentPlanner:
    """LangChain ReAct agent planner — replaces regex logic with LLM tool-calling."""

    def __init__(self, memory: TravelMemoryStore) -> None:
        self.memory = memory
        self._agent = self._build_agent()

    def _build_agent(self):
        llm = ChatOpenAI(
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/") + "/v1",
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            temperature=0.1,
            max_tokens=3000,
            extra_body={"thinking": {"type": "disabled"}},
        )

        return create_agent(
            model=llm,
            tools=AGENT_TOOLS,
            system_prompt=SYSTEM_PROMPT,
            response_format=structured_output.ToolStrategy(FinalItineraryOutput),
        )

    async def handle(self, request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or str(uuid4())

        # Update memory (same side effects as legacy TravelPlanner)
        remembered = self.memory.update_from_message(request.user_id, request.message)
        memory_hits = self.memory.search(request.user_id, request.message)
        all_hits = remembered + memory_hits if remembered else memory_hits

        # Quick pre-check: if user explicitly mentions an unsupported city, skip agent
        mentioned_city = self._extract_city_mention(request.message)
        if mentioned_city and mentioned_city not in SUPPORTED_CITY_LIST:
            return ChatResponse(
                session_id=session_id,
                reply=f"{mentioned_city}暂未收录。目前只支持这 {len(SUPPORTED_CITY_LIST)} 个城市：{SUPPORTED_CITY_TEXT}。",
                itinerary=None,
                memory_hits=[MemoryHit(**h) for h in all_hits],
                reminders=[],
                quick_actions=[f"{c}3天小众路线" for c in SUPPORTED_CITY_LIST[:3]],
                debug={
                    "intent": "not_collected",
                    "destination": mentioned_city,
                    "supported_cities": SUPPORTED_CITY_LIST,
                    "agent": "langchain-tool-calling",
                    "collected": False,
                },
            )

        # Embed context into the user message
        context_prefix = (
            f"[上下文: user_id=\"{request.user_id}\", session_id=\"{session_id}\"]\n\n"
        )
        augmented_message = context_prefix + request.message

        response: ChatResponse | None = None
        failure_reason = ""
        for attempt in range(2):
            message = augmented_message if attempt == 0 else augmented_message + RETRY_SUFFIX
            try:
                result = await self._agent.ainvoke(
                    {"messages": [{"role": "user", "content": message}]},
                    config={"recursion_limit": 30},
                )
            except Exception as exc:
                failure_reason = f"{type(exc).__name__}: {exc}"
                break

            response = self._parse_output(result, session_id, all_hits)
            if not response.debug.get("agent_failed"):
                response.debug["agent_attempts"] = attempt + 1
                break
            failure_reason = str(response.debug.get("reason", "no_structured_output"))
            response = None

        if response is None:
            return await self._fallback_to_rules(request, session_id, failure_reason)

        # Generate map markers from itinerary day plans
        if response.itinerary and response.itinerary.day_plans:
            response.map_markers = await self._build_map_markers(
                response.itinerary.destination, response.itinerary.day_plans
            )

        # Record interaction
        payload = response.model_dump() if hasattr(response, "model_dump") else response.dict()
        self.memory.record_interaction(request.user_id, session_id, request.message, payload)
        return response

    async def _fallback_to_rules(self, request: ChatRequest, session_id: str, reason: str) -> ChatResponse:
        from app.services.planner import TravelPlanner

        fallback_request = request.model_copy(update={"session_id": session_id})
        response = await TravelPlanner(self.memory, enable_remote_context=True).handle(fallback_request)
        if response.itinerary:
            response.reply = "Agent 本次输出不稳定，我已先用本地规则引擎生成一版稳定行程。" + response.reply
        response.debug.update({
            "agent": "langchain-tool-calling",
            "agent_failed": True,
            "agent_fallback": "rules",
            "agent_failure_reason": reason,
        })
        return response

    @staticmethod
    def _extract_city_mention(message: str) -> str | None:
        """Quick check if message mentions a specific city."""
        for city in sorted(SUPPORTED_CITY_LIST, key=len, reverse=True):
            if city in message:
                return city
        # Also check for non-supported Chinese cities by pattern
        import re
        match = re.search(r"([一-龥]{2,3})(?:\d{1,2}|[一二三四五六七八九十两]+)\s*[天日]", message)
        if match:
            candidate = match.group(1).rstrip("市")
            if candidate not in SUPPORTED_CITY_LIST and len(candidate) >= 2:
                return candidate
        return None

    @staticmethod
    async def _build_map_markers(destination: str, day_plans: list) -> list:
        """Geocode day plan cities and build map markers."""
        from app.services.geo import geo
        from app.models import FoodPOI, MapMarker

        markers: list = []
        for i, plan in enumerate(day_plans):
            city_name = plan.city if hasattr(plan, "city") else plan["city"]
            coord = await geo.geocode(city_name, destination)
            foods: list = []
            if coord:
                try:
                    food_pois = await geo.search_foods(coord[0], coord[1], count=5)
                    foods = [FoodPOI(name=f.name, address=f.address, category=f.category) for f in food_pois]
                except Exception:
                    pass

            day = plan.day if hasattr(plan, "day") else plan["day"]
            theme = plan.theme if hasattr(plan, "theme") else plan.get("theme", "")
            morning = plan.morning if hasattr(plan, "morning") else plan.get("morning", "")
            afternoon = plan.afternoon if hasattr(plan, "afternoon") else plan.get("afternoon", "")
            evening = plan.evening if hasattr(plan, "evening") else plan.get("evening", "")
            transport = plan.transport if hasattr(plan, "transport") else plan.get("transport", "")

            if coord:
                markers.append(MapMarker(
                    name=city_name, lng=coord[0], lat=coord[1],
                    day=day, theme=theme,
                    morning=morning, afternoon=afternoon, evening=evening,
                    transport=transport, nearby_foods=foods,
                ))
            else:
                center = geo.city_center(destination)
                if center:
                    try:
                        lng_str, lat_str = center.split(",")
                        markers.append(MapMarker(
                            name=city_name,
                            lng=float(lng_str) + i * 0.01, lat=float(lat_str) + i * 0.005,
                            day=day, theme=theme,
                            morning=morning, afternoon=afternoon, evening=evening,
                            transport=transport,
                        ))
                    except (ValueError, TypeError):
                        pass
        return markers

    @staticmethod
    def _parse_output(
        agent_result: dict,
        session_id: str,
        memory_hits: list[dict],
    ) -> ChatResponse:
        """Extract FinalItineraryOutput from agent tool calls and build ChatResponse."""
        messages = agent_result.get("messages", [])

        structured_response = agent_result.get("structured_response")
        if structured_response:
            if hasattr(structured_response, "model_dump"):
                final_data = structured_response.model_dump()
            elif isinstance(structured_response, dict):
                final_data = structured_response
            else:
                final_data = {}
        else:
            final_data = None

        # Find the final structured output from ToolStrategy
        # ToolStrategy binds FinalItineraryOutput as a tool; look for its call
        if not final_data:
            for msg in reversed(messages):
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        if tc.get("name") == "FinalItineraryOutput":
                            final_data = tc.get("args", {})
                            break
                if final_data:
                    break

        if not final_data:
            # Fallback: check ToolMessage content for "Returning structured response:"
            for msg in reversed(messages):
                content = str(getattr(msg, "content", ""))
                if "Returning structured response:" in content:
                    prefix = "Returning structured response: "
                    json_str = content[content.index(prefix) + len(prefix):].strip()
                    try:
                        final_data = json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
                    break

        if not final_data:
            # Log what we got for debugging
            last_content = ""
            for msg in reversed(messages):
                if hasattr(msg, "content") and msg.content:
                    last_content = str(msg.content)[:200]
                    break
            return ChatResponse(
                session_id=session_id,
                reply="抱歉，我暂时无法完成这个规划。请尝试重新描述您的需求。",
                itinerary=None,
                memory_hits=[MemoryHit(**h) for h in memory_hits],
                reminders=[],
                quick_actions=[],
                debug={
                    "intent": "error",
                    "agent_failed": True,
                    "reason": f"no_structured_output (last_msg: {last_content})",
                },
            )

        # Build DayPlan list
        day_plans = []
        for dp in final_data.get("day_plans", []):
            day_plans.append(DayPlan(
                day=dp.get("day", 1),
                city=_single_spot_name(dp.get("city", "")),
                theme=dp.get("theme", ""),
                morning=dp.get("morning", ""),
                afternoon=dp.get("afternoon", ""),
                evening=dp.get("evening", ""),
                transport=dp.get("transport", ""),
                weather_tip=dp.get("weather_tip", ""),
            ))

        # Build Reminder list
        reminders = []
        for r in final_data.get("reminders", []):
            reminders.append(Reminder(
                timing=r.get("timing", ""),
                title=r.get("title", ""),
                detail=r.get("detail", ""),
                priority=r.get("priority", "normal"),
            ))

        destination = final_data.get("destination", "")
        days = final_data.get("days", len(day_plans))
        budget = final_data.get("budget")

        itinerary = Itinerary(
            title=f"{destination}{days}天智能行程",
            destination=destination,
            days=days,
            budget=budget,
            summary=f"AI Agent 基于偏好、天气和 {len(day_plans)} 个景点生成。",
            day_plans=day_plans,
            avoid=final_data.get("avoid", []),
            highlights=final_data.get("highlights", []),
        )

        hit_models = [MemoryHit(**h) for h in memory_hits]

        return ChatResponse(
            session_id=session_id,
            reply=final_data.get("reply", ""),
            itinerary=itinerary,
            memory_hits=hit_models,
            reminders=reminders,
            quick_actions=final_data.get("quick_actions", []),
            weather=None,
            nearby_pois=[],
            map_markers=[],
            debug={
                "intent": "plan",
                "destination": destination,
                "days": days,
                "agent": "langchain-tool-calling",
            },
        )


def _single_spot_name(value: object) -> str:
    name = str(value or "").strip()
    for sep in ("+", "＋", "、", "/", "／", "，", ",", "和", "与"):
        if sep in name:
            name = name.split(sep, 1)[0].strip()
    return name

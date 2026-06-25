import tempfile
import unittest
from pathlib import Path

from app.models import ChatRequest
from app.services.agent_planner import AgentPlanner, _single_spot_name
from app.services.agent_tools import DayPlanOutput, FinalItineraryOutput, ReminderOutput
from app.services.memory import TravelMemoryStore


class FakeAgent:
    def __init__(self, results: list[dict]) -> None:
        self.results = results
        self.calls: list[dict] = []

    async def ainvoke(self, payload: dict, config: dict | None = None) -> dict:
        self.calls.append(payload)
        return self.results.pop(0)


def test_agent_parse_output_uses_langchain_structured_response() -> None:
    structured = FinalItineraryOutput(
        reply="已生成广州2天小众路线。",
        destination="广州",
        days=2,
        day_plans=[
            DayPlanOutput(
                day=1,
                city="黄埔古港",
                theme="小众探索",
                morning="古港村慢走",
                afternoon="黄埔村小店",
                evening="回市区吃清淡粤菜",
                transport="地铁+短途打车",
                weather_tip="有雨，带雨具。",
            ),
            DayPlanOutput(
                day=2,
                city="沙湾古镇",
                theme="文化慢游",
                morning="清晨入园",
                afternoon="广东音乐馆",
                evening="古镇夜色",
                transport="地铁+公交",
                weather_tip="午后留室内备选。",
            ),
        ],
        avoid=["人多", "商业化"],
        highlights=["黄埔古港", "沙湾古镇"],
        reminders=[
            ReminderOutput(timing="行前3天", title="天气复核", detail="确认降雨。"),
        ],
        quick_actions=["继续避开商业街"],
    )

    response = AgentPlanner._parse_output(
        {"structured_response": structured, "messages": []},
        session_id="agent-structured",
        memory_hits=[],
    )

    assert response.itinerary is not None
    assert response.reply == "已生成广州2天小众路线。"
    assert response.itinerary.destination == "广州"
    assert [plan.city for plan in response.itinerary.day_plans] == ["黄埔古港", "沙湾古镇"]
    assert response.debug["agent"] == "langchain-tool-calling"


def test_single_spot_name_removes_joined_spots() -> None:
    assert _single_spot_name("广州老城+沙面") == "广州老城"
    assert _single_spot_name("黄埔古港、沙湾古镇") == "黄埔古港"


class AgentPlannerRetryTest(unittest.IsolatedAsyncioTestCase):
    async def test_agent_retries_when_first_result_has_no_structured_output(self) -> None:
        structured = FinalItineraryOutput(
            reply="已生成广州2天小众路线。",
            destination="广州",
            days=2,
            day_plans=[
                DayPlanOutput(
                    day=1,
                    city="沙面",
                    theme="小众探索",
                    morning="沙面建筑群慢走",
                    afternoon="沿江西路周边",
                    evening="珠江边散步",
                    transport="地铁+步行",
                    weather_tip="有雨，带雨具。",
                ),
                DayPlanOutput(
                    day=2,
                    city="黄埔古港",
                    theme="文化慢游",
                    morning="古港村和粤海第一关",
                    afternoon="黄埔村小店",
                    evening="回市区吃粤菜",
                    transport="地铁+短途打车",
                    weather_tip="午后留室内备选。",
                ),
            ],
            avoid=["人多", "商业化"],
            highlights=["沙面", "黄埔古港"],
            reminders=[],
            quick_actions=["继续避开商业街"],
        )

        with tempfile.TemporaryDirectory() as tmp:
            planner = AgentPlanner.__new__(AgentPlanner)
            planner.memory = TravelMemoryStore(Path(tmp))
            planner._agent = FakeAgent([
                {"messages": []},
                {"structured_response": structured, "messages": []},
            ])

            response = await planner.handle(ChatRequest(
                user_id="demo-user",
                session_id="agent-retry",
                message="广州2天去小众景点，避开人多和商业化景点",
                mode="agent",
            ))

        assert response.itinerary is not None
        assert response.debug["agent_attempts"] == 2
        assert [plan.city for plan in response.itinerary.day_plans] == ["沙面", "黄埔古港"]
        assert len(planner._agent.calls) == 2

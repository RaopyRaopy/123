from pathlib import Path
import unittest

from app.models import ChatRequest
from app.services.memory import TravelMemoryStore
from app.services.planner import SUPPORTED_CITIES, TravelPlanner


TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".test-tmp"


def build_planner(name: str) -> TravelPlanner:
    TEST_TMP_ROOT.mkdir(exist_ok=True)
    data_dir = TEST_TMP_ROOT / name
    data_dir.mkdir(exist_ok=True)
    # clean any leftover files
    for f in data_dir.glob("*.json"):
        f.unlink()
    memory = TravelMemoryStore(data_dir)
    return TravelPlanner(memory)


class PlannerTest(unittest.IsolatedAsyncioTestCase):
    async def test_all_supported_cities_can_generate_plan(self) -> None:
        for city in SUPPORTED_CITIES:
            with self.subTest(city=city):
                planner = build_planner(f"mem-{city}")
                response = await planner.handle(ChatRequest(message=f"{city}1天小众路线", session_id=f"s-{city}"))

                self.assertIsNotNone(response.itinerary)
                self.assertEqual(response.itinerary.destination, city)
                self.assertEqual(response.itinerary.days, 1)
                self.assertTrue(response.debug["collected"])

    async def test_guangzhou_request_does_not_fall_back_to_other_city(self) -> None:
        planner = build_planner("mem-guangzhou")
        response = await planner.handle(ChatRequest(message="广州2天去小众景点", session_id="s3"))

        self.assertIsNotNone(response.itinerary)
        self.assertEqual(response.itinerary.destination, "广州")
        self.assertEqual(response.itinerary.days, 2)
        self.assertEqual([plan.city for plan in response.itinerary.day_plans], ["广州老城", "沙面"])

    async def test_guangzhou_avoid_crowds_and_commercial_uses_local_tags(self) -> None:
        planner = build_planner("mem-guangzhou-avoid")
        response = await planner.handle(
            ChatRequest(message="广州2天去小众景点，避开人多和商业化景点", session_id="s7")
        )

        self.assertIsNotNone(response.itinerary)
        self.assertEqual(response.itinerary.destination, "广州")
        self.assertEqual(response.itinerary.days, 2)
        self.assertEqual([plan.city for plan in response.itinerary.day_plans], ["广州老城", "沙面"])
        self.assertNotIn("广州塔与花城广场", response.itinerary.highlights)

    async def test_city_name_with_suffix_is_supported(self) -> None:
        planner = build_planner("mem-beijing")
        response = await planner.handle(ChatRequest(message="北京市2天历史文化路线", session_id="s6"))

        self.assertIsNotNone(response.itinerary)
        self.assertEqual(response.itinerary.destination, "北京")
        self.assertEqual(response.itinerary.days, 2)

    async def test_uncollected_city_returns_not_collected(self) -> None:
        planner = build_planner("mem-uncollected")
        response = await planner.handle(ChatRequest(message="深圳2天去小众景点", session_id="s4"))

        self.assertIsNone(response.itinerary)
        self.assertEqual(response.debug["intent"], "not_collected")
        self.assertEqual(response.debug["destination"], "深圳")
        self.assertIn("暂未收录", response.reply)

    async def test_missing_city_asks_for_supported_city(self) -> None:
        planner = build_planner("mem-missing")
        response = await planner.handle(ChatRequest(message="想去小众景点，预算3000", session_id="s5"))

        self.assertIsNone(response.itinerary)
        self.assertEqual(response.debug["intent"], "not_collected")
        self.assertIsNone(response.debug["destination"])
        self.assertIn("请先输入一个已收录城市", response.reply)

    async def test_rainy_adjustment_uses_existing_supported_city(self) -> None:
        planner = build_planner("mem-adjust")
        await planner.handle(ChatRequest(message="广州2天去小众景点", session_id="s2"))
        response = await planner.handle(ChatRequest(message="今天广州下雨了，想改成室内活动", session_id="s2"))

        self.assertIsNotNone(response.itinerary)
        self.assertEqual(response.itinerary.destination, "广州")
        self.assertEqual(response.debug["intent"], "adjust")
        self.assertTrue(any(reminder.priority == "high" for reminder in response.reminders))


if __name__ == "__main__":
    unittest.main()

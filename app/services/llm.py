from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx


from app.services.config import load_env as load_local_env, env


class OllamaClient:
    """Optional adapter for a local Qwen model served by Ollama."""

    def __init__(self) -> None:
        load_local_env()
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        self.enabled = os.getenv("SMART_TRIP_USE_OLLAMA", "0") == "1"

    async def status(self) -> dict[str, str | bool]:
        if not self.enabled:
            return {"enabled": False, "model": self.model, "status": "disabled"}
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
        except httpx.HTTPError as exc:
            return {"enabled": True, "model": self.model, "status": f"unavailable: {exc}"}
        return {"enabled": True, "model": self.model, "status": "ready"}

    async def generate(self, prompt: str) -> str | None:
        if not self.enabled:
            return None
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError:
            return None
        return data.get("response")


class DeepSeekClient:
    """OpenAI-compatible DeepSeek adapter for travel intent parsing."""

    def __init__(self) -> None:
        load_local_env()
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
        self.enabled = bool(self.api_key) and os.getenv("SMART_TRIP_USE_DEEPSEEK", "1") != "0"
        self.last_error = ""

    async def status(self) -> dict[str, str | bool]:
        if not self.enabled:
            return {"enabled": False, "model": self.model, "status": "disabled"}
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=self._payload("只返回JSON：{\"ok\":true}"),
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                self.last_error = f"auth failed ({exc.response.status_code}): check DEEPSEEK_API_KEY"
                return {"enabled": True, "model": self.model, "status": self.last_error}
            self.last_error = str(exc)
            return {"enabled": True, "model": self.model, "status": f"unavailable: {exc}"}
        except httpx.HTTPError as exc:
            self.last_error = str(exc)
            return {"enabled": True, "model": self.model, "status": f"unavailable: {exc}"}
        self.last_error = ""
        return {"enabled": True, "model": self.model, "status": "ready"}

    async def interpret_travel_request(self, message: str) -> dict[str, Any]:
        if not self.enabled:
            return {}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=self._payload(message),
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            self.last_error = f"HTTP {exc.response.status_code}"
            return {}
        except httpx.HTTPError as exc:
            self.last_error = str(exc)
            return {}

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = self._parse_json(content)
        if parsed:
            parsed["provider"] = "deepseek"
        self.last_error = ""
        return parsed

    async def recommend_attractions(
        self, destination: str, count: int, existing_spots: list[str], preferences: list[str] = None
    ) -> list[str]:
        if not self.enabled:
            return []
        preferences = preferences or []
        if len(preferences) > 5:
            preferences = preferences[:5]
        prompt = (
            f"推荐{count}个{destination}的特色景点，要求：\n"
            f"1. 不重复已有的景点：{','.join(existing_spots)}\n"
            f"2. 偏好：{','.join(preferences) if preferences else '无特殊偏好'}\n"
            f"3. 只返回景点名称，用中文逗号分隔，不要解释。\n"
            f"4. 每个推荐必须是{destination}市范围内的真实景点，不要推荐其他城市的景点。"
        )
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "你是旅行景点推荐专家，精通中国各大城市的旅游景点。"},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.7,
                        "stream": False,
                        "max_tokens": 200,
                    },
                )
                response.raise_for_status()
                data = response.json()
                msg = data.get("choices", [{}])[0].get("message", {})
                content = msg.get("content", "")
                reasoning = msg.get("reasoning_content", "")

                spots = []
                if content and content.strip():
                    spots = [s.strip() for s in content.split(",") if s.strip()]
                if not spots and reasoning:
                    pattern = (
                        r"([一-龥]+森林公园|[一-龥]+湿地公园|"
                        r"[一-龥]+国家森林公园|[一-龥]+村|"
                        r"[一-龥]+山|[一-龥]+岛|[一-龥]+古港|"
                        r"[一-龥]+古镇|[一-龥]+祠|[一-龥]+塔|"
                        r"[一-龥]+湖|[一-龥]+湾)"
                    )
                    matches = re.findall(pattern, reasoning)
                    spots = [m.strip() for m in matches if m.strip()]
                spots = list(dict.fromkeys(spots))
                for existing in existing_spots:
                    spots = [s for s in spots if existing not in s and s not in existing]
                return spots[:count]
        except Exception:
            return []

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _payload(self, message: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是旅行需求解析器，只输出JSON，不要解释。字段："
                        "intent(plan/adjust/memory), destination, days, budget, preferences, avoid。"
                        "目的地只允许解析为：重庆、北京、上海、成都、杭州、西安、广州、桂林、苏州、长沙；"
                        "如果用户输入其他城市，也原样放入destination，后端会判断暂未收录。"
                        "如果用户说'广州2天去小众景点'，destination必须是'广州'，days必须是2。"
                    ),
                },
                {"role": "user", "content": message},
            ],
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "temperature": 0.1,
            "stream": False,
            "max_tokens": 400,
        }

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        try:
            value = json.loads(content)
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.S)
            if not match:
                return {}
            try:
                value = json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
            return value if isinstance(value, dict) else {}

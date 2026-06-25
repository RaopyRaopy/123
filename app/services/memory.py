from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_USER: dict[str, Any] = {
    "profile": {"name": "", "tags": [], "budget_range": "", "companions": []},
    "trip_history": [],
    "feedback": [],
}

DEFAULT_SESSIONS: dict[str, Any] = {}


class TravelMemoryStore:

    def __init__(self, data_dir: Path | None = None) -> None:
        root = Path(__file__).resolve().parents[2]
        base = data_dir or root / "data"
        base.mkdir(parents=True, exist_ok=True)
        self._prefs_path = base / "user_preferences.json"
        self._sessions_path = base / "chat_sessions.json"
        self._prefs = self._load(self._prefs_path, {"users": {"demo-user": deepcopy(DEFAULT_USER)}})
        self._sessions = self._load(
            self._sessions_path, {"users": {"demo-user": deepcopy(DEFAULT_SESSIONS)}}
        )

    # ── file I/O ──

    @staticmethod
    def _load(path: Path, default: dict) -> dict:
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return default
        data.setdefault("users", {})
        data["users"].setdefault("demo-user", {})
        return data

    def _save(self) -> None:
        with self._prefs_path.open("w", encoding="utf-8") as f:
            json.dump(self._prefs, f, ensure_ascii=False, indent=2)
        with self._sessions_path.open("w", encoding="utf-8") as f:
            json.dump(self._sessions, f, ensure_ascii=False, indent=2)

    # ── user access ──

    def user(self, user_id: str) -> dict[str, Any]:
        """Return combined view of preferences + sessions for a user."""
        p = self._prefs.setdefault("users", {}).setdefault(user_id, deepcopy(DEFAULT_USER))
        s = self._sessions.setdefault("users", {}).setdefault(user_id, deepcopy(DEFAULT_SESSIONS))
        return {**p, "sessions": s}

    def profile(self, user_id: str) -> dict[str, Any]:
        return self._prefs.setdefault("users", {}).setdefault(
            user_id, deepcopy(DEFAULT_USER)
        )["profile"]

    # ── preferences ──

    def update_from_message(self, user_id: str, message: str) -> list[dict[str, str]]:
        profile = self.profile(user_id)
        tags: list = profile.setdefault("tags", [])
        new_items: list[dict[str, str]] = []

        for pattern in (r"喜欢([^，。,.；;]+)", r"偏好([^，。,.；;]+)", r"想要([^，。,.；;]+)"):
            for match in re.findall(pattern, message):
                value = self._clean_fragment(match)
                if value and value not in tags:
                    tags.append(value)
                    new_items.append({"kind": "preference", "title": "新增偏好", "detail": value})

        for pattern in (r"不喜欢([^，。,.；;]+)", r"讨厌([^，。,.；;]+)", r"避开([^，。,.；;]+)"):
            for match in re.findall(pattern, message):
                value = self._clean_fragment(match)
                negative = f"避开{value}"
                if value and negative not in tags:
                    tags.append(negative)
                    new_items.append({"kind": "preference", "title": "新增避雷", "detail": negative})

        budget = re.search(r"预算(?:大概|约|是)?\s*(\d{3,6})", message)
        if budget:
            profile["budget_range"] = budget.group(1)
            new_items.append({"kind": "budget", "title": "更新预算", "detail": budget.group(1)})

        if any(word in message for word in ("上次", "之前", "去过")) and any(
            word in message for word in ("不喜欢", "踩坑", "太商业化", "很好", "很棒")
        ):
            user = self._prefs.setdefault("users", {}).setdefault(user_id, deepcopy(DEFAULT_USER))
            user.setdefault("feedback", []).append(
                {"text": message, "created_at": datetime.now(timezone.utc).isoformat()}
            )
            new_items.append({"kind": "feedback", "title": "记录旅行反馈", "detail": message})

        if new_items:
            with self._prefs_path.open("w", encoding="utf-8") as f:
                json.dump(self._prefs, f, ensure_ascii=False, indent=2)
        return new_items

    def search(self, user_id: str, query: str, limit: int = 4) -> list[dict[str, str]]:
        p = self._prefs.setdefault("users", {}).setdefault(user_id, deepcopy(DEFAULT_USER))
        tokens = self._tokens(query)
        hits: list[dict[str, str]] = []

        for tag in p.get("profile", {}).get("tags", []):
            score = self._score(tag, tokens)
            if score:
                hits.append({"kind": "profile", "title": "偏好记忆", "detail": tag, "score": score})

        for trip in p.get("trip_history", []):
            detail = (
                f"目的地：{trip.get('destination', '')}；"
                f"喜欢：{'、'.join(trip.get('liked', []))}；"
                f"避雷：{'、'.join(trip.get('disliked', []))}"
            )
            score = self._score(detail, tokens)
            if score:
                hits.append({"kind": "history", "title": "历史行程", "detail": detail, "score": score})

        for item in p.get("feedback", []):
            detail = item.get("text", "")
            score = self._score(detail, tokens)
            if score:
                hits.append({"kind": "feedback", "title": "用户反馈", "detail": detail, "score": score})

        hits.sort(key=lambda item: item["score"], reverse=True)
        return [{k: v for k, v in hit.items() if k != "score"} for hit in hits[:limit]]

    def clear_preferences(self, user_id: str) -> int:
        p = self._prefs.setdefault("users", {}).setdefault(user_id, deepcopy(DEFAULT_USER))
        tag_count = len(p.get("profile", {}).get("tags", []))
        fb_count = len(p.get("feedback", []))
        p["profile"]["tags"] = []
        p["feedback"] = []
        self._sessions.setdefault("users", {})[user_id] = deepcopy(DEFAULT_SESSIONS)
        self._save()
        return tag_count + fb_count

    # ── sessions ──

    def session(self, user_id: str, session_id: str) -> dict[str, Any]:
        s = self._sessions.setdefault("users", {}).setdefault(user_id, deepcopy(DEFAULT_SESSIONS))
        return s.setdefault(
            session_id,
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "messages": [],
                "last_itinerary": None,
            },
        )

    def record_interaction(
        self, user_id: str, session_id: str, user_message: str, assistant_payload: dict[str, Any]
    ) -> None:
        session = self.session(user_id, session_id)
        t = datetime.now(timezone.utc).isoformat()
        session.setdefault("messages", []).append({"role": "user", "content": user_message, "created_at": t})
        session["messages"].append({"role": "assistant", "content": assistant_payload.get("reply", ""), "created_at": t})
        if assistant_payload.get("itinerary"):
            session["last_itinerary"] = assistant_payload["itinerary"]
        with self._sessions_path.open("w", encoding="utf-8") as f:
            json.dump(self._sessions, f, ensure_ascii=False, indent=2)

    def last_itinerary(self, user_id: str, session_id: str) -> dict[str, Any] | None:
        return self.session(user_id, session_id).get("last_itinerary")

    # ── helpers ──

    @staticmethod
    def _clean_fragment(value: str) -> str:
        return value.strip(" ，。,.；;的了和以及")

    @staticmethod
    def _tokens(text: str) -> set[str]:
        words = set(re.findall(r"[A-Za-z0-9]+", text.lower()))
        for kw in [
            "重庆", "北京", "上海", "成都", "杭州", "西安", "广州", "桂林", "苏州", "长沙",
            "自然", "小众", "商业化", "预算", "情侣", "下雨", "室内", "美食", "博物馆", "骑行",
        ]:
            if kw in text:
                words.add(kw)
        return words

    @classmethod
    def _score(cls, text: str, tokens: set[str]) -> int:
        if not tokens:
            return 1
        return sum(1 for t in tokens if t in text.lower())

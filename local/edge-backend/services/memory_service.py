from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from config import settings
from services.db import db_session
from services.db_models import UserMemory, UserProfile


MEMORY_TYPES = {"semantic_fact", "episodic_event", "dynamic_observation"}
SOURCE_TYPES = {"explicit_user", "text_inference", "multimodal_observation"}
PROFILE_TEMPLATE = {
    "preferred_name": None,
    "interests": [],
    "communication_preferences": {},
    "important_people": [],
    "living_context": {},
    "routines": [],
    "support_preferences": [],
}


class MemoryError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass
class MemoryInput:
    user_id: str
    memory_type: str
    category: str
    normalized_key: str
    content: str
    source_type: str
    confidence: float
    importance: float
    structured_payload: dict | None = None
    expires_at: datetime | None = None
    source_session_id: str | None = None
    source_turn_id: int | None = None
    supersedes_memory_id: str | None = None


class MemoryService:
    def create_or_update_memory(self, memory_input: MemoryInput) -> UserMemory:
        self._validate_memory(memory_input)
        now = utc_now()
        with db_session() as session:
            existing = session.scalar(
                select(UserMemory)
                .where(UserMemory.user_id == memory_input.user_id)
                .where(UserMemory.normalized_key == memory_input.normalized_key)
                .where(UserMemory.status == "active")
            )
            if existing and self._same_memory(existing, memory_input):
                existing.last_seen_at = now
                existing.confidence = max(existing.confidence, self._clamp(memory_input.confidence))
                existing.importance = max(existing.importance, self._clamp(memory_input.importance))
                existing.updated_at = now
                memory = existing
            else:
                supersedes_id = memory_input.supersedes_memory_id
                if existing:
                    existing.status = "superseded"
                    existing.updated_at = now
                    supersedes_id = existing.memory_id
                memory = UserMemory(
                    user_id=memory_input.user_id,
                    memory_type=memory_input.memory_type,
                    category=memory_input.category,
                    normalized_key=memory_input.normalized_key,
                    content=memory_input.content.strip()[: settings.memory_single_item_max_chars],
                    structured_payload=memory_input.structured_payload or {},
                    source_type=memory_input.source_type,
                    confidence=self._clamp(memory_input.confidence),
                    importance=self._clamp(memory_input.importance),
                    status="active",
                    first_seen_at=now,
                    last_seen_at=now,
                    expires_at=memory_input.expires_at,
                    source_session_id=memory_input.source_session_id,
                    source_turn_id=memory_input.source_turn_id,
                    supersedes_memory_id=supersedes_id,
                    created_at=now,
                    updated_at=now,
                )
                session.add(memory)
                session.flush()
            self.materialize_profile(memory_input.user_id, db_session=session)
            return memory

    def load_active_memories(self, user_id: str, *, limit: int | None = None) -> list[UserMemory]:
        now = utc_now()
        with db_session() as session:
            query = (
                select(UserMemory)
                .where(UserMemory.user_id == user_id)
                .where(UserMemory.status == "active")
                .where((UserMemory.expires_at.is_(None)) | (UserMemory.expires_at > now))
                .order_by(UserMemory.importance.desc(), UserMemory.last_seen_at.desc())
            )
            if limit:
                query = query.limit(limit)
            return list(session.scalars(query).all())

    def expire_dynamic_memories(self, *, now: datetime | None = None) -> int:
        current = now or utc_now()
        with db_session() as session:
            memories = list(
                session.scalars(
                    select(UserMemory)
                    .where(UserMemory.status == "active")
                    .where(UserMemory.expires_at.is_not(None))
                    .where(UserMemory.expires_at <= current)
                ).all()
            )
            affected_users = {memory.user_id for memory in memories}
            for memory in memories:
                memory.status = "expired"
                memory.updated_at = current
            for user_id in affected_users:
                self.materialize_profile(user_id, db_session=session)
            return len(memories)

    def delete_memory(self, *, user_id: str, memory_id: str) -> bool:
        with db_session() as session:
            memory = session.get(UserMemory, memory_id)
            if not memory or memory.user_id != user_id:
                return False
            session.delete(memory)
            self.materialize_profile(user_id, db_session=session)
            return True

    def clear_user_memories(self, user_id: str) -> int:
        with db_session() as session:
            memories = list(session.scalars(select(UserMemory).where(UserMemory.user_id == user_id)).all())
            count = len(memories)
            for memory in memories:
                session.delete(memory)
            profile = self._ensure_profile(user_id, db_session=session)
            profile.stable_profile = empty_profile()
            profile.dynamic_summary = {}
            profile.version += 1
            profile.updated_at = utc_now()
            return count

    def materialize_profile(self, user_id: str, *, db_session=None) -> UserProfile:
        if db_session is not None:
            return self._materialize_profile_in_session(user_id, db_session)
        with globals()["db_session"]() as session:
            return self._materialize_profile_in_session(user_id, session)

    def build_compact_profile_text(self, user_id: str, *, max_chars: int | None = None) -> str:
        with db_session() as session:
            profile = session.get(UserProfile, user_id)
            if not profile:
                return ""
            return format_stable_profile(profile.stable_profile, max_chars=max_chars or settings.memory_core_profile_max_chars)

    def _materialize_profile_in_session(self, user_id: str, session) -> UserProfile:
        now = utc_now()
        profile = self._ensure_profile(user_id, db_session=session)
        active = list(
            session.scalars(
                select(UserMemory)
                .where(UserMemory.user_id == user_id)
                .where(UserMemory.status == "active")
                .where((UserMemory.expires_at.is_(None)) | (UserMemory.expires_at > now))
                .order_by(UserMemory.importance.desc(), UserMemory.last_seen_at.desc())
            ).all()
        )
        profile.stable_profile = materialize_stable_profile(active)
        profile.dynamic_summary = materialize_dynamic_summary(active)
        profile.version += 1
        profile.updated_at = now
        return profile

    def _ensure_profile(self, user_id: str, *, db_session) -> UserProfile:
        profile = db_session.get(UserProfile, user_id)
        if profile:
            return profile
        now = utc_now()
        profile = UserProfile(
            user_id=user_id,
            stable_profile=empty_profile(),
            dynamic_summary={},
            version=1,
            created_at=now,
            updated_at=now,
        )
        db_session.add(profile)
        db_session.flush()
        return profile

    @staticmethod
    def _validate_memory(memory_input: MemoryInput) -> None:
        if memory_input.memory_type not in MEMORY_TYPES:
            raise MemoryError("Unsupported memory type.")
        if memory_input.source_type not in SOURCE_TYPES:
            raise MemoryError("Unsupported memory source type.")
        if not memory_input.user_id or not memory_input.normalized_key.strip() or not memory_input.content.strip():
            raise MemoryError("Memory requires user, key, and content.")

    @staticmethod
    def _same_memory(existing: UserMemory, memory_input: MemoryInput) -> bool:
        return existing.content.strip() == memory_input.content.strip()

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))


def materialize_stable_profile(memories: list[UserMemory]) -> dict:
    profile = empty_profile()
    for memory in memories:
        if memory.memory_type != "semantic_fact" or memory.source_type == "multimodal_observation":
            continue
        if memory.confidence < 0.8:
            continue
        payload = memory.structured_payload or {}
        content = memory.content.strip()
        category = memory.category
        if category == "preferred_name":
            profile["preferred_name"] = payload.get("preferred_name") or content
        elif category == "interest":
            _append_unique(profile["interests"], payload.get("interest") or content)
        elif category == "communication_preference":
            key = str(payload.get("key") or memory.normalized_key).replace("communication:", "")
            profile["communication_preferences"][key] = payload.get("value") or content
        elif category == "important_person":
            _append_unique(profile["important_people"], payload or {"description": content})
        elif category == "living_context":
            key = str(payload.get("key") or memory.normalized_key).replace("living:", "")
            profile["living_context"][key] = payload.get("value") or content
        elif category == "routine":
            _append_unique(profile["routines"], payload or {"description": content})
        elif category == "support_preference":
            _append_unique(profile["support_preferences"], payload or {"description": content})
    return profile


def materialize_dynamic_summary(memories: list[UserMemory]) -> dict:
    observations = []
    for memory in memories:
        if memory.memory_type != "dynamic_observation":
            continue
        observations.append(
            {
                "category": memory.category,
                "content": memory.content[: settings.memory_single_item_max_chars],
                "confidence": memory.confidence,
                "last_seen_at": memory.last_seen_at.isoformat(),
            }
        )
    return {"recent_observations": observations[:20]}


def format_stable_profile(profile: dict, *, max_chars: int) -> str:
    lines = []
    if profile.get("preferred_name"):
        lines.append(f"Preferred name: {profile['preferred_name']}")
    if profile.get("interests"):
        lines.append("Interests: " + ", ".join(map(str, profile["interests"][:12])))
    if profile.get("communication_preferences"):
        parts = [f"{key}={value}" for key, value in sorted(profile["communication_preferences"].items())]
        lines.append("Communication preferences: " + "; ".join(parts))
    if profile.get("important_people"):
        lines.append("Important people: " + "; ".join(_stringify_items(profile["important_people"][:8])))
    if profile.get("living_context"):
        parts = [f"{key}={value}" for key, value in sorted(profile["living_context"].items())]
        lines.append("Living context: " + "; ".join(parts))
    if profile.get("routines"):
        lines.append("Routines: " + "; ".join(_stringify_items(profile["routines"][:8])))
    if profile.get("support_preferences"):
        lines.append("Support preferences: " + "; ".join(_stringify_items(profile["support_preferences"][:8])))
    return "\n".join(lines)[:max_chars]


def default_dynamic_expires_at() -> datetime:
    return utc_now() + timedelta(days=settings.memory_dynamic_ttl_days)


def _append_unique(items: list, value) -> None:
    if value and value not in items:
        items.append(value)


def _stringify_items(items: list) -> list[str]:
    result = []
    for item in items:
        if isinstance(item, dict):
            result.append(", ".join(f"{key}: {value}" for key, value in sorted(item.items())))
        else:
            result.append(str(item))
    return result


def empty_profile() -> dict:
    return deepcopy(PROFILE_TEMPLATE)


def utc_now() -> datetime:
    return datetime.now(UTC)


memory_service = MemoryService()

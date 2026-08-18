from datetime import UTC, datetime, timedelta
import sys
import unittest
from pathlib import Path
from uuid import uuid4

from sqlalchemy import inspect, select

EDGE_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(EDGE_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(EDGE_BACKEND_ROOT))

from services.db import db_session, engine  # noqa: E402
from services.db_models import User, UserMemory, UserProfile  # noqa: E402
from services.memory_service import (  # noqa: E402
    MemoryInput,
    MemoryService,
    default_dynamic_expires_at,
    format_stable_profile,
)


def create_user() -> str:
    with db_session() as session:
        user = User(status="active", created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
        session.add(user)
        session.flush()
        return user.user_id


class MemorySchemaTest(unittest.TestCase):
    def test_phase10_tables_exist(self):
        inspector = inspect(engine)
        self.assertIn("user_profiles", inspector.get_table_names())
        self.assertIn("user_memories", inspector.get_table_names())
        memory_columns = {column["name"] for column in inspector.get_columns("user_memories")}
        self.assertIn("normalized_key", memory_columns)
        self.assertIn("supersedes_memory_id", memory_columns)


class MemoryServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = MemoryService()
        self.user_id = create_user()

    def test_memory_crud_and_stable_profile_materialization(self):
        memory = self.service.create_or_update_memory(
            MemoryInput(
                user_id=self.user_id,
                memory_type="semantic_fact",
                category="interest",
                normalized_key="interest:xiangqi",
                content="象棋",
                structured_payload={"interest": "象棋"},
                source_type="explicit_user",
                confidence=0.95,
                importance=0.8,
            )
        )

        active = self.service.load_active_memories(self.user_id)
        self.assertEqual([item.memory_id for item in active], [memory.memory_id])
        with db_session() as session:
            profile = session.get(UserProfile, self.user_id)
            self.assertEqual(profile.stable_profile["interests"], ["象棋"])

    def test_dedup_updates_last_seen_without_duplicate(self):
        first = self.service.create_or_update_memory(
            MemoryInput(
                user_id=self.user_id,
                memory_type="semantic_fact",
                category="interest",
                normalized_key="interest:jingju",
                content="京剧",
                source_type="explicit_user",
                confidence=0.9,
                importance=0.5,
            )
        )
        second = self.service.create_or_update_memory(
            MemoryInput(
                user_id=self.user_id,
                memory_type="semantic_fact",
                category="interest",
                normalized_key="interest:jingju",
                content="京剧",
                source_type="explicit_user",
                confidence=0.95,
                importance=0.7,
            )
        )

        self.assertEqual(first.memory_id, second.memory_id)
        self.assertEqual(len(self.service.load_active_memories(self.user_id)), 1)
        self.assertGreaterEqual(second.confidence, 0.95)

    def test_same_key_conflict_supersedes_old_memory(self):
        old = self.service.create_or_update_memory(
            MemoryInput(
                user_id=self.user_id,
                memory_type="semantic_fact",
                category="living_context",
                normalized_key="important_person:daughter:location",
                content="女儿在上海",
                structured_payload={"key": "daughter_location", "value": "上海"},
                source_type="explicit_user",
                confidence=0.9,
                importance=0.7,
            )
        )
        new = self.service.create_or_update_memory(
            MemoryInput(
                user_id=self.user_id,
                memory_type="semantic_fact",
                category="living_context",
                normalized_key="important_person:daughter:location",
                content="女儿在杭州",
                structured_payload={"key": "daughter_location", "value": "杭州"},
                source_type="explicit_user",
                confidence=0.95,
                importance=0.8,
            )
        )

        with db_session() as session:
            old_row = session.get(UserMemory, old.memory_id)
            new_row = session.get(UserMemory, new.memory_id)
            self.assertEqual(old_row.status, "superseded")
            self.assertEqual(new_row.supersedes_memory_id, old.memory_id)

    def test_multi_value_interests_use_distinct_keys(self):
        for key, content in [("interest:xiangqi", "象棋"), ("interest:jingju", "京剧")]:
            self.service.create_or_update_memory(
                MemoryInput(
                    user_id=self.user_id,
                    memory_type="semantic_fact",
                    category="interest",
                    normalized_key=key,
                    content=content,
                    source_type="explicit_user",
                    confidence=0.9,
                    importance=0.6,
                )
            )
        with db_session() as session:
            profile = session.get(UserProfile, self.user_id)
            self.assertEqual(set(profile.stable_profile["interests"]), {"象棋", "京剧"})

    def test_weak_inference_does_not_materialize_stable_profile(self):
        self.service.create_or_update_memory(
            MemoryInput(
                user_id=self.user_id,
                memory_type="semantic_fact",
                category="interest",
                normalized_key="interest:gardening",
                content="园艺",
                source_type="text_inference",
                confidence=0.55,
                importance=0.4,
            )
        )
        with db_session() as session:
            profile = session.get(UserProfile, self.user_id)
            self.assertEqual(profile.stable_profile["interests"], [])

    def test_dynamic_observation_has_ttl_and_never_enters_stable_profile(self):
        expires_at = default_dynamic_expires_at()
        self.service.create_or_update_memory(
            MemoryInput(
                user_id=self.user_id,
                memory_type="dynamic_observation",
                category="emotion_observation",
                normalized_key=f"emotion:{uuid4().hex}",
                content="近期观察：语音情绪偏低落",
                structured_payload={"dominant_emotion": "sad", "confidence": 0.7},
                source_type="multimodal_observation",
                confidence=0.7,
                importance=0.3,
                expires_at=expires_at,
            )
        )
        with db_session() as session:
            profile = session.get(UserProfile, self.user_id)
            self.assertEqual(profile.stable_profile["interests"], [])
            self.assertEqual(len(profile.dynamic_summary["recent_observations"]), 1)

    def test_profile_template_does_not_leak_across_users(self):
        self.service.create_or_update_memory(
            MemoryInput(
                user_id=self.user_id,
                memory_type="semantic_fact",
                category="interest",
                normalized_key="interest:xiangqi",
                content="象棋",
                source_type="explicit_user",
                confidence=0.95,
                importance=0.8,
            )
        )
        other_user_id = create_user()
        self.service.create_or_update_memory(
            MemoryInput(
                user_id=other_user_id,
                memory_type="dynamic_observation",
                category="emotion_observation",
                normalized_key=f"emotion:{uuid4().hex}",
                content="近期观察：语音情绪偏低落",
                source_type="multimodal_observation",
                confidence=0.7,
                importance=0.3,
            )
        )

        with db_session() as session:
            other_profile = session.get(UserProfile, other_user_id)
            self.assertEqual(other_profile.stable_profile["interests"], [])

    def test_expire_delete_clear_and_cross_user_scope(self):
        other_user_id = create_user()
        expired = self.service.create_or_update_memory(
            MemoryInput(
                user_id=self.user_id,
                memory_type="dynamic_observation",
                category="emotion_observation",
                normalized_key=f"emotion:{uuid4().hex}",
                content="过期观察",
                source_type="multimodal_observation",
                confidence=0.7,
                importance=0.2,
                expires_at=datetime.now(UTC) - timedelta(seconds=1),
            )
        )
        self.service.create_or_update_memory(
            MemoryInput(
                user_id=other_user_id,
                memory_type="semantic_fact",
                category="interest",
                normalized_key="interest:calligraphy",
                content="书法",
                source_type="explicit_user",
                confidence=0.9,
                importance=0.6,
            )
        )

        self.assertEqual(self.service.expire_dynamic_memories(), 1)
        self.assertFalse(self.service.delete_memory(user_id=other_user_id, memory_id=expired.memory_id))
        count = self.service.clear_user_memories(other_user_id)
        self.assertEqual(count, 1)
        self.assertEqual(self.service.load_active_memories(other_user_id), [])

    def test_compact_profile_format_is_deterministic_and_bounded(self):
        self.service.create_or_update_memory(
            MemoryInput(
                user_id=self.user_id,
                memory_type="semantic_fact",
                category="preferred_name",
                normalized_key="preferred_name",
                content="王叔",
                source_type="explicit_user",
                confidence=0.95,
                importance=0.9,
            )
        )
        with db_session() as session:
            profile = session.scalar(select(UserProfile).where(UserProfile.user_id == self.user_id))
            compact = format_stable_profile(profile.stable_profile, max_chars=20)
            self.assertLessEqual(len(compact), 20)
            self.assertTrue(compact.startswith("Preferred name:"))


if __name__ == "__main__":
    unittest.main()

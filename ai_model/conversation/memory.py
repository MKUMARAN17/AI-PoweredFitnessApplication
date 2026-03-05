"""
Conversation Memory
====================
MongoDB-backed conversation history system.

Two responsibilities:
1. SHORT-TERM MEMORY: Stores recent turns per user so the model
   maintains context across a multi-turn conversation (like a real coach).

2. LEARNING COLLECTION: Flags high-quality conversations for future
   fine-tuning — this is how the model improves over time from real user data.
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)

MONGO_URI       = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME         = "fitness_ai_db"
HISTORY_COLL    = "conversation_history"
TRAINING_COLL   = "training_conversations"

# How many past turns to include in the model's context window
CONTEXT_WINDOW_TURNS = 6  # Last 3 user messages + 3 assistant responses


class ConversationMemory:
    """
    Manages per-user conversation history stored in MongoDB.
    """

    def __init__(self):
        try:
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            self.client.admin.command("ping")
            self.db = self.client[DB_NAME]
            self._ensure_indexes()
            self._memory_enabled = True
            logger.info("✅ ConversationMemory connected to MongoDB.")
        except ConnectionFailure as e:
            logger.warning(f"MongoDB unavailable — conversation memory disabled: {e}")
            self._memory_enabled = False
            self._in_memory_store = {}  # Fallback in-process store

    def _ensure_indexes(self):
        """Create indexes for fast lookups."""
        history = self.db[HISTORY_COLL]
        history.create_index([("userId", ASCENDING), ("timestamp", DESCENDING)])
        history.create_index("timestamp", expireAfterSeconds=86400 * 7)  # TTL: 7 days

        training = self.db[TRAINING_COLL]
        training.create_index([("quality_score", DESCENDING)])
        training.create_index("quality_approved")

    # ── Message storage ───────────────────────────────────────────────────────

    def add_message(self, user_id: str, role: str, content: str):
        """
        Store a single message turn for a user.

        Args:
            user_id: The user's ID from your Spring Boot userservice
            role: "user" or "assistant"
            content: The message text
        """
        if not self._memory_enabled:
            self._in_memory_add(user_id, role, content)
            return

        self.db[HISTORY_COLL].insert_one({
            "userId":    user_id,
            "role":      role,
            "content":   content,
            "timestamp": datetime.now(timezone.utc),
        })

    def get_recent_history(self, user_id: str, n_turns: int = CONTEXT_WINDOW_TURNS) -> list[dict]:
        """
        Retrieve the last N message turns for a user, formatted for the model.

        Returns list of {"role": ..., "content": ...} dicts in chronological order.
        """
        if not self._memory_enabled:
            return self._in_memory_get(user_id, n_turns)

        messages = list(
            self.db[HISTORY_COLL]
            .find({"userId": user_id}, {"_id": 0, "role": 1, "content": 1})
            .sort("timestamp", DESCENDING)
            .limit(n_turns)
        )

        # Reverse so oldest message is first (chronological order for model)
        return list(reversed(messages))

    def clear_history(self, user_id: str):
        """Clear all conversation history for a user (e.g. when they start a new session)."""
        if not self._memory_enabled:
            self._in_memory_store.pop(user_id, None)
            return
        self.db[HISTORY_COLL].delete_many({"userId": user_id})

    # ── Learning collection ───────────────────────────────────────────────────

    def save_conversation_for_training(
        self,
        user_id: str,
        messages: list[dict],
        quality_score: float = 0.0,
        auto_approve_threshold: float = 0.8,
    ):
        """
        Save a completed conversation for future fine-tuning.

        quality_score is automatically computed based on:
        - Conversation length (longer = more useful)
        - User engagement signals (follow-up questions)
        - Recency

        Conversations above auto_approve_threshold are flagged for training.

        Args:
            user_id: The user's ID
            messages: Full conversation as [{"role": ..., "content": ...}]
            quality_score: 0.0–1.0 score (computed automatically if 0.0)
            auto_approve_threshold: Score above which conversation is auto-approved for training
        """
        if not self._memory_enabled or len(messages) < 4:
            return  # Don't save short or incomplete conversations

        if quality_score == 0.0:
            quality_score = self._compute_quality_score(messages)

        doc = {
            "userId":           user_id,
            "messages":         messages,
            "turn_count":       len([m for m in messages if m["role"] == "user"]),
            "quality_score":    quality_score,
            "quality_approved": quality_score >= auto_approve_threshold,
            "used_in_training": False,
            "created_at":       datetime.now(timezone.utc),
        }

        self.db[TRAINING_COLL].insert_one(doc)
        status = "✅ auto-approved" if doc["quality_approved"] else "📋 pending review"
        logger.debug(f"Saved conversation for training (score={quality_score:.2f}, {status})")

    def _compute_quality_score(self, messages: list[dict]) -> float:
        """
        Heuristically score a conversation's training value.

        Scoring factors:
        - Number of turns (more turns = richer context for training)
        - User message length (longer messages = more specific context)
        - Presence of follow-up questions (indicates engaged conversation)
        - Assistant response length (longer = more substantive coaching)
        """
        user_msgs      = [m for m in messages if m["role"] == "user"]
        assistant_msgs = [m for m in messages if m["role"] == "assistant"]

        if not user_msgs or not assistant_msgs:
            return 0.0

        # Turn count score (max at 4+ turns)
        turn_score = min(len(user_msgs) / 4.0, 1.0)

        # Average user message length (max at 100+ chars)
        avg_user_len = sum(len(m["content"]) for m in user_msgs) / len(user_msgs)
        length_score = min(avg_user_len / 100.0, 1.0)

        # Follow-up indicator: user asked multiple questions
        followup_score = 1.0 if len(user_msgs) > 1 else 0.5

        # Assistant response quality (avoid very short responses)
        avg_asst_len = sum(len(m["content"]) for m in assistant_msgs) / len(assistant_msgs)
        response_score = min(avg_asst_len / 200.0, 1.0)

        # Weighted average
        score = (
            turn_score     * 0.30 +
            length_score   * 0.25 +
            followup_score * 0.20 +
            response_score * 0.25
        )
        return round(score, 3)

    def get_unapproved_conversations(self, limit: int = 50) -> list[dict]:
        """Fetch conversations pending manual quality review."""
        if not self._memory_enabled:
            return []
        return list(
            self.db[TRAINING_COLL]
            .find({"quality_approved": False}, {"_id": 0})
            .sort("quality_score", DESCENDING)
            .limit(limit)
        )

    def approve_conversation(self, user_id: str, created_at: datetime):
        """Manually approve a conversation for training."""
        if not self._memory_enabled:
            return
        self.db[TRAINING_COLL].update_one(
            {"userId": user_id, "created_at": created_at},
            {"$set": {"quality_approved": True}},
        )

    def count_training_conversations(self) -> dict:
        """Return stats on training conversation collection."""
        if not self._memory_enabled:
            return {"total": 0, "approved": 0, "used": 0}
        total    = self.db[TRAINING_COLL].count_documents({})
        approved = self.db[TRAINING_COLL].count_documents({"quality_approved": True})
        used     = self.db[TRAINING_COLL].count_documents({"used_in_training": True})
        return {"total": total, "approved": approved, "used": used}

    # ── In-memory fallback (when MongoDB is unavailable) ─────────────────────

    def _in_memory_add(self, user_id: str, role: str, content: str):
        if user_id not in self._in_memory_store:
            self._in_memory_store[user_id] = []
        self._in_memory_store[user_id].append({"role": role, "content": content})

    def _in_memory_get(self, user_id: str, n_turns: int) -> list[dict]:
        messages = self._in_memory_store.get(user_id, [])
        return messages[-n_turns:]

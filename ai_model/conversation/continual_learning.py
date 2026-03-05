"""
Continual Learning Scheduler
==============================
Automatically retrains the model on newly collected user conversations.
Runs as a background process alongside the FastAPI server.

Schedule: Weekly retrain if enough new approved conversations exist.
This is how the model actually LEARNS from your users over time.
"""

import logging
import asyncio
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from pymongo import MongoClient
import os

logger = logging.getLogger(__name__)

MONGO_URI        = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME          = "fitness_ai_db"
TRAINING_COLL    = "training_conversations"
MIN_NEW_CONVOS   = 20       # Minimum new conversations to trigger a retrain
RETRAIN_INTERVAL = 604800   # 7 days in seconds


class ContinualLearningScheduler:
    """
    Background scheduler that monitors the training conversation collection
    and triggers fine-tuning jobs when enough new data has accumulated.
    """

    def __init__(self):
        self._running = False
        self._last_retrain = None
        try:
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
            self.db = self.client[DB_NAME]
            self._enabled = True
        except Exception as e:
            logger.warning(f"Continual learning scheduler disabled (MongoDB unavailable): {e}")
            self._enabled = False

    async def start(self):
        """Start the background scheduler loop."""
        if not self._enabled:
            return
        self._running = True
        logger.info("🔄 Continual learning scheduler started.")
        asyncio.create_task(self._schedule_loop())

    def stop(self):
        self._running = False

    async def _schedule_loop(self):
        """Check every hour if retraining should be triggered."""
        while self._running:
            await asyncio.sleep(3600)  # Check every hour
            await self._check_and_retrain()

    async def _check_and_retrain(self):
        """Check conditions and trigger retrain if criteria are met."""
        try:
            new_count = self._count_new_approved_conversations()

            logger.info(f"[ContinualLearning] New approved conversations since last train: {new_count}")

            if new_count < MIN_NEW_CONVOS:
                logger.info(f"  Not enough data yet ({new_count}/{MIN_NEW_CONVOS} needed). Skipping.")
                return

            if self._last_retrain:
                elapsed = (datetime.now(timezone.utc) - self._last_retrain).total_seconds()
                if elapsed < RETRAIN_INTERVAL:
                    remaining_hours = (RETRAIN_INTERVAL - elapsed) / 3600
                    logger.info(f"  Too soon to retrain. Next window in {remaining_hours:.1f} hours.")
                    return

            logger.info(f"✅ Conditions met! Triggering retrain with {new_count} new conversations...")
            await self._trigger_retrain()

        except Exception as e:
            logger.error(f"Error in continual learning check: {e}")

    async def _trigger_retrain(self):
        """
        Launch training as a subprocess so it doesn't block the API server.
        After training, marks conversations as used.
        """
        logger.info("🚀 Starting background fine-tuning job...")
        self._last_retrain = datetime.now(timezone.utc)

        try:
            # Run training in a subprocess (non-blocking)
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "training.train",
                "--no-mongo",   # Use data from prepare_data.py which already reads MongoDB
                "--merge",      # Merge adapters after training
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info("✅ Background fine-tuning completed successfully!")
                self._mark_conversations_as_used()
                logger.info("   Model will be reloaded on next server restart.")
            else:
                logger.error(f"❌ Fine-tuning failed:\n{stderr.decode()}")

        except Exception as e:
            logger.error(f"Failed to launch training subprocess: {e}")

    def _count_new_approved_conversations(self) -> int:
        """Count approved conversations not yet used in training."""
        return self.db[TRAINING_COLL].count_documents({
            "quality_approved": True,
            "used_in_training": False,
        })

    def _mark_conversations_as_used(self):
        """Mark all approved conversations as used after a training run."""
        result = self.db[TRAINING_COLL].update_many(
            {"quality_approved": True, "used_in_training": False},
            {"$set": {"used_in_training": True, "used_at": datetime.now(timezone.utc)}},
        )
        logger.info(f"  Marked {result.modified_count} conversations as used in training.")

    def get_status(self) -> dict:
        """Return current scheduler status — exposed via /api/ai/training-status endpoint."""
        if not self._enabled:
            return {"enabled": False, "reason": "MongoDB unavailable"}

        new_count = self._count_new_approved_conversations()
        return {
            "enabled":             True,
            "last_retrain":        self._last_retrain.isoformat() if self._last_retrain else None,
            "new_conversations":   new_count,
            "min_required":        MIN_NEW_CONVOS,
            "ready_to_retrain":    new_count >= MIN_NEW_CONVOS,
            "check_interval_hours": RETRAIN_INTERVAL // 3600,
        }

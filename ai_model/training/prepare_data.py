"""
Data Preparation Pipeline
==========================
Converts fitness conversations → HuggingFace Dataset format for QLoRA fine-tuning.

Also handles:
- Loading real conversation data from MongoDB (user-collected data)
- Data augmentation for underrepresented topics
- Train/validation split
- Tokenization and formatting for causal LM training
"""

import json
import os
import logging
from pathlib import Path
from datasets import Dataset
from transformers import AutoTokenizer
from training.dataset import CONVERSATIONS

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
DATA_DIR       = Path("./data")
TRAIN_FILE     = DATA_DIR / "train.jsonl"
VAL_FILE       = DATA_DIR / "val.jsonl"
VAL_SPLIT      = 0.1        # 10% validation
MAX_SEQ_LENGTH = 2048       # Token limit per sample


def format_conversation_to_prompt(conversation: dict, tokenizer) -> str:
    """
    Convert a ShareGPT-style conversation dict into the model's chat template format.
    Uses the tokenizer's built-in apply_chat_template for correct formatting.

    Args:
        conversation: {"messages": [{"role": ..., "content": ...}, ...]}
        tokenizer: HuggingFace tokenizer with a chat template

    Returns:
        Formatted string ready for tokenization
    """
    messages = conversation["messages"]
    try:
        formatted = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )
        return formatted
    except Exception as e:
        logger.warning(f"Chat template failed: {e} — falling back to manual format.")
        return _manual_format(messages)


def _manual_format(messages: list) -> str:
    """Fallback formatter if the tokenizer has no chat template."""
    parts = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"].strip()
        if role == "system":
            parts.append(f"<|system|>\n{content}\n")
        elif role == "user":
            parts.append(f"<|user|>\n{content}\n")
        elif role == "assistant":
            parts.append(f"<|assistant|>\n{content}\n")
    return "".join(parts) + "<|end|>"


def load_mongodb_conversations(mongo_uri: str = None) -> list:
    """
    Load real user conversations collected from your fitness app (MongoDB).
    These are conversations users had with the previous AI — filtered for quality.

    Returns list of conversation dicts in the same format as CONVERSATIONS.
    """
    if not mongo_uri:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")

    try:
        from pymongo import MongoClient
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        db = client["fitness_ai_db"]
        collection = db["training_conversations"]

        # Only load conversations marked as high-quality (rated by users or admin)
        docs = list(collection.find(
            {"quality_approved": True, "turn_count": {"$gte": 2}},
            {"_id": 0, "messages": 1}
        ))
        logger.info(f"📦 Loaded {len(docs)} conversations from MongoDB.")
        return docs

    except Exception as e:
        logger.warning(f"Could not connect to MongoDB for training data: {e}")
        return []


def prepare_dataset(
    model_name: str,
    include_mongodb: bool = True,
    mongo_uri: str = None,
) -> tuple[Dataset, Dataset]:
    """
    Build train and validation datasets from:
    1. Curated fitness conversations (in dataset.py)
    2. Real user conversations from MongoDB (if available and enabled)

    Returns: (train_dataset, val_dataset)
    """
    logger.info("📂 Preparing training dataset...")

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ── Collect all conversations ─────────────────────────────────────────
    all_conversations = list(CONVERSATIONS)
    logger.info(f"  Curated conversations: {len(all_conversations)}")

    if include_mongodb:
        mongo_convos = load_mongodb_conversations(mongo_uri)
        all_conversations.extend(mongo_convos)
        logger.info(f"  MongoDB conversations added: {len(mongo_convos)}")

    logger.info(f"  Total conversations: {len(all_conversations)}")

    # ── Format each conversation into model input text ────────────────────
    formatted_texts = []
    skipped = 0
    for convo in all_conversations:
        text = format_conversation_to_prompt(convo, tokenizer)
        tokens = tokenizer(text, return_length=True)["length"][0]

        if tokens > MAX_SEQ_LENGTH:
            skipped += 1
            continue  # Skip sequences that are too long

        formatted_texts.append({"text": text, "length": tokens})

    logger.info(f"  Formatted: {len(formatted_texts)} | Skipped (too long): {skipped}")

    # ── Train / val split ─────────────────────────────────────────────────
    split_idx = max(1, int(len(formatted_texts) * (1 - VAL_SPLIT)))
    train_data = formatted_texts[:split_idx]
    val_data   = formatted_texts[split_idx:]

    train_dataset = Dataset.from_list(train_data)
    val_dataset   = Dataset.from_list(val_data)

    # ── Save as JSONL ─────────────────────────────────────────────────────
    DATA_DIR.mkdir(exist_ok=True)
    _save_jsonl(train_data, TRAIN_FILE)
    _save_jsonl(val_data, VAL_FILE)

    logger.info(f"✅ Dataset ready — Train: {len(train_dataset)}, Val: {len(val_dataset)}")
    logger.info(f"   Saved to {TRAIN_FILE} and {VAL_FILE}")

    return train_dataset, val_dataset


def _save_jsonl(data: list, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def tokenize_dataset(dataset: Dataset, tokenizer, max_length: int = MAX_SEQ_LENGTH) -> Dataset:
    """Tokenize the dataset for causal LM training."""

    def tokenize(examples):
        tokens = tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_length,
            padding=False,
            return_tensors=None,
        )
        tokens["labels"] = tokens["input_ids"].copy()
        return tokens

    return dataset.map(
        tokenize,
        batched=True,
        remove_columns=["text", "length"],
        desc="Tokenizing",
    )


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    # Default to Mistral 7B for data prep
    model = sys.argv[1] if len(sys.argv) > 1 else "mistralai/Mistral-7B-Instruct-v0.3"
    prepare_dataset(model_name=model)

"""
QLoRA Fine-Tuning Script — Fitness AI Coach
=============================================

Uses Parameter-Efficient Fine-Tuning (PEFT) with QLoRA to fine-tune
Mistral-7B-Instruct on fitness coaching conversations.

Why QLoRA?
- Fine-tunes only 0.5–1% of model parameters (LoRA adapters)
- Quantizes base model to 4-bit, dramatically reducing VRAM
- Runs on a single 12GB GPU (RTX 3060/4060/A100)
- Can run on 8GB GPU with smaller batch size

Training flow:
  Load base model (4-bit quantized)
    → Attach LoRA adapters (trainable layers)
    → Train on fitness conversations
    → Save LoRA adapter weights (NOT the full model)
    → Inference: load base model + merge adapters

Run:
  python -m training.train                          # default settings
  python -m training.train --model mistralai/Mistral-7B-Instruct-v0.3
  python -m training.train --resume                 # resume from checkpoint
"""

import os
import logging
import argparse
from pathlib import Path
from datetime import datetime

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    BitsAndBytesConfig,
    EarlyStoppingCallback,
)
from peft import (
    LoraConfig,
    get_peft_model,
    TaskType,
    prepare_model_for_kbit_training,
)
from trl import SFTTrainer, SFTConfig
from training.prepare_data import prepare_dataset, tokenize_dataset

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_BASE_MODEL   = "mistralai/Mistral-7B-Instruct-v0.3"
ADAPTER_OUTPUT_DIR   = "./models/fitness-coach-adapter"
FULL_MODEL_DIR       = "./models/fitness-coach-merged"
TRAINING_LOGS_DIR    = "./training_logs"


# LoRA hyperparameters — these control which layers we fine-tune and how much
LORA_CONFIG = LoraConfig(
    r=16,                           # Rank: higher = more capacity but more parameters
    lora_alpha=32,                  # Scaling factor (usually 2× rank)
    target_modules=[                # Which weight matrices to attach LoRA to
        "q_proj", "k_proj",         # Attention query and key projections
        "v_proj", "o_proj",         # Attention value and output
        "gate_proj", "up_proj",     # FFN gate and up projections
        "down_proj",                # FFN down projection
    ],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

# 4-bit quantization config — loads the base model at reduced precision to save VRAM
QUANTIZATION_CONFIG = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_type="nf4",      # NormalFloat4 — best quality for 4-bit
    bnb_4bit_use_double_quant=True, # Extra memory savings with minimal quality loss
)


def get_training_args(output_dir: str, resume: bool = False) -> SFTConfig:
    """Build SFTTrainer training arguments."""
    return SFTConfig(
        output_dir=output_dir,

        # ── Training duration ──────────────────────────────────────────
        num_train_epochs=3,             # 3 full passes over the dataset
        max_steps=-1,                   # -1 = use epochs, not steps

        # ── Batch and gradient ────────────────────────────────────────
        per_device_train_batch_size=2,  # Adjust based on your VRAM
        per_device_eval_batch_size=2,
        gradient_accumulation_steps=4,  # Effective batch size = 2×4 = 8
        gradient_checkpointing=True,    # Trade compute for memory savings

        # ── Optimizer ────────────────────────────────────────────────
        optim="paged_adamw_32bit",      # Memory-efficient optimizer for QLoRA
        learning_rate=2e-4,             # Standard for LoRA fine-tuning
        lr_scheduler_type="cosine",     # Cosine decay — smoother than linear
        warmup_ratio=0.05,              # 5% of steps for LR warmup

        # ── Precision ────────────────────────────────────────────────
        fp16=True,                      # Use float16 for training compute

        # ── Logging & evaluation ──────────────────────────────────────
        logging_dir=TRAINING_LOGS_DIR,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=50,
        save_total_limit=3,            # Keep only the 3 best checkpoints
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",

        # ── Sequence length ───────────────────────────────────────────
        max_seq_length=2048,

        # ── Dataset ───────────────────────────────────────────────────
        dataset_text_field="text",

        # ── Misc ──────────────────────────────────────────────────────
        report_to="none",               # Set to "wandb" or "tensorboard" if desired
        seed=42,
    )


def load_model_and_tokenizer(model_name: str):
    """
    Load base model with 4-bit quantization and prepare for LoRA training.
    """
    logger.info(f"Loading base model: {model_name}")
    logger.info("This downloads ~4GB on first run — subsequent runs use cache.")

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"   # Required for causal LM training

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=QUANTIZATION_CONFIG,
        device_map="auto",              # Automatically distributes across available GPUs
        trust_remote_code=True,
        torch_dtype=torch.float16,
    )

    # Prepare quantized model for LoRA training (adds special gradient hooks)
    model = prepare_model_for_kbit_training(model)

    logger.info(f"Base model loaded. Parameters: {model.num_parameters():,}")
    return model, tokenizer


def attach_lora_adapters(model):
    """Attach LoRA adapters to the model and freeze all base weights."""
    model = get_peft_model(model, LORA_CONFIG)
    trainable, total = model.get_nb_trainable_parameters()
    pct = 100 * trainable / total
    logger.info(f"LoRA adapters attached.")
    logger.info(f"Trainable parameters: {trainable:,} / {total:,} ({pct:.2f}%)")
    return model


def train(
    base_model: str = DEFAULT_BASE_MODEL,
    output_dir: str = ADAPTER_OUTPUT_DIR,
    include_mongodb: bool = True,
    resume: bool = False,
):
    """
    Main training function.

    Args:
        base_model: HuggingFace model ID or local path
        output_dir: Where to save LoRA adapter weights
        include_mongodb: Whether to augment with real user conversations from MongoDB
        resume: Resume from last checkpoint if available
    """
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(TRAINING_LOGS_DIR).mkdir(exist_ok=True)

    logger.info("=" * 60)
    logger.info(f"🏋️  Fitness AI Coach — Fine-Tuning Run {run_id}")
    logger.info(f"Base model: {base_model}")
    logger.info(f"Output: {output_dir}")
    logger.info("=" * 60)

    # ── Check GPU ────────────────────────────────────────────────────────
    if not torch.cuda.is_available():
        logger.warning("⚠️  No GPU detected! Training on CPU will be VERY slow.")
        logger.warning("    Consider using Google Colab (free T4) or Kaggle (P100).")
        logger.warning("    See TRAINING_GUIDE.md for cloud training instructions.")
    else:
        gpu = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        logger.info(f"✅ GPU: {gpu} | VRAM: {vram:.1f}GB")

    # ── Prepare data ────────────────────────────────────────────────────
    logger.info("\n📦 Step 1/4: Preparing dataset...")
    train_dataset, val_dataset = prepare_dataset(
        model_name=base_model,
        include_mongodb=include_mongodb,
    )

    # ── Load model ──────────────────────────────────────────────────────
    logger.info("\n🤖 Step 2/4: Loading model with QLoRA...")
    model, tokenizer = load_model_and_tokenizer(base_model)
    model = attach_lora_adapters(model)

    # ── Training arguments ───────────────────────────────────────────────
    training_args = get_training_args(output_dir, resume=resume)

    # ── Build trainer ───────────────────────────────────────────────────
    logger.info("\n🔧 Step 3/4: Configuring SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        processing_class=tokenizer,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
    )

    # ── Train ────────────────────────────────────────────────────────────
    logger.info("\n🚀 Step 4/4: Starting training...")
    resume_checkpoint = output_dir if resume and Path(output_dir).exists() else None
    trainer.train(resume_from_checkpoint=resume_checkpoint)

    # ── Save ─────────────────────────────────────────────────────────────
    logger.info(f"\n💾 Saving LoRA adapter weights to: {output_dir}")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    train_loss = trainer.state.log_history[-1].get("train_loss", "N/A")
    eval_loss  = trainer.state.log_history[-1].get("eval_loss", "N/A")
    logger.info("\n" + "=" * 60)
    logger.info(f"✅ Training complete!")
    logger.info(f"   Final train loss: {train_loss}")
    logger.info(f"   Final eval loss:  {eval_loss}")
    logger.info(f"   Adapter saved to: {output_dir}")
    logger.info("=" * 60)
    logger.info("\nNext step: run merge_model.py to merge adapters into base model.")

    return trainer


def merge_and_save(
    base_model: str = DEFAULT_BASE_MODEL,
    adapter_dir: str = ADAPTER_OUTPUT_DIR,
    output_dir:  str = FULL_MODEL_DIR,
):
    """
    Merge LoRA adapters into the base model and save as a standalone model.
    This creates the model that inference.py will load.

    Merging advantages: faster inference, no PEFT dependency at runtime.
    """
    logger.info(f"🔀 Merging LoRA adapters into base model...")
    logger.info(f"   Base: {base_model}")
    logger.info(f"   Adapter: {adapter_dir}")
    logger.info(f"   Output: {output_dir}")

    from peft import PeftModel

    # Load base model in full precision for merging
    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16,
        device_map="cpu",           # Merge on CPU to avoid OOM
    )
    tokenizer = AutoTokenizer.from_pretrained(adapter_dir)

    # Load and merge adapters
    peft_model = PeftModel.from_pretrained(base, adapter_dir)
    merged = peft_model.merge_and_unload()

    # Save merged model
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(output_dir, safe_serialization=True)
    tokenizer.save_pretrained(output_dir)

    logger.info(f"✅ Merged model saved to: {output_dir}")
    logger.info(f"   Size: ~14GB (full fp16 weights)")
    logger.info(f"\n   Load in inference.py with: model_path='{output_dir}'")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    parser = argparse.ArgumentParser(description="Train Fitness AI Coach with QLoRA")
    parser.add_argument("--model",   default=DEFAULT_BASE_MODEL, help="Base model ID or path")
    parser.add_argument("--output",  default=ADAPTER_OUTPUT_DIR, help="Adapter output directory")
    parser.add_argument("--resume",  action="store_true",        help="Resume from checkpoint")
    parser.add_argument("--no-mongo", action="store_true",       help="Skip MongoDB data")
    parser.add_argument("--merge",   action="store_true",        help="Merge adapters after training")
    args = parser.parse_args()

    train(
        base_model=args.model,
        output_dir=args.output,
        include_mongodb=not args.no_mongo,
        resume=args.resume,
    )

    if args.merge:
        merge_and_save(base_model=args.model, adapter_dir=args.output)

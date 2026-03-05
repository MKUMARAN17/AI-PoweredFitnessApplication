"""
Inference Engine — Fine-Tuned Fitness Coach
============================================
Loads the fine-tuned model (merged weights OR base + LoRA adapters)
and runs streaming/non-streaming inference.

Used by rag_service.py as the LLM backend instead of OpenAI/Gemini.

Hardware notes (your machine: i5-12500H, 16GB RAM, no dedicated GPU):
- This will run on CPU using float32 / int8 quantization
- Mistral-7B on CPU uses ~12–14GB RAM (close to your limit)
- Recommended: use a smaller model like TinyLlama or phi-2 for CPU-only
  or quantize Mistral with llama.cpp / GGUF format
- GGUF path is commented below — uncomment if you install llama-cpp-python
"""

import logging
import os
import torch
from pathlib import Path
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TextIteratorStreamer,
    pipeline,
)
from threading import Thread

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# PATHS — set via env var or use defaults
# ─────────────────────────────────────────────────────────────────────────────
MERGED_MODEL_PATH   = os.getenv("FITNESS_MODEL_PATH",   "./models/fitness-coach-merged")
ADAPTER_PATH        = os.getenv("FITNESS_ADAPTER_PATH", "./models/fitness-coach-adapter")

# ─────────────────────────────────────────────────────────────────────────────
# CPU-FRIENDLY FALLBACK MODEL
# For your i5-12500H with 16GB RAM, Mistral-7B is borderline.
# TinyLlama (1.1B params) runs comfortably with ~2GB RAM — great for testing.
# Switch to Mistral once you have the trained weights on a GPU/Colab.
# ─────────────────────────────────────────────────────────────────────────────
BASE_MODEL_FALLBACK = os.getenv(
    "FITNESS_BASE_MODEL",
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0"  # CPU-friendly default
    # "mistralai/Mistral-7B-Instruct-v0.3"  # uncomment once trained
)

# ─────────────────────────────────────────────────────────────────────────────
# GGUF / llama-cpp-python path (optional, much faster on CPU)
# Install: pip install llama-cpp-python
# Download a GGUF file from HuggingFace (e.g. TheBloke/TinyLlama-GGUF)
# ─────────────────────────────────────────────────────────────────────────────
GGUF_MODEL_PATH = os.getenv("FITNESS_GGUF_PATH", "")  # e.g. ./models/tinyllama.Q4_K_M.gguf


class FitnessModelInference:
    """
    Loads and wraps the fine-tuned fitness coach model for inference.

    Loading strategy (in order of preference):
    1. GGUF model via llama-cpp (fastest on CPU — recommended for your specs)
    2. Merged HuggingFace model (GPU: fast, CPU: slow for 7B)
    3. Base model + LoRA adapters (requires PEFT at runtime)
    4. BASE_MODEL_FALLBACK (TinyLlama for CPU testing)
    """

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.pipe = None
        self._use_llama_cpp = False
        self._llama_model = None
        self._load_model()

    def _load_model(self):
        """Detect which model variant is available and load it."""

        # Option 0: GGUF via llama-cpp (fastest on CPU)
        if GGUF_MODEL_PATH and Path(GGUF_MODEL_PATH).exists():
            logger.info(f"Loading GGUF model via llama-cpp: {GGUF_MODEL_PATH}")
            self._load_gguf_model(GGUF_MODEL_PATH)

        # Option 1: Load merged HuggingFace model (preferred for GPU)
        elif Path(MERGED_MODEL_PATH).exists():
            logger.info(f"Loading merged fine-tuned model from: {MERGED_MODEL_PATH}")
            self._load_merged_model(MERGED_MODEL_PATH)

        # Option 2: Load base + LoRA adapters
        elif Path(ADAPTER_PATH).exists():
            logger.info(f"Loading base model + LoRA adapters from: {ADAPTER_PATH}")
            self._load_with_adapters(ADAPTER_PATH)

        # Option 3: CPU-friendly fallback (TinyLlama or configured base model)
        else:
            logger.warning(
                f"No fine-tuned model found at {MERGED_MODEL_PATH} or {ADAPTER_PATH}.\n"
                f"Falling back to: {BASE_MODEL_FALLBACK}\n"
                f"For CPU inference, consider using GGUF format (see GGUF_MODEL_PATH).\n"
                f"Run 'python -m training.train' in ai_model/ to train your model first."
            )
            self._load_merged_model(BASE_MODEL_FALLBACK)

    def _load_gguf_model(self, model_path: str):
        """Load a GGUF quantized model — fastest option for CPU inference."""
        try:
            from llama_cpp import Llama
            n_gpu_layers = -1 if torch.cuda.is_available() else 0
            self._llama_model = Llama(
                model_path=model_path,
                n_ctx=2048,
                n_gpu_layers=n_gpu_layers,
                verbose=False,
            )
            self._use_llama_cpp = True
            logger.info(f"✅ GGUF model loaded from {model_path}")
        except ImportError:
            logger.warning("llama-cpp-python not installed. Falling back to HuggingFace.")
            self._load_merged_model(BASE_MODEL_FALLBACK)

    def _get_quantization_config(self) -> BitsAndBytesConfig | None:
        """Return 4-bit quantization config if CUDA is available, else None."""
        if not torch.cuda.is_available():
            return None
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )

    def _load_merged_model(self, model_path: str):
        """Load a standalone merged model."""
        quant_config = self._get_quantization_config()

        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=quant_config,
            device_map="auto" if torch.cuda.is_available() else "cpu",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            trust_remote_code=True,
            low_cpu_mem_usage=True,  # Important for 16GB RAM
        )
        self.model.eval()
        self._build_pipeline()
        logger.info(f"✅ Model loaded from {model_path}")

    def _load_with_adapters(self, adapter_path: str):
        """Load base model and attach LoRA adapters at runtime."""
        from peft import PeftModel

        import json
        adapter_config_path = Path(adapter_path) / "adapter_config.json"
        if adapter_config_path.exists():
            with open(adapter_config_path) as f:
                base_model = json.load(f).get("base_model_name_or_path", BASE_MODEL_FALLBACK)
        else:
            base_model = BASE_MODEL_FALLBACK

        logger.info(f"  Base model: {base_model}")

        quant_config = self._get_quantization_config()
        self.tokenizer = AutoTokenizer.from_pretrained(adapter_path, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        base = AutoModelForCausalLM.from_pretrained(
            base_model,
            quantization_config=quant_config,
            device_map="auto" if torch.cuda.is_available() else "cpu",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
        self.model = PeftModel.from_pretrained(base, adapter_path)
        self.model.eval()
        self._build_pipeline()
        logger.info("✅ Fine-tuned model loaded (base + adapters).")

    def _build_pipeline(self):
        """Build HuggingFace text-generation pipeline for easy inference."""
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            device_map="auto" if torch.cuda.is_available() else None,
        )

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        max_new_tokens: int = 512,
        temperature: float = 0.75,
        top_p: float = 0.9,
        repetition_penalty: float = 1.1,
    ) -> str:
        """
        Generate a response from the fine-tuned model.

        Args:
            system_prompt: Coach personality instructions
            user_message: The full coaching prompt (user data + knowledge)
            max_new_tokens: Max tokens to generate (keep lower for CPU: 256–384)
            temperature: Creativity (0.7–0.85 for coaching)
            top_p: Nucleus sampling
            repetition_penalty: Penalize repeated phrases

        Returns:
            Generated coaching response string
        """
        # GGUF path (llama-cpp-python)
        if self._use_llama_cpp and self._llama_model:
            return self._generate_gguf(system_prompt, user_message, max_new_tokens, temperature)

        # HuggingFace path
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ]

        prompt_text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        # Reduce max_new_tokens on CPU to keep latency reasonable
        effective_tokens = max_new_tokens if torch.cuda.is_available() else min(max_new_tokens, 384)

        outputs = self.pipe(
            prompt_text,
            max_new_tokens=effective_tokens,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            do_sample=True,
            pad_token_id=self.tokenizer.pad_token_id,
            return_full_text=False,
        )

        response = outputs[0]["generated_text"].strip()
        return response

    def _generate_gguf(
        self,
        system_prompt: str,
        user_message: str,
        max_new_tokens: int,
        temperature: float,
    ) -> str:
        """Generate using llama-cpp-python (GGUF format)."""
        output = self._llama_model.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            max_tokens=max_new_tokens,
            temperature=temperature,
            top_p=0.9,
            repeat_penalty=1.1,
        )
        return output["choices"][0]["message"]["content"].strip()

    def generate_streaming(
        self,
        system_prompt: str,
        user_message: str,
        max_new_tokens: int = 384,
        temperature: float = 0.75,
    ):
        """
        Generator that yields tokens as they are produced (streaming).
        Use for real-time frontend display.
        """
        if self._use_llama_cpp and self._llama_model:
            # llama-cpp streaming
            for chunk in self._llama_model.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_message},
                ],
                max_tokens=max_new_tokens,
                temperature=temperature,
                stream=True,
            ):
                delta = chunk["choices"][0].get("delta", {}).get("content", "")
                if delta:
                    yield delta
            return

        # HuggingFace streaming
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ]

        prompt_text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        inputs = self.tokenizer(prompt_text, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
        )

        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=True,
            pad_token_id=self.tokenizer.pad_token_id,
        )

        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()

        for token in streamer:
            yield token

        thread.join()

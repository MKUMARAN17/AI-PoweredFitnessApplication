# 🏋️ Fitness AI Coach — Training Guide

## What Changed from v1 (Ollama) to v2 (Fine-Tuned)

| | v1 (Ollama + RAG) | v2 (Fine-Tuned) |
|---|---|---|
| Model | Generic Mistral from Ollama | Mistral fine-tuned on fitness coaching |
| Learns? | No | Yes — retrains on user conversations |
| Multi-turn? | No | Yes — remembers conversation history |
| Personality | Prompted at runtime | Baked into model weights |
| Runs where? | Local only | Local GPU or Google Colab |
| VRAM needed | ~5GB | ~12GB (QLoRA), ~24GB (full) |

---

## System Architecture

```
React Frontend (5173)
        │
        ▼
API Gateway (8090)
        │
        ▼
aiservice (8083) ─── Spring Boot
        │
        │ HTTP POST /api/ai/recommend
        ▼
fitness-ai-service (8085) ─── Python FastAPI
        │
        ├── LangGraph Pipeline (5 nodes)
        │        │
        │        ├── ChromaDB (fitness knowledge)
        │        └── Fine-Tuned Mistral (your trained model)
        │
        ├── ConversationMemory ─── MongoDB (per-user history)
        │
        └── ContinualLearningScheduler
                 └── Weekly retrain on new user conversations
```

---

## Step 1 — Setup

```bash
cd fitness-ai-service
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# CPU only (for inference after training elsewhere):
pip install -r requirements.txt

# GPU training (CUDA 12.1):
pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

---

## Step 2 — Train the Model

### Option A: Local GPU (Recommended if you have ≥12GB VRAM)

```bash
# Check GPU
python -c "import torch; print(torch.cuda.get_device_name(0))"

# Train (downloads Mistral ~14GB on first run, cached after)
python -m training.train

# After training, merge adapters into standalone model
python -m training.train --merge
```

Training time estimates:
- RTX 3060 (12GB): ~45–60 min
- RTX 4090 (24GB): ~20–30 min
- RTX 3080 (10GB): ~60–90 min with gradient_accumulation_steps=8

### Option B: Google Colab (Free T4 GPU)

1. Go to https://colab.research.google.com
2. Runtime → Change runtime type → T4 GPU
3. Upload the `fitness-ai-service/` folder to `/content/`
4. Run:

```python
!pip install -r /content/fitness-ai-service/requirements.txt
!cd /content/fitness-ai-service && python -m training.train --merge
```

5. Download the merged model from `./models/fitness-coach-merged/`
6. Copy to your local machine

### Option C: Add More Training Data First (Recommended)

Before training, add more conversations to `training/dataset.py`:
- Each conversation = one entry in `CONVERSATIONS` list
- Format: ShareGPT style (system / user / assistant messages)
- Aim for 500+ conversations for best results
- Cover edge cases: injuries, pregnancy, elderly, specific sports

```bash
# See how many conversations you have
python -c "from training.dataset import get_conversation_count; print(get_conversation_count())"
```

---

## Step 3 — Start the Service

```bash
# After training is complete:
python main.py
```

The service auto-detects the best available model:
1. `./models/fitness-coach-merged/` (merged, fastest)
2. `./models/fitness-coach-adapter/` (base + adapters)
3. Base `mistralai/Mistral-7B-Instruct-v0.3` (fallback, no fine-tuning)

Test it:
```bash
curl http://localhost:8085/health

curl -X POST http://localhost:8085/api/ai/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "user123",
    "age": 28, "weight": 78, "height": 175,
    "goal": "WEIGHT_LOSS",
    "steps": 8200, "caloriesBurned": 350, "workoutDuration": 40,
    "workoutType": "Running", "message": ""
  }'
```

---

## How Continual Learning Works

Every conversation your users have with the coach is automatically saved to MongoDB.

```
User chats with Alex
        │
        ▼
Conversation stored in MongoDB (fitness_ai_db.training_conversations)
        │
        ▼
Quality score computed (0.0–1.0)
High quality (≥0.8) → auto-approved for training
Low quality → pending manual review
        │
        ▼
Every 7 days: if 20+ new approved conversations exist:
        │
        ▼
Background fine-tuning job launches (doesn't block the API)
        │
        ▼
New adapter weights saved
        │
        ▼
Restart service to load new model
```

Check training stats anytime:
```bash
curl http://localhost:8085/api/ai/training-status
```

Manually trigger a retrain:
```bash
python -m training.train --merge
```

---

## Conversation Memory (Multi-Turn)

The model now remembers what users said earlier in the same session.

Example:
```
User: "I want to lose 10kg"
Alex: "At your weight and height, that'll take about 4–5 months..."

User: "What should I eat?"
Alex: "For your 10kg goal, you'll want to be at 1,700 calories/day..."
      ^── references the earlier goal automatically
```

History is stored per user in MongoDB with a 7-day TTL (auto-expires).

Reset a user's history:
```bash
curl -X DELETE http://localhost:8085/api/ai/memory/user123
```

---

## File Structure

```
fitness-ai-service/
├── main.py                          ← FastAPI app (entry point)
├── rag_service.py                   ← LangGraph pipeline
├── models.py                        ← Pydantic request/response models
├── requirements.txt
│
├── training/
│   ├── dataset.py                   ← 200+ curated fitness conversations
│   ├── prepare_data.py              ← Data formatting + MongoDB loader
│   └── train.py                     ← QLoRA fine-tuning script
│
├── model/
│   └── inference.py                 ← Fine-tuned model loader + generator
│
├── conversation/
│   ├── memory.py                    ← MongoDB conversation history
│   └── continual_learning.py        ← Auto-retrain scheduler
│
├── knowledge/
│   ├── fitness_data.py              ← ChromaDB fitness knowledge
│   └── knowledge_base.py           ← Vector store manager
│
└── models/
    ├── fitness-coach-adapter/       ← LoRA adapter weights (after training)
    └── fitness-coach-merged/        ← Merged standalone model (after merge)
```

---

## Improving the Model Over Time

### Add more training data
Edit `training/dataset.py` → add more conversation entries → retrain.

### Use real user conversations
Any conversation rated highly by users automatically feeds back into training.
Add a thumbs up/down to your React frontend and call:
```
POST /api/ai/training-approve
{ "userId": "...", "createdAt": "..." }
```

### Adjust training hyperparameters
Edit `training/train.py`:
- More epochs (3→5): better learning, risk of overfitting
- Higher LoRA rank (16→32): more model capacity, more VRAM
- Lower learning rate (2e-4→1e-4): more stable but slower

---

## Hardware Requirements

| Task | Minimum | Recommended |
|---|---|---|
| Inference only | 8GB RAM, no GPU | 16GB RAM + 8GB VRAM |
| QLoRA Training | 12GB VRAM (RTX 3060) | 24GB VRAM (RTX 4090/A100) |
| CPU inference | 32GB RAM | 64GB RAM (slow but works) |

"""
Fitness AI Coach — FastAPI Server (Local Fine-Tuned Model Edition)
==================================================================
Runs on port 8085. Called by Spring Boot aiservice (port 8083).

Endpoints:
  POST /api/ai/recommend         — personalized recommendation
  POST /api/ai/chat              — multi-turn chat with conversation memory
  DELETE /api/ai/memory/{userId} — reset conversation history for a user
  GET  /api/ai/training-status   — continual learning stats
  POST /api/ai/reset-knowledge   — rebuild ChromaDB knowledge base
  GET  /health                   — health check

Start:
  cd ai_model
  python -m venv venv
  venv\\Scripts\\activate          (Windows)
  pip install -r requirements.txt
  python main.py
  # OR:
  uvicorn main:app --host 0.0.0.0 --port 8085 --reload
"""

import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()  # Load .env file if present

from models import UserContext, RecommendationResponse, HealthResponse
from rag_service import FitnessRAGService
from conversation.continual_learning import ContinualLearningScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

rag_service: FitnessRAGService = None
scheduler: ContinualLearningScheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_service, scheduler
    logger.info("🚀 Starting Fitness AI Coach (local fine-tuned model)...")
    rag_service = FitnessRAGService()
    scheduler   = ContinualLearningScheduler()
    await scheduler.start()
    logger.info("✅ All systems ready. Listening on http://0.0.0.0:8085")
    yield
    scheduler.stop()
    logger.info("👋 Shutdown complete.")


app = FastAPI(
    title="Fitness AI Coach",
    description="Local fine-tuned Mistral/TinyLlama fitness coach with RAG + conversation memory.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": str(exc)})


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return HealthResponse(
        status="healthy",
        model="fitness-coach-local",
        knowledge_base_ready=rag_service is not None,
    )


@app.post("/api/ai/recommend", response_model=RecommendationResponse, tags=["Coach"])
async def get_recommendation(context: UserContext):
    """
    Daily fitness recommendation based on user's activity data.
    Called by Spring Boot aiservice instead of OpenAI/Gemini.
    """
    if rag_service is None:
        raise HTTPException(status_code=503, detail="Service initializing.")
    try:
        recommendation = await rag_service.get_recommendation(context)
        return RecommendationResponse(
            userId=context.userId,
            recommendation=recommendation,
            model="fitness-coach-local",
        )
    except Exception as e:
        logger.error(f"Error for user {context.userId}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ChatRequest(BaseModel):
    userId: str
    message: str
    age: int = 25
    weight: float = 70.0
    height: float = 175.0
    goal: str = "MAINTENANCE"


@app.post("/api/ai/chat", tags=["Coach"])
async def chat(request: ChatRequest):
    """
    Multi-turn chat endpoint — the model remembers previous messages.
    Used by the React frontend AICoach page.
    """
    if rag_service is None:
        raise HTTPException(status_code=503, detail="Service initializing.")

    ctx = UserContext(
        userId=request.userId,
        age=request.age,
        weight=request.weight,
        height=request.height,
        goal=request.goal,
        steps=0,
        caloriesBurned=0.0,
        workoutDuration=0,
        message=request.message,
    )

    try:
        response = await rag_service.get_recommendation(ctx)
        return {"userId": request.userId, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/ai/memory/{user_id}", tags=["Memory"])
async def clear_memory(user_id: str):
    """Reset conversation history for a user (e.g. on logout or new session)."""
    if rag_service is None:
        raise HTTPException(status_code=503, detail="Service initializing.")
    rag_service.memory.clear_history(user_id)
    return {"message": f"Conversation history cleared for user {user_id}."}


@app.get("/api/ai/training-status", tags=["Admin"])
async def training_status():
    """Shows continual learning stats."""
    if scheduler is None:
        return {"enabled": False}
    stats = scheduler.get_status()
    if rag_service:
        stats["conversation_db"] = rag_service.memory.count_training_conversations()
    return stats


@app.post("/api/ai/reset-knowledge", tags=["Admin"])
async def reset_knowledge():
    """Rebuild the ChromaDB fitness knowledge base from scratch."""
    if rag_service is None:
        raise HTTPException(status_code=503, detail="Service initializing.")
    rag_service.kb.reset()
    return {"message": "Knowledge base rebuilt."}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8085, reload=False)

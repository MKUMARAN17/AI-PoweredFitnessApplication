"""
Pydantic Models for the Fitness AI Coach API
=============================================
Shared request / response schemas used by main.py and rag_service.py.
"""

from typing import Optional, List
from pydantic import BaseModel


class HistoricalActivity(BaseModel):
    """One past activity entry for trend analysis."""
    steps: int = 0
    caloriesBurned: float = 0.0
    workoutDuration: int = 0
    workoutType: Optional[str] = None


class UserContext(BaseModel):
    """
    Full user context sent from Spring Boot aiservice.
    Maps exactly to the JSON sent by LocalAiService.java.
    """
    userId: str
    age: int = 25
    weight: float = 70.0        # kg
    height: float = 175.0       # cm
    goal: str = "MAINTENANCE"   # WEIGHT_LOSS | MUSCLE_GAIN | ENDURANCE | MAINTENANCE
    steps: int = 0
    caloriesBurned: float = 0.0
    workoutDuration: int = 0    # minutes
    workoutType: Optional[str] = None
    message: Optional[str] = None
    historicalData: Optional[List[HistoricalActivity]] = None


class RecommendationResponse(BaseModel):
    """Response returned for /api/ai/recommend."""
    userId: str
    recommendation: str
    model: str = "fitness-coach-local"


class HealthResponse(BaseModel):
    """Response returned for /health."""
    status: str
    model: str
    knowledge_base_ready: bool

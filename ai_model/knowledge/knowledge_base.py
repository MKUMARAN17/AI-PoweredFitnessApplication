"""
Fitness Knowledge Base — ChromaDB Vector Store
===============================================
Stores fitness knowledge chunks that are retrieved at inference time
to ground the model's recommendations in real exercise science.

The knowledge base is populated once on startup and persists to disk.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chromadb")
COLLECTION_NAME = "fitness_knowledge"

# ─────────────────────────────────────────────────────────────────────────────
# BUILT-IN FITNESS KNOWLEDGE CHUNKS
# These are embedded into ChromaDB on first run (or after reset).
# ─────────────────────────────────────────────────────────────────────────────
FITNESS_KNOWLEDGE = [
    # Weight loss fundamentals
    "Calorie deficit is the foundation of weight loss. A deficit of 500 calories/day leads to ~0.5kg loss per week. Never go below 1200 kcal for women or 1500 kcal for men without medical supervision.",
    "NEAT (Non-Exercise Activity Thermogenesis) accounts for 15-50% of daily calorie burn. Increasing steps from 5,000 to 10,000/day can add 200-400 extra calories burned without formal exercise.",
    "Protein helps preserve muscle mass during weight loss. Aim for 1.6-2.2g per kg of bodyweight. High protein also increases satiety and has the highest thermic effect of food (~30% of calories burned in digestion).",

    # Muscle building
    "Progressive overload is the primary driver of muscle growth. Increase weight, reps, sets, or difficulty over time. Even 1 extra rep per session adds up significantly over months.",
    "Muscle protein synthesis requires adequate leucine (~2-3g per meal) to trigger the anabolic response. This means ~30-40g of complete protein per meal for most people.",
    "Compound movements (squat, deadlift, bench press, row, overhead press) build muscle more efficiently than isolation exercises because they recruit more total muscle mass and trigger greater hormonal response.",
    "Rest and sleep are when muscle growth actually occurs. Growth hormone release peaks during deep sleep. Aim for 7-9 hours. Training without adequate sleep reduces gains by up to 60%.",

    # Endurance and cardio
    "Zone 2 cardio (conversational pace, 60-70% max HR) builds aerobic base, improves mitochondrial density, and enhances fat oxidation. 150+ minutes per week is the health minimum.",
    "VO2 max improves significantly with consistent aerobic training. Each 1 MET increase in VO2 max reduces cardiovascular mortality risk by 13%.",
    "The 10% rule: never increase weekly running distance by more than 10% to prevent overuse injuries like shin splints, IT band syndrome, and stress fractures.",
    "HIIT (High Intensity Interval Training) produces similar cardiovascular adaptations to steady-state cardio in half the time. Best ratio: 1:2 work-to-rest (e.g., 30 seconds hard, 60 seconds easy).",

    # Recovery
    "Muscle soreness (DOMS) peaks 24-48 hours after training and indicates microscopic muscle damage that triggers growth. Light movement, adequate protein, and sleep accelerate recovery.",
    "Overtraining syndrome symptoms: persistent fatigue, mood changes, performance decline, frequent illness. Treatment: 1-2 weeks rest, increase calories, prioritize sleep.",
    "Deload weeks (reducing volume by 40-50% every 4-8 weeks) allow accumulated fatigue to dissipate while retaining fitness adaptations. Performance often improves the week after a deload.",
    "Cold/contrast therapy reduces acute inflammation and DOMS. 10 minutes in cold water (10-15°C) or alternating hot/cold shower (2 min hot, 30 sec cold, repeat 3x) significantly reduces next-day soreness.",

    # Nutrition timing
    "Pre-workout nutrition (2-3 hours before): complex carbs + protein for sustained energy. 30-60 minutes before: simple carbs only (banana, rice cake). Avoid high fat/fiber pre-workout.",
    "Post-workout anabolic window is wider than once thought (up to 2 hours), but consuming 30-40g protein + carbs within 60 minutes optimizes muscle protein synthesis and glycogen replenishment.",
    "Carbohydrate loading before endurance events (60+ min): increase carb intake to 8-12g/kg body weight for 1-3 days before to maximize glycogen stores.",

    # Hydration
    "Dehydration of just 1-2% body weight (0.7-1.4kg for 70kg person) reduces strength by 5-8% and endurance by 10-20%. Drink 500ml water 2 hours before exercise.",
    "During exercise: 400-800ml per hour depending on sweat rate and temperature. Add electrolytes (sodium, potassium) for sessions over 60 minutes.",

    # Sleep and hormones
    "Testosterone and growth hormone peak during deep sleep stages 3 and 4. Just one night of poor sleep (under 6 hours) reduces testosterone by 10-15% and increases cortisol.",
    "Cortisol is catabolic — it breaks down muscle and promotes fat storage. Chronic stress and poor sleep chronically elevate cortisol and actively sabotage body composition goals.",

    # BMI and body composition
    "BMI is a screening tool, not a diagnostic. Athletes often have 'overweight' BMI due to muscle mass. Body fat percentage and waist circumference are better health indicators.",
    "Healthy body fat ranges: men 6-24%, women 16-30%. Athlete range: men 6-13%, women 14-20%. Below 5% (men) and 13% (women) is dangerous.",

    # Goal-specific calorie targets
    "For weight loss: eat at 20% below TDEE (Total Daily Energy Expenditure). For muscle gain: eat at 5-10% above TDEE. For maintenance: eat at TDEE. Calculate TDEE as BMR × activity multiplier.",
    "Mifflin-St Jeor BMR formula: Men: (10 × weight_kg) + (6.25 × height_cm) - (5 × age) + 5. Women: (10 × weight_kg) + (6.25 × height_cm) - (5 × age) - 161.",
    "Activity multipliers for TDEE: Sedentary (desk job, no exercise) × 1.2. Light activity (1-3 days/week) × 1.375. Moderate (3-5 days) × 1.55. Active (6-7 days) × 1.725.",

    # Supplementation
    "Creatine monohydrate: most researched supplement in sports science. 3-5g/day increases strength by 5-15% and muscle mass by 1-2kg over 4 weeks. Safe for long-term use.",
    "Caffeine: 3-6mg/kg body weight 30-60 min before exercise improves endurance by 12% and strength by 5-7%. Tolerance builds quickly — cycle off for 2 weeks every 2 months.",
    "Vitamin D3 deficiency (found in 40% of adults) reduces testosterone, impairs immune function, and decreases muscle strength. 2000-4000 IU/day for most people.",
]


class FitnessKnowledgeBase:
    """
    ChromaDB-backed vector store for fitness knowledge retrieval.
    """

    def __init__(self):
        self._chroma_available = self._init_chromadb()
        if not self._chroma_available:
            logger.warning("ChromaDB unavailable — using keyword fallback for knowledge retrieval.")

    def _init_chromadb(self) -> bool:
        try:
            import chromadb
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

            Path(CHROMA_PATH).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=CHROMA_PATH)

            embed_fn = SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"  # Small, fast, CPU-friendly (~80MB)
            )

            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=embed_fn,
            )

            if self._collection.count() == 0:
                logger.info("Populating ChromaDB knowledge base...")
                self._collection.add(
                    documents=FITNESS_KNOWLEDGE,
                    ids=[f"chunk_{i}" for i in range(len(FITNESS_KNOWLEDGE))],
                )
                logger.info(f"✅ Knowledge base populated with {len(FITNESS_KNOWLEDGE)} chunks.")
            else:
                logger.info(f"✅ Knowledge base loaded ({self._collection.count()} chunks).")

            return True

        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}")
            return False

    def query(self, query_text: str, n_results: int = 3) -> list[str]:
        """Retrieve the most relevant knowledge chunks for a query."""
        if not self._chroma_available:
            return self._keyword_fallback(query_text, n_results)

        try:
            results = self._collection.query(
                query_texts=[query_text],
                n_results=min(n_results, self._collection.count()),
            )
            return results["documents"][0] if results["documents"] else []
        except Exception as e:
            logger.error(f"ChromaDB query failed: {e}")
            return self._keyword_fallback(query_text, n_results)

    def _keyword_fallback(self, query_text: str, n_results: int) -> list[str]:
        """Simple keyword-based fallback when ChromaDB is unavailable."""
        query_lower = query_text.lower()
        scored = []
        for chunk in FITNESS_KNOWLEDGE:
            score = sum(1 for word in query_lower.split() if word in chunk.lower())
            scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored[:n_results]]

    def reset(self):
        """Rebuild the collection from scratch."""
        if not self._chroma_available:
            return
        try:
            self._client.delete_collection(COLLECTION_NAME)
            self._init_chromadb()
            logger.info("✅ Knowledge base reset and rebuilt.")
        except Exception as e:
            logger.error(f"Reset failed: {e}")

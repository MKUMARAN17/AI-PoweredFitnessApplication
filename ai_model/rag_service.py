"""
Fitness AI Coach — LangGraph Pipeline (Fine-Tuned Model Edition)
================================================================

Same 5-node LangGraph graph, but now uses:
1. Fine-tuned Mistral (your own trained model) instead of base Ollama
2. Conversation memory (MongoDB) for multi-turn context
3. Post-session learning collection for continual improvement

Graph:
  START → analyze_context → retrieve_knowledge → build_prompt
        → generate_response → validate_response → END
                 ↑_______________(retry loop)___|
"""

import logging
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage

from knowledge.knowledge_base import FitnessKnowledgeBase
from model.inference import FitnessModelInference
from conversation.memory import ConversationMemory
from models import UserContext

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# COACH PERSONALITY
# ─────────────────────────────────────────────────────────────────────────────
COACH_SYSTEM_PROMPT = """
You are Alex, a certified personal trainer and nutritionist with 10 years of experience.
You talk like a real human coach — warm, encouraging, direct. Never robotic or formal.

PERSONALITY:
- Like that knowledgeable friend who genuinely cares about your progress
- Celebrates every win, no matter how small
- Honest but never harsh — problems are addressed with solutions
- Casual natural language, occasional light humor, real-world examples
- SPECIFIC advice based on the person's ACTUAL numbers — never vague tips

EXPERTISE:
- Workout programming: progressive overload, splits, periodization
- Nutrition: macros, calorie targets, meal timing, supplements
- Recovery: sleep, DOMS, deload weeks, injury prevention
- Metrics: steps, calories, workout duration — you know what they mean

RESPONSE STYLE:
- Acknowledge where they are RIGHT NOW with their exact data
- Reference their specific numbers
- 2–3 concrete actionable recommendations
- End with motivation or an engaging question
- Under 200 words for daily check-ins
- Natural line breaks, no markdown headers, no bullet dashes
- Voice message from their coach — not a Wikipedia article

TONE:
- Always encouraging
- Great data: genuine enthusiasm
- Low data: supportive and solution-focused, never guilt-tripping
- Direct question: answer it first, then coach context
"""


# ─────────────────────────────────────────────────────────────────────────────
# GRAPH STATE
# ─────────────────────────────────────────────────────────────────────────────
class CoachingState(TypedDict):
    user_context:          UserContext
    conversation_history:  list        # Past turns from MongoDB memory
    user_summary:          str
    bmi:                   float
    bmi_label:             str
    tdee:                  int
    focus_areas:           list
    avg_steps:             int
    avg_calories:          float
    retrieved_knowledge:   str
    full_prompt:           str
    raw_response:          str
    retry_count:           int
    final_response:        str
    is_valid:              bool


# ─────────────────────────────────────────────────────────────────────────────
# NODE 1 — analyze_context
# ─────────────────────────────────────────────────────────────────────────────
def analyze_context(state: CoachingState) -> dict:
    ctx = state["user_context"]
    logger.info(f"[analyze_context] user={ctx.userId}, goal={ctx.goal}")

    height_m = ctx.height / 100
    bmi      = round(ctx.weight / (height_m ** 2), 1)
    bmi_label = (
        "underweight" if bmi < 18.5 else
        "healthy weight" if bmi < 25 else
        "slightly overweight" if bmi < 30 else
        "obese"
    )

    bmr  = 10 * ctx.weight + 6.25 * ctx.height - 5 * ctx.age
    tdee = round(bmr * 1.55)

    avg_steps, avg_calories = 0, 0.0
    if ctx.historicalData:
        avg_steps = round(sum(h.steps for h in ctx.historicalData) / len(ctx.historicalData))
        avg_calories = round(
            sum(h.caloriesBurned for h in ctx.historicalData) / len(ctx.historicalData), 1
        )

    focus_areas = [ctx.goal.upper()]
    if ctx.steps < 5000:             focus_areas.append("low_activity")
    if 0 < ctx.workoutDuration < 20: focus_areas.append("short_workout")
    if ctx.workoutDuration >= 45:    focus_areas.append("recovery")
    if ctx.caloriesBurned < 150 and ctx.workoutDuration > 0:
                                     focus_areas.append("nutrition")
    if ctx.message and len(ctx.message.strip()) > 5:
                                     focus_areas.append("user_question")

    goal_labels = {
        "WEIGHT_LOSS":  "lose weight",
        "MUSCLE_GAIN":  "build muscle",
        "ENDURANCE":    "improve endurance",
        "MAINTENANCE":  "maintain fitness",
    }

    history_line = ""
    if ctx.historicalData:
        history_line = (
            f"\nHistory ({len(ctx.historicalData)} sessions): "
            f"avg {avg_steps:,} steps, avg {avg_calories} kcal/session."
        )

    user_summary = f"""USER:
- Age: {ctx.age} | {ctx.weight}kg | {ctx.height}cm | BMI: {bmi} ({bmi_label})
- Goal: {goal_labels.get(ctx.goal.upper(), ctx.goal)} | TDEE: ~{tdee} kcal/day

TODAY:
- Steps: {ctx.steps:,} | Calories burned: {ctx.caloriesBurned} kcal
- Workout: {ctx.workoutDuration} min of {ctx.workoutType or 'general training'}
{history_line}
MESSAGE: "{ctx.message or 'Give me my daily fitness recommendation.'}" """.strip()

    return {
        "bmi": bmi, "bmi_label": bmi_label, "tdee": tdee,
        "avg_steps": avg_steps, "avg_calories": avg_calories,
        "focus_areas": focus_areas, "user_summary": user_summary, "retry_count": 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 2 — retrieve_knowledge
# ─────────────────────────────────────────────────────────────────────────────
def make_retrieve_node(kb: FitnessKnowledgeBase):
    def retrieve_knowledge(state: CoachingState) -> dict:
        ctx = state["user_context"]
        focus_areas = state["focus_areas"]

        query_map = {
            "WEIGHT_LOSS":   "weight loss calorie deficit fat burning",
            "MUSCLE_GAIN":   "muscle building progressive overload protein",
            "ENDURANCE":     "endurance running aerobic stamina",
            "MAINTENANCE":   "fitness maintenance healthy habits",
            "recovery":      "recovery sleep rest DOMS soreness",
            "nutrition":     "nutrition macros protein meal timing",
            "low_activity":  "steps walking daily movement NEAT",
            "short_workout": "short workout HIIT efficient time-saving",
            "user_question": ctx.message or "",
        }

        seen, chunks = set(), []
        for c in kb.query(query_map.get(ctx.goal.upper(), "fitness"), n_results=3):
            if c not in seen: seen.add(c); chunks.append(c)
        for area in focus_areas:
            q = query_map.get(area)
            if not q: continue
            for c in kb.query(q, n_results=2):
                if c not in seen: seen.add(c); chunks.append(c)

        return {"retrieved_knowledge": "\n\n---\n\n".join(chunks[:6])}
    return retrieve_knowledge


# ─────────────────────────────────────────────────────────────────────────────
# NODE 3 — build_prompt
# Includes conversation history for multi-turn context
# ─────────────────────────────────────────────────────────────────────────────
def build_prompt(state: CoachingState) -> dict:
    history = state.get("conversation_history", [])
    history_section = ""
    if history:
        turns = []
        for msg in history:
            label = "User" if msg["role"] == "user" else "Alex (you)"
            turns.append(f"{label}: {msg['content']}")
        history_section = "\n\nPREVIOUS CONVERSATION CONTEXT:\n" + "\n\n".join(turns)

    prompt = f"""User fitness data:

{state["user_summary"]}

Relevant fitness knowledge:

{state["retrieved_knowledge"]}
{history_section}

Give this person a personalized coaching recommendation. Be Alex — warm, specific, human."""

    return {"full_prompt": prompt}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 4 — generate_response (uses fine-tuned model)
# ─────────────────────────────────────────────────────────────────────────────
def make_generate_node(model: FitnessModelInference):
    def generate_response(state: CoachingState) -> dict:
        attempt = state.get("retry_count", 0) + 1
        logger.info(f"[generate_response] Attempt {attempt}...")
        response = model.generate(
            system_prompt=COACH_SYSTEM_PROMPT,
            user_message=state["full_prompt"],
            max_new_tokens=512,
            temperature=0.75,
        )
        return {"raw_response": response, "retry_count": attempt}
    return generate_response


# ─────────────────────────────────────────────────────────────────────────────
# NODE 5 — validate_response
# ─────────────────────────────────────────────────────────────────────────────
def validate_response(state: CoachingState) -> dict:
    import re
    raw = state["raw_response"]
    retry_count = state.get("retry_count", 1)
    issues = []

    if len(raw) < 80:          issues.append("too_short")
    if raw.lower().startswith(("i cannot", "i'm sorry", "as an ai")): issues.append("refusal")
    if len(raw) > 2000:        raw = raw[:2000].rsplit(". ", 1)[0] + "."
    raw = re.sub(r"\n{3,}", "\n\n", raw)

    is_valid = (not issues) or (retry_count >= 2)
    if issues and not is_valid:
        logger.warning(f"[validate_response] Issues: {issues} — retrying.")

    return {"is_valid": is_valid, "final_response": raw if is_valid else "", "raw_response": raw}


def route_after_validation(state: CoachingState) -> str:
    return END if state["is_valid"] else "generate_response"


# ─────────────────────────────────────────────────────────────────────────────
# GRAPH BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def build_coaching_graph(model: FitnessModelInference, kb: FitnessKnowledgeBase):
    graph = StateGraph(CoachingState)

    graph.add_node("analyze_context",    analyze_context)
    graph.add_node("retrieve_knowledge", make_retrieve_node(kb))
    graph.add_node("build_prompt",       build_prompt)
    graph.add_node("generate_response",  make_generate_node(model))
    graph.add_node("validate_response",  validate_response)

    graph.add_edge(START,                "analyze_context")
    graph.add_edge("analyze_context",    "retrieve_knowledge")
    graph.add_edge("retrieve_knowledge", "build_prompt")
    graph.add_edge("build_prompt",       "generate_response")
    graph.add_edge("generate_response",  "validate_response")
    graph.add_conditional_edges(
        "validate_response",
        route_after_validation,
        {END: END, "generate_response": "generate_response"},
    )

    return graph.compile()


# ─────────────────────────────────────────────────────────────────────────────
# SERVICE CLASS
# ─────────────────────────────────────────────────────────────────────────────
class FitnessRAGService:
    def __init__(self):
        logger.info("🤖 Initializing FitnessRAGService (fine-tuned model + LangGraph)...")
        self.kb     = FitnessKnowledgeBase()
        self.model  = FitnessModelInference()
        self.memory = ConversationMemory()
        self.graph  = build_coaching_graph(self.model, self.kb)
        logger.info("✅ FitnessRAGService ready.")

    async def get_recommendation(self, ctx: UserContext) -> str:
        """Run the LangGraph pipeline; persist conversation to memory."""

        # Load conversation history for multi-turn context
        history = self.memory.get_recent_history(ctx.userId)

        initial_state: CoachingState = {
            "user_context":         ctx,
            "conversation_history": history,
            "user_summary":         "",
            "bmi":                  0.0,
            "bmi_label":            "",
            "tdee":                 0,
            "focus_areas":          [],
            "avg_steps":            0,
            "avg_calories":         0.0,
            "retrieved_knowledge":  "",
            "full_prompt":          "",
            "raw_response":         "",
            "retry_count":          0,
            "final_response":       "",
            "is_valid":             False,
        }

        final_state = await self.graph.ainvoke(initial_state)
        response    = final_state["final_response"] or final_state["raw_response"]

        # Persist this turn to memory (enables multi-turn conversations)
        user_msg = ctx.message or "Daily fitness check-in."
        self.memory.add_message(ctx.userId, "user", user_msg)
        self.memory.add_message(ctx.userId, "assistant", response)

        # Collect full conversation for future training
        full_convo_messages = [
            {"role": "system", "content": COACH_SYSTEM_PROMPT},
            *history,
            {"role": "user",      "content": user_msg},
            {"role": "assistant", "content": response},
        ]
        self.memory.save_conversation_for_training(ctx.userId, full_convo_messages)

        return response

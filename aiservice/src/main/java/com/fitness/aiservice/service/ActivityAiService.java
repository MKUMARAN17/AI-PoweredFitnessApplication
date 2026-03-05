package com.fitness.aiservice.service;

import com.fitness.aiservice.model.Activity;
import com.fitness.aiservice.model.Recommendation;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Generates AI recommendations for logged activities.
 * Now powered by the local Python AI service (ai_model/main.py)
 * instead of OpenAI or Gemini.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class ActivityAiService {

  private final LocalAiService localAiService;

  public Recommendation generateRecommendation(Activity activity) {
    try {
      Map<String, Object> payload = buildUserContext(activity);
      String aiResponse = localAiService.getRecommendation(payload);
      log.info("Local AI response for activity {}: {}", activity.getId(), aiResponse);
      return buildRecommendation(activity, aiResponse);
    } catch (Exception e) {
      log.error("Failed to generate AI recommendation for activity {}. Falling back to default.", activity.getId(), e);
      return createDefaultRecommendation(activity);
    }
  }

  /**
   * Build the UserContext payload expected by the Python /api/ai/recommend
   * endpoint.
   * Maps Activity fields to the Pydantic UserContext schema.
   */
  private Map<String, Object> buildUserContext(Activity activity) {
    Map<String, Object> payload = new HashMap<>();
    payload.put("userId", activity.getUserId() != null ? activity.getUserId() : "unknown");
    payload.put("goal", "MAINTENANCE"); // Activities don't carry goal — use default
    payload.put("workoutType", activity.getType() != null ? activity.getType() : "General Training");
    payload.put("workoutDuration", activity.getDuration() != null ? activity.getDuration() : 0);
    payload.put("caloriesBurned",
        activity.getCaloriesBurned() != null ? activity.getCaloriesBurned().doubleValue() : 0.0);
    payload.put("steps", extractSteps(activity));
    payload.put("age", 30); // Default — could be fetched from userservice
    payload.put("weight", 75.0); // Default — could be fetched from userservice
    payload.put("height", 175.0); // Default — could be fetched from userservice
    payload.put("message", buildActivityPrompt(activity));
    return payload;
  }

  /**
   * Construct a message that describes the activity for the AI coach.
   */
  private String buildActivityPrompt(Activity activity) {
    StringBuilder sb = new StringBuilder();
    sb.append("I just completed a ");
    if (activity.getDuration() != null) {
      sb.append(activity.getDuration()).append("-minute ");
    }
    if (activity.getType() != null) {
      sb.append(activity.getType());
    } else {
      sb.append("workout");
    }
    if (activity.getCaloriesBurned() != null && activity.getCaloriesBurned() > 0) {
      sb.append(" and burned ").append(activity.getCaloriesBurned()).append(" calories");
    }
    sb.append(
        ". Please analyze my performance and give me specific recommendations for improvement, next workout suggestions, and safety tips.");
    return sb.toString();
  }

  /**
   * Extract steps from additionalMetrics if present.
   */
  private int extractSteps(Activity activity) {
    if (activity.getAdditionalMetrics() == null)
      return 0;
    Object steps = activity.getAdditionalMetrics().get("steps");
    if (steps == null)
      return 0;
    try {
      return Integer.parseInt(steps.toString());
    } catch (NumberFormatException e) {
      return 0;
    }
  }

  /**
   * The local AI returns a single plain-text coaching response.
   * We parse it into the structured Recommendation format.
   *
   * The Python model is prompted to give:
   * - Overall analysis
   * - Concrete improvement points
   * - Next workout suggestion
   * - Safety reminders
   *
   * We split on sentence boundaries to fill the recommendation fields.
   */
  private Recommendation buildRecommendation(Activity activity, String aiText) {
    // Split the response into sentences for structured fields
    String[] sentences = aiText.split("(?<=[.!?])\\s+");

    // First 2-3 sentences = analysis
    String analysis = joinSentences(sentences, 0, Math.min(3, sentences.length));

    // Extract improvement hints (look for sentences with action words)
    List<String> improvements = extractActionSentences(sentences,
        new String[] { "try", "increase", "add", "improve", "should", "consider", "aim", "push", "need" },
        2);

    // Suggestions (workout-related sentences)
    List<String> suggestions = extractActionSentences(sentences,
        new String[] { "workout", "session", "exercise", "train", "run", "lift", "next", "week" },
        2);

    // Safety (sentences about safety, rest, hydration, warm-up)
    List<String> safety = extractActionSentences(sentences,
        new String[] { "safety", "rest", "warm", "hydrat", "listen", "injury", "stretch", "cool", "recover" },
        2);

    // Fallbacks
    if (improvements.isEmpty())
      improvements = Collections.singletonList("Maintain consistency with your training.");
    if (suggestions.isEmpty())
      suggestions = Collections.singletonList("Continue with your current routine and add progressive overload.");
    if (safety.isEmpty())
      safety = Arrays.asList("Always warm up before exercise.", "Stay hydrated.", "Listen to your body.");

    return Recommendation.builder()
        .activityId(activity.getId())
        .userId(activity.getUserId())
        .activityType(activity.getType())
        .recommendation(analysis)
        .improvements(improvements)
        .suggestion(suggestions)
        .safety(safety)
        .createdAt(LocalDateTime.now())
        .build();
  }

  private String joinSentences(String[] sentences, int from, int to) {
    return String.join(" ", Arrays.copyOfRange(sentences, from, to)).trim();
  }

  private List<String> extractActionSentences(String[] sentences, String[] keywords, int max) {
    List<String> result = new java.util.ArrayList<>();
    for (String sentence : sentences) {
      if (result.size() >= max)
        break;
      String lower = sentence.toLowerCase();
      for (String kw : keywords) {
        if (lower.contains(kw)) {
          result.add(sentence.trim());
          break;
        }
      }
    }
    return result;
  }

  private Recommendation createDefaultRecommendation(Activity activity) {
    return Recommendation.builder()
        .activityId(activity.getId())
        .userId(activity.getUserId())
        .activityType(activity.getType())
        .recommendation("Great effort on your " + (activity.getType() != null ? activity.getType() : "workout")
            + "! Keep up the consistency.")
        .improvements(
            Collections.singletonList("Continue with your current routine and focus on progressive overload."))
        .suggestion(Collections.singletonList("Consider consulting a fitness professional for a personalized plan."))
        .safety(Arrays.asList(
            "Always warm up before exercise",
            "Stay hydrated throughout your workout",
            "Listen to your body and rest when needed"))
        .createdAt(LocalDateTime.now())
        .build();
  }
}

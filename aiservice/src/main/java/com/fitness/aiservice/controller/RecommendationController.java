package com.fitness.aiservice.controller;

import com.fitness.aiservice.model.Activity;
import com.fitness.aiservice.model.Recommendation;
import com.fitness.aiservice.service.ActivityMessageListener;
import com.fitness.aiservice.service.RecommendationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * REST controller for AI recommendations.
 *
 * All AI calls now go to the local Python service (port 8085),
 * not OpenAI or Gemini — no API key needed.
 */
@RestController
@RequiredArgsConstructor
@Slf4j
@RequestMapping("/api/recommendations")
public class RecommendationController {

    private final RecommendationService service;
    private final ActivityMessageListener activityMessageListener;

    @GetMapping("/user")
    public ResponseEntity<List<Recommendation>> getUserRecommendation(
            @RequestHeader("X-User-Id") String userId) {
        return ResponseEntity.ok(service.getUserRecommendation(userId));
    }

    @GetMapping("/activity/{activityId}")
    public ResponseEntity<Recommendation> getActivityRecommendation(
            @PathVariable String activityId) {
        return ResponseEntity.ok(service.getActivityRecommendation(activityId));
    }

    /**
     * Unified endpoint for:
     * - Chat messages from AICoach page → { "prompt": "...", "userId": "...",
     * "goal": "..." }
     * - Activity processing → { "id": "...", "userId": "...", "type": "...", ... }
     */
    @PostMapping("/process")
    public ResponseEntity<Map<String, String>> processActivity(
            @RequestBody Map<String, Object> requestBody,
            @RequestHeader(value = "X-User-Id", required = false) String headerUserId) {

        Map<String, String> responseBody = new HashMap<>();

        if (requestBody.containsKey("prompt")) {
            // ── Chat message from AICoach page ────────────────────────────
            String prompt = (String) requestBody.get("prompt");

            // Resolve userId: prefer request body, fall back to header
            String userId = requestBody.containsKey("userId")
                    ? (String) requestBody.get("userId")
                    : (headerUserId != null ? headerUserId : "anonymous");

            String goal = requestBody.containsKey("goal")
                    ? (String) requestBody.get("goal")
                    : "MAINTENANCE";

            log.info("Chat request from user {} (goal={}): {}", userId, goal, prompt);
            String response = service.getChatResponse(userId, prompt, goal);
            responseBody.put("message", response);

        } else {
            // ── Activity object processing ────────────────────────────────
            Activity activity = new Activity();
            if (requestBody.containsKey("id"))
                activity.setId((String) requestBody.get("id"));
            if (requestBody.containsKey("userId"))
                activity.setUserId((String) requestBody.get("userId"));
            if (requestBody.containsKey("type"))
                activity.setType((String) requestBody.get("type"));
            if (requestBody.containsKey("duration") && requestBody.get("duration") != null)
                activity.setDuration(Integer.parseInt(requestBody.get("duration").toString()));
            if (requestBody.containsKey("caloriesBurned") && requestBody.get("caloriesBurned") != null)
                activity.setCaloriesBurned(Integer.parseInt(requestBody.get("caloriesBurned").toString()));

            activityMessageListener.processActivity(activity);
            responseBody.put("message", "Activity processing started");
        }

        return ResponseEntity.ok(responseBody);
    }

    /**
     * Clear conversation history for a user.
     */
    @DeleteMapping("/memory/{userId}")
    public ResponseEntity<Map<String, String>> clearMemory(@PathVariable String userId) {
        log.info("Resetting conversation memory for user: {}", userId);
        service.clearChatHistory(userId);
        return ResponseEntity.ok(Map.of("message", "History cleared"));
    }

    /**
     * Health check — proxies to the local Python AI service.
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> healthCheck() {
        boolean aiHealthy = service.isAiServiceHealthy();
        Map<String, Object> status = new HashMap<>();
        status.put("aiservice", "up");
        status.put("localAiModel", aiHealthy ? "up" : "down");
        status.put("message", aiHealthy
                ? "Local AI model is running on port 8085"
                : "Local AI model is NOT running — start ai_model/main.py");
        return ResponseEntity.ok(status);
    }
}

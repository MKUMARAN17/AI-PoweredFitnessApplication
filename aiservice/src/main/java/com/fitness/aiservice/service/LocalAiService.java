package com.fitness.aiservice.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;

import java.time.Duration;
import java.util.Map;

/**
 * Replaces OpenAiService / GeminiService.
 *
 * Calls the local Python FastAPI server (ai_model/main.py) running on port
 * 8085.
 * No external API key required.
 *
 * Two main operations:
 * 1. getRecommendation(UserContext) → POST /api/ai/recommend
 * 2. getChatResponse(userId, msg) → POST /api/ai/chat
 */
@Service
@Slf4j
public class LocalAiService {

    private final WebClient webClient;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${local.ai.url:http://localhost:8085}")
    private String localAiUrl;

    public LocalAiService(WebClient.Builder webClientBuilder) {
        this.webClient = webClientBuilder.build();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Activity recommendation (called when a new activity is logged)
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Send activity data to the local AI and get back a plain-text recommendation.
     *
     * @param payload Map matching the Python UserContext schema:
     *                userId, age, weight, height, goal, steps, caloriesBurned,
     *                workoutDuration, workoutType, message
     * @return Plain-text coaching recommendation
     */
    public String getRecommendation(Map<String, Object> payload) {
        try {
            String raw = webClient.post()
                    .uri(localAiUrl + "/api/ai/recommend")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(payload)
                    .retrieve()
                    .bodyToMono(String.class)
                    .timeout(Duration.ofSeconds(120)) // CPU inference can be slow
                    .block();

            // Response: { "userId": "...", "recommendation": "...", "model": "..." }
            JsonNode node = objectMapper.readTree(raw);
            return node.path("recommendation").asText("No recommendation generated.");

        } catch (WebClientResponseException e) {
            log.error("Local AI error {}: {}", e.getStatusCode(), e.getResponseBodyAsString());
            throw new RuntimeException("Local AI service error: " + e.getResponseBodyAsString(), e);
        } catch (Exception e) {
            log.error("Failed to contact local AI service at {}", localAiUrl, e);
            throw new RuntimeException("Cannot reach local AI service (is ai_model/main.py running on port 8085?)", e);
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Multi-turn chat (used by AICoach page via /api/recommendations/process)
    // ─────────────────────────────────────────────────────────────────────────

    public String getChatResponse(String userId, String message, String goal) {
        Map<String, Object> payload = Map.of(
                "userId", userId,
                "message", message,
                "goal", goal != null ? goal : "MAINTENANCE");

        try {
            String raw = webClient.post()
                    .uri(localAiUrl + "/api/ai/chat")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(payload)
                    .retrieve()
                    .bodyToMono(String.class)
                    .timeout(Duration.ofSeconds(120))
                    .block();

            // Response: { "userId": "...", "response": "..." }
            JsonNode node = objectMapper.readTree(raw);
            return node.path("response").asText("I couldn't generate a response. Please try again.");

        } catch (WebClientResponseException e) {
            log.error("Local AI chat error {}: {}", e.getStatusCode(), e.getResponseBodyAsString());
            throw new RuntimeException("Local AI chat error: " + e.getResponseBodyAsString(), e);
        } catch (Exception e) {
            log.error("Failed to contact local AI chat endpoint", e);
            throw new RuntimeException("Cannot reach local AI chat service (is ai_model/main.py running on port 8085?)",
                    e);
        }
    }

    /**
     * Clear user conversation history in Python memory.
     */
    public void clearMemory(String userId) {
        try {
            webClient.delete()
                    .uri(localAiUrl + "/api/ai/memory/" + userId)
                    .retrieve()
                    .toBodilessEntity()
                    .timeout(Duration.ofSeconds(10))
                    .block();
        } catch (Exception e) {
            log.error("Failed to clear memory for user: {}", userId, e);
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Health check
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Ping the local AI service health endpoint.
     *
     * @return true if the service is healthy, false otherwise
     */
    public boolean isHealthy() {
        try {
            String raw = webClient.get()
                    .uri(localAiUrl + "/health")
                    .retrieve()
                    .bodyToMono(String.class)
                    .timeout(Duration.ofSeconds(5))
                    .block();

            JsonNode node = objectMapper.readTree(raw);
            return "healthy".equals(node.path("status").asText());
        } catch (Exception e) {
            log.warn("Local AI health check failed: {}", e.getMessage());
            return false;
        }
    }
}

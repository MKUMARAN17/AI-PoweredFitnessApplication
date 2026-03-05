package com.fitness.aiservice.service;

import com.fitness.aiservice.model.Recommendation;
import com.fitness.aiservice.repo.RecommendationRepo;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * Recommendation service — now routes all AI calls through LocalAiService
 * (the local Python FastAPI at port 8085) instead of OpenAI or Gemini.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class RecommendationService {

    private final RecommendationRepo repo;
    private final LocalAiService localAiService;

    public List<Recommendation> getUserRecommendation(String userId) {
        return repo.findByUserId(userId);
    }

    public Recommendation getActivityRecommendation(String activityId) {
        return repo.findByActivityId(activityId)
                .orElseThrow(() -> new RuntimeException("No recommendation found for activity: " + activityId));
    }

    /**
     * Multi-turn chat with the local AI coach.
     *
     * @param userId The user's ID (for conversation memory in Python)
     * @param prompt The user's chat message
     * @param goal   The user's fitness goal (optional, defaults to MAINTENANCE)
     * @return Plain-text coaching response
     */
    public String getChatResponse(String userId, String prompt, String goal) {
        log.info("Chat request from user {}: {}", userId, prompt);
        return localAiService.getChatResponse(userId, prompt, goal);
    }

    /**
     * Clear user conversation history in Python memory.
     */
    public void clearChatHistory(String userId) {
        localAiService.clearMemory(userId);
    }

    /**
     * Check if the local Python AI service is healthy.
     */
    public boolean isAiServiceHealthy() {
        return localAiService.isHealthy();
    }
}

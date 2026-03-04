package com.fitness.aiservice.service;

import com.fitness.aiservice.model.Recommendation;
import com.fitness.aiservice.repo.RecommendationRepo;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class RecommendationService {
    private final RecommendationRepo repo;
    private final OpenAiService openAiService;

    public List<Recommendation> getUserRecommendation(String userId) {
        return repo.findByUserId(userId);
    }

    public Recommendation getActivityRecommendation(String activityId) {
        return repo.findByActivityId(activityId)
                .orElseThrow(() -> new RuntimeException("No Recommendation for this activity" + activityId));
    }

    public String getChatResponse(String prompt) {
        return openAiService.getAnswer(prompt);
    }
}

package com.fitness.aiservice.service;

import com.fitness.aiservice.model.Activity;
import com.fitness.aiservice.model.Recommendation;
import com.fitness.aiservice.repo.RecommendationRepo;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Service
@Slf4j
@RequiredArgsConstructor
public class ActivityMessageListener {

    private final ActivityAiService aiService;
    private final RecommendationRepo repo;

    /**
     * Call this method to process an activity and generate an AI recommendation.
     * Previously this was triggered by a RabbitMQ @RabbitListener.
     * RabbitMQ has been removed; wire this up via a direct REST call or scheduler
     * as needed.
     */
    public void processActivity(Activity activity) {
        log.info("Processing activity for AI recommendation: {}", activity.getId());
        Recommendation recommendation = aiService.generateRecommendation(activity);
        log.info("Generated recommendation: {}", recommendation);
        repo.save(recommendation);
    }
}

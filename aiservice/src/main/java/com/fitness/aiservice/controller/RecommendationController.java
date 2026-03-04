package com.fitness.aiservice.controller;

import com.fitness.aiservice.model.Activity;
import com.fitness.aiservice.model.Recommendation;
import com.fitness.aiservice.service.ActivityMessageListener;
import com.fitness.aiservice.service.RecommendationService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.HashMap;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/recommendations")
public class RecommendationController {
    private final RecommendationService service;
    private final ActivityMessageListener activityMessageListener;

    @GetMapping("/user")
    public ResponseEntity<List<Recommendation>> getUserRecommendation(@RequestHeader("X-User-Id") String userId) {
        return ResponseEntity.ok(service.getUserRecommendation(userId));
    }

    @GetMapping("/activity/{activityId}")
    public ResponseEntity<Recommendation> getActivityRecommendation(@PathVariable String activityId) {
        return ResponseEntity.ok(service.getActivityRecommendation(activityId));
    }

    @PostMapping("/process")
    public ResponseEntity<Map<String, String>> processActivity(@RequestBody Map<String, Object> requestBody) {
        if (requestBody.containsKey("prompt")) {
            // It's a direct chat message from the user
            String prompt = (String) requestBody.get("prompt");
            String response = service.getChatResponse(prompt);
            Map<String, String> responseBody = new HashMap<>();
            responseBody.put("message", response);
            return ResponseEntity.ok(responseBody);
        } else {
            // It's an activity object processing request
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

            Map<String, String> responseBody = new HashMap<>();
            responseBody.put("message", "Activity processing started");
            return ResponseEntity.ok(responseBody);
        }
    }
}

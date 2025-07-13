package com.fitness.aiservice.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException; // Import for WebClient errors

import java.util.Map;
import lombok.extern.slf4j.Slf4j; // Import for logging

@Service
@Slf4j // Add this annotation for logging
public class GeminiService {

    private final WebClient webClient;

    @Value("${gemini.api.url}")
    private String geminiApiUrl;
    @Value("${gemini.api.key}")
    private String geminiApiKey;

    public GeminiService(WebClient.Builder webClientBuilder) {
        this.webClient = webClientBuilder.build();
    }

    public String getAnswer(String question){
        // Construct the request body as required by the Gemini API
        Map<String , Object> requestBody = Map.of(
                "contents",new Object[]{
                        Map.of("parts", new Object[]{
                                Map.of("text",question)
                        })
                }
        );

        // --- CRITICAL FIX: Correctly append the API key as a query parameter ---
        String fullApiUrl = geminiApiUrl + "?key=" + geminiApiKey;

        try {
            String response = webClient.post()
                    .uri(fullApiUrl) // Use the correctly constructed URL
                    .header("Content-Type","application/json") // Ensure correct header casing
                    .bodyValue(requestBody)
                    .retrieve()
                    .bodyToMono(String.class)
                    .block(); // Blocking call (synchronous)
            return response;
        } catch (WebClientResponseException e) {
            // Log specific HTTP errors from the Gemini API (e.g., 400, 403, 429, 500)
            log.error("Error calling Gemini API. Status: {}, Response Body: {}",
                    e.getStatusCode(), e.getResponseBodyAsString(), e);
            // Rethrow a more descriptive runtime exception or handle it as appropriate for your app
            throw new RuntimeException("Failed to get response from Gemini API: " + e.getResponseBodyAsString(), e);
        } catch (Exception e) {
            // Catch any other unexpected exceptions (e.g., network issues)
            log.error("An unexpected error occurred while calling Gemini API", e);
            throw new RuntimeException("An unexpected error occurred while processing AI request", e);
        }
    }
}
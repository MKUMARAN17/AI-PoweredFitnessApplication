package com.fitness.aiservice.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.util.retry.Retry;

import java.time.Duration;
import java.util.Map;
import lombok.extern.slf4j.Slf4j;

@Service
@Slf4j
public class OpenAiService {

    private final WebClient webClient;

    @Value("${openai.api.url}")
    private String openaiApiUrl;

    @Value("${openai.api.key}")
    private String openaiApiKey;

    public OpenAiService(WebClient.Builder webClientBuilder) {
        this.webClient = webClientBuilder.build();
    }

    public String getAnswer(String question) {
        Map<String, Object> requestBody = Map.of(
                "model", "gpt-4o-mini",
                "messages", new Object[] {
                        Map.of(
                                "role", "user",
                                "content", question)
                });

        try {
            String response = webClient.post()
                    .uri(openaiApiUrl)
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + openaiApiKey)
                    .bodyValue(requestBody)
                    .retrieve()
                    .bodyToMono(String.class)
                    .retryWhen(Retry.backoff(3, Duration.ofSeconds(2))
                            .filter(throwable -> throwable instanceof WebClientResponseException &&
                                    ((WebClientResponseException) throwable).getStatusCode().value() == 429))
                    .block();
            return response;
        } catch (WebClientResponseException e) {
            log.error("Error calling OpenAI API. Status: {}, Response Body: {}",
                    e.getStatusCode(), e.getResponseBodyAsString(), e);
            throw new RuntimeException("Failed to get response from OpenAI API: " + e.getResponseBodyAsString(), e);
        } catch (Exception e) {
            log.error("An unexpected error occurred while calling OpenAI API", e);
            throw new RuntimeException("An unexpected error occurred while processing AI request", e);
        }
    }
}

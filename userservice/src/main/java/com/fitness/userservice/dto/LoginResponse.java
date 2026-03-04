package com.fitness.userservice.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class LoginResponse {
    private UserResponse user;
    private String token; // JWT access token
    private String refreshToken; // Long-lived refresh token
    private long expiresIn; // Access token TTL in ms
}

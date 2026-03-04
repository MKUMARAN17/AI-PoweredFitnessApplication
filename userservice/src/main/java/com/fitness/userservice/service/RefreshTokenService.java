package com.fitness.userservice.service;

import com.fitness.userservice.model.RefreshToken;
import com.fitness.userservice.repository.RefreshTokenRepo;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;

@Service
@RequiredArgsConstructor
public class RefreshTokenService {

    private final RefreshTokenRepo refreshTokenRepo;
    private final JwtService jwtService;

    @Value("${jwt.refresh-expiration}")
    private long refreshExpirationMs;

    // ── Create ───────────────────────────────────────────────────────────────

    @Transactional
    public RefreshToken createRefreshToken(String userId) {
        // Revoke previous tokens for this user (one active session per user)
        refreshTokenRepo.deleteAllByUserId(userId);

        String tokenValue = jwtService.generateRefreshToken(userId);

        RefreshToken refreshToken = RefreshToken.builder()
                .token(tokenValue)
                .userId(userId)
                .expiresAt(Instant.now().plusMillis(refreshExpirationMs))
                .revoked(false)
                .build();

        return refreshTokenRepo.save(refreshToken);
    }

    // ── Verify ───────────────────────────────────────────────────────────────

    public RefreshToken verifyRefreshToken(String token) {
        RefreshToken refreshToken = refreshTokenRepo.findByToken(token)
                .orElseThrow(() -> new RuntimeException("Refresh token not found"));

        if (refreshToken.isRevoked()) {
            throw new RuntimeException("Refresh token has been revoked");
        }
        if (refreshToken.getExpiresAt().isBefore(Instant.now())) {
            refreshTokenRepo.delete(refreshToken);
            throw new RuntimeException("Refresh token expired. Please log in again.");
        }
        return refreshToken;
    }

    // ── Revoke / Logout ───────────────────────────────────────────────────────

    @Transactional
    public void revokeAllUserTokens(String userId) {
        refreshTokenRepo.deleteAllByUserId(userId);
    }
}

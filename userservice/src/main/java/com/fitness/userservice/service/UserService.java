package com.fitness.userservice.service;

import com.fitness.userservice.dto.LoginResponse;
import com.fitness.userservice.dto.RegisterRequest;
import com.fitness.userservice.dto.UserResponse;
import com.fitness.userservice.model.RefreshToken;
import com.fitness.userservice.model.User;
import com.fitness.userservice.repository.UserRepo;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepo userRepo;
    private final JwtService jwtService;
    private final RefreshTokenService refreshTokenService;

    private static final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    // ── Register ─────────────────────────────────────────────────────────────

    public UserResponse register(@Valid RegisterRequest request) {
        if (userRepo.existsByEmail(request.getEmail())) {
            throw new RuntimeException("Email already exists");
        }
        if (userRepo.existsByUsername(request.getUsername())) {
            throw new RuntimeException("Username already exists");
        }
        if (!request.getPassword().equals(request.getConfirmPassword())) {
            throw new RuntimeException("Passwords do not match");
        }

        User user = new User();
        user.setUsername(request.getUsername());
        user.setEmail(request.getEmail());
        user.setPassword(passwordEncoder.encode(request.getPassword())); // hash!
        user.setFirstName(request.getFirstName());
        user.setLastName(request.getLastName());

        User savedUser = userRepo.save(user);
        return mapToResponse(savedUser);
    }

    // ── Login ────────────────────────────────────────────────────────────────

    public LoginResponse login(String identifier, String password) {
        User user = userRepo.findByUsername(identifier)
                .or(() -> userRepo.findByEmail(identifier))
                .orElseThrow(() -> new RuntimeException("Invalid username/email or password"));

        if (!passwordEncoder.matches(password, user.getPassword())) {
            throw new RuntimeException("Invalid username/email or password");
        }

        String accessToken = jwtService.generateAccessToken(user.getId(), user.getEmail(), user.getRole().name());
        RefreshToken refreshToken = refreshTokenService.createRefreshToken(user.getId());

        return LoginResponse.builder()
                .user(mapToResponse(user))
                .token(accessToken)
                .refreshToken(refreshToken.getToken())
                .expiresIn(jwtService.getExpirationMs())
                .build();
    }

    // ── Refresh Token ─────────────────────────────────────────────────────────

    public LoginResponse refreshAccessToken(String rawRefreshToken) {
        RefreshToken verified = refreshTokenService.verifyRefreshToken(rawRefreshToken);

        User user = userRepo.findById(verified.getUserId())
                .orElseThrow(() -> new RuntimeException("User not found"));

        // Rotate refresh token (old one deleted, new one issued)
        RefreshToken newRefreshToken = refreshTokenService.createRefreshToken(user.getId());
        String newAccessToken = jwtService.generateAccessToken(user.getId(), user.getEmail(), user.getRole().name());

        return LoginResponse.builder()
                .user(mapToResponse(user))
                .token(newAccessToken)
                .refreshToken(newRefreshToken.getToken())
                .expiresIn(jwtService.getExpirationMs())
                .build();
    }

    // ── Logout ─────────────────────────────────────────────────────────────────

    public void logout(String userId) {
        refreshTokenService.revokeAllUserTokens(userId);
    }

    // ── Profile ───────────────────────────────────────────────────────────────

    public UserResponse getUserProfile(String userId) {
        User user = userRepo.findById(userId)
                .orElseThrow(() -> new RuntimeException("User not found"));
        return mapToResponse(user);
    }

    public Boolean existByUserId(String userId) {
        return userRepo.existsById(userId);
    }

    // ── Mapping ───────────────────────────────────────────────────────────────

    private UserResponse mapToResponse(User user) {
        return UserResponse.builder()
                .id(user.getId())
                .username(user.getUsername())
                .email(user.getEmail())
                .firstName(user.getFirstName())
                .lastName(user.getLastName())
                .createdAt(user.getCreatedAt())
                .updatedAt(user.getUpdatedAt())
                .build();
    }
}

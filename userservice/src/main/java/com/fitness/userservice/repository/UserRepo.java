package com.fitness.userservice.repository;

import com.fitness.userservice.model.User;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface UserRepo extends JpaRepository<User, String> {

    boolean existsByEmail(String email);

    boolean existsByUsername(String username);

    java.util.Optional<User> findByEmail(String email);

    java.util.Optional<User> findByUsername(String username);
}

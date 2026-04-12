package com.gifpt.security.auth.user;

import com.gifpt.user.domain.User;
import lombok.Getter;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

import java.util.Collection;
import java.util.Collections;

@Getter
@SuppressWarnings("null")
public class CustomUserPrincipal implements UserDetails {
    private final User user;

    public CustomUserPrincipal(User user) {
        this.user = user;
    }

    /**
     * Build a lightweight principal from JWT claims, skipping the database
     * round-trip. The returned User entity is transient (not managed) and only
     * carries the fields needed by downstream controllers (id, email).
     */
    public static CustomUserPrincipal fromTokenClaims(Long userId, String email) {
        User stub = new User();
        stub.setId(userId);
        stub.setEmail(email);
        // status defaults to "ACTIVE" on the entity; passwordHash is unused
        // post-login (auth uses the JWT signature, not the password).
        stub.setPasswordHash("");
        return new CustomUserPrincipal(stub);
    }

    public Long getId() {
        return user.getId();
    }

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER"));
    }

    @Override
    public String getPassword() {
        return user.getPasswordHash();
    }

    @Override
    public String getUsername() {
        return user.getEmail();
    }

    @Override
    public boolean isAccountNonExpired() {
        return true;
    }

    @Override
    public boolean isAccountNonLocked() {
        return "ACTIVE".equals(user.getStatus());
    }

    @Override
    public boolean isCredentialsNonExpired() {
        return true;
    }

    @Override
    public boolean isEnabled() {
        return "ACTIVE".equals(user.getStatus());
    }
}



package com.gifpt.security.auth.service;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.lang.Nullable;
import org.springframework.stereotype.Service;
import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

@Service
@SuppressWarnings("null")
public class JwtService {

  public static final String CLAIM_USER_ID = "uid";
  public static final String CLAIM_ROLE = "role";

  private final SecretKey key;
  private final long expiresInMs;

  public JwtService(
      @Value("${gifpt.jwt.secret}") String secret,
      @Value("${gifpt.jwt.expires-in-ms}") long expiresInMs
  ) {
    this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    this.expiresInMs = expiresInMs;
  }

  /**
   * Generate an access token carrying the user's id and role so downstream
   * filters can authenticate without a database round-trip.
   */
  public String generateAccessToken(Long userId, String email, String role) {
    Map<String, Object> claims = new HashMap<>();
    claims.put(CLAIM_USER_ID, userId);
    claims.put(CLAIM_ROLE, role);
    long now = System.currentTimeMillis();
    return Jwts.builder()
        .subject(email)
        .claims(claims)
        .issuedAt(new Date(now))
        .expiration(new Date(now + expiresInMs))
        .signWith(key)
        .compact();
  }

  /**
   * Validate signature + expiration and return parsed claims.
   * Returns null if the token is invalid or expired.
   */
  @Nullable
  public Claims parseClaims(String token) {
    try {
      Claims claims = Jwts.parser().verifyWith(key).build()
          .parseSignedClaims(token).getPayload();
      Date exp = claims.getExpiration();
      if (exp == null || !exp.after(new Date())) {
        return null;
      }
      return claims;
    } catch (Exception e) {
      return null;
    }
  }
}

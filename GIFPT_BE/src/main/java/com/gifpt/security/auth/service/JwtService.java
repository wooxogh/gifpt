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
  public static final String CLAIM_STATUS = "status";
  public static final String STATUS_ACTIVE = "ACTIVE";

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
   * Generate an access token carrying the user's id, status, and role so
   * downstream filters can authenticate (and gate disabled accounts) without
   * a database round-trip.
   *
   * Status freshness caveat: a status change after token issuance only takes
   * effect once the token expires. Tighten {@code gifpt.jwt.expires-in-ms} or
   * add a revocation list if shorter lockout is required.
   */
  public String generateAccessToken(Long userId, String email, String status, String role) {
    Map<String, Object> claims = new HashMap<>();
    claims.put(CLAIM_USER_ID, userId);
    claims.put(CLAIM_STATUS, status);
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

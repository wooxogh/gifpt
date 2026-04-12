package com.gifpt.security.auth.jwt;

import io.jsonwebtoken.Claims;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.lang.NonNull;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import com.gifpt.security.auth.service.JwtService;
import com.gifpt.security.auth.user.CustomUserPrincipal;

import java.io.IOException;

@Component
@SuppressWarnings("null")
public class JwtAuthFilter extends OncePerRequestFilter {

  private final JwtService jwtService;

  public JwtAuthFilter(JwtService jwtService) {
    this.jwtService = jwtService;
  }

  @Override
  protected void doFilterInternal(@NonNull HttpServletRequest req, @NonNull HttpServletResponse res, @NonNull FilterChain chain)
      throws ServletException, IOException {

    String auth = req.getHeader("Authorization");
    if (auth != null && auth.startsWith("Bearer ")) {
      String token = auth.substring(7);
      if (SecurityContextHolder.getContext().getAuthentication() == null) {
        Claims claims = jwtService.parseClaims(token);
        if (claims != null) {
          String email = claims.getSubject();
          Number uidClaim = claims.get(JwtService.CLAIM_USER_ID, Number.class);
          String status = claims.get(JwtService.CLAIM_STATUS, String.class);
          // Reject tokens that lack required claims or were issued for a
          // non-active account. Status freshness is bounded by token TTL —
          // see JwtService#generateAccessToken for the trade-off rationale.
          if (email != null && uidClaim != null && JwtService.STATUS_ACTIVE.equals(status)) {
            CustomUserPrincipal principal = CustomUserPrincipal.fromTokenClaims(uidClaim.longValue(), email, status);
            var authToken = new UsernamePasswordAuthenticationToken(principal, null, principal.getAuthorities());
            authToken.setDetails(new WebAuthenticationDetailsSource().buildDetails(req));
            SecurityContextHolder.getContext().setAuthentication(authToken);
          }
        }
      }
    }
    chain.doFilter(req, res);
  }
  
  @Override
  protected boolean shouldNotFilter(@NonNull HttpServletRequest request) {
      // 공개/예외 경로는 필터 스킵
      String p = request.getRequestURI();
      return p.equals("/swagger-ui.html")
          || p.startsWith("/swagger-ui")
          || p.startsWith("/v3/api-docs")
          || p.startsWith("/healthz")
          || p.startsWith("/api/v1/auth/login")
          || p.startsWith("/api/v1/auth/refresh");
  }
}

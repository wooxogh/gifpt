package com.gifpt.security.auth.config;

import com.gifpt.security.auth.jwt.JwtAuthFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
@SuppressWarnings("null")
public class SecurityConfig {

  private final JwtAuthFilter jwtAuthFilter;

  public SecurityConfig(JwtAuthFilter jwtAuthFilter) {
    this.jwtAuthFilter = jwtAuthFilter;
  }

  @Bean
  public AuthenticationManager authenticationManager(AuthenticationConfiguration cfg) throws Exception {
    return cfg.getAuthenticationManager();
  }

  @Bean
  SecurityFilterChain security(HttpSecurity http) throws Exception {
    http
      .csrf(csrf -> csrf.disable())
      .cors(Customizer.withDefaults())
      .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
      .authorizeHttpRequests(auth -> auth
        .requestMatchers(
          "/healthz",
          "/actuator/health",
          "/actuator/health/**",
          "/v3/api-docs",
          "/v3/api-docs/**",
          "/swagger-ui/**",
          "/swagger-ui.html",
          "/api/v1/auth/**",
          "/v1/auth/**",
          "/api/v1/analysis/*/complete",
          "/api/v1/animate/**",
          "/api/v1/gallery"
        ).permitAll()
        .requestMatchers("/api/v1/workspaces/**").authenticated()
        .anyRequest().authenticated()
      )
      .httpBasic(basic -> basic.disable())
      .formLogin(form -> form.disable())
      .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class);

    return http.build();
  }

  @Bean
  org.springframework.web.cors.CorsConfigurationSource corsConfigurationSource(
  ) {
    var c = new org.springframework.web.cors.CorsConfiguration();
    c.setAllowedOrigins(java.util.List.of(
      "https://gifpt-front.vercel.app",
      "https://gifpt-kappa.vercel.app",
      "http://localhost:3000",
      "http://127.0.0.1:3000"
    ));
    c.setAllowedMethods(java.util.List.of("GET","POST","PUT","PATCH","DELETE","OPTIONS"));
    c.setAllowedHeaders(java.util.List.of("Authorization","Content-Type","X-Requested-With"));
    c.setExposedHeaders(java.util.List.of("Authorization","Set-Cookie"));
    c.setAllowCredentials(true);
    c.setMaxAge(3600L);
    var src = new org.springframework.web.cors.UrlBasedCorsConfigurationSource();
    src.registerCorsConfiguration("/**", c);
    return src;
  }
}

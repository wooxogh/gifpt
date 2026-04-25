package com.gifpt.analysis.controller;

import com.gifpt.analysis.domain.AnalysisJob;
import com.gifpt.analysis.domain.AnalysisStatus;
import com.gifpt.analysis.repository.AnalysisJobRepository;
import com.gifpt.file.service.S3StorageService;
import com.gifpt.security.auth.user.CustomUserPrincipal;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.lang.Nullable;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/animate")
@RequiredArgsConstructor
@SuppressWarnings("null")
public class AnimateController {

    private static final int MAX_ALGORITHM_LENGTH = 200;
    private static final int MAX_PROMPT_LENGTH = 8000;

    public record AnimateRequest(
            @NotBlank @Size(max = MAX_ALGORITHM_LENGTH) String algorithm,
            @Nullable @Size(max = MAX_PROMPT_LENGTH) String prompt
    ) {}

    private final S3StorageService s3StorageService;
    private final AnalysisJobRepository analysisJobRepository;
    private final RestClient.Builder restClientBuilder;

    // Experiment B: Redis status cache (present only under loadtest profile).
    @org.springframework.beans.factory.annotation.Autowired(required = false)
    private com.gifpt.analysis.cache.StatusCache statusCache;

    @Value("${gifpt.s3.bucket}")
    private String s3Bucket;

    @Value("${gifpt.ai-server.base-url}")
    private String aiServerBaseUrl;

    /**
     * GET /api/v1/animate?algorithm={name}
     *
     * Simple algorithm name lookup (backward compatible).
     * Anonymous: cache HIT → 200 + videoUrl; cache MISS → 401
     * Authenticated: cache HIT → 200 + videoUrl; cache MISS → 202 + jobId
     */
    @GetMapping
    public ResponseEntity<?> animate(
            @RequestParam String algorithm,
            @AuthenticationPrincipal @Nullable CustomUserPrincipal user
    ) {
        return doAnimate(algorithm, null, user);
    }

    /**
     * POST /api/v1/animate
     *
     * Extended endpoint: accepts algorithm name + optional prompt (description/pseudocode).
     * When prompt is provided, skips cache and uses the rich rendering pipeline.
     * Body: { "algorithm": "S3FIFO", "prompt": "S3FIFO uses three FIFO queues..." }
     */
    @PostMapping
    public ResponseEntity<?> animateWithPrompt(
            @Valid @RequestBody AnimateRequest body,
            @AuthenticationPrincipal @Nullable CustomUserPrincipal user
    ) {
        String algorithm = body.algorithm().trim();
        String rawPrompt = body.prompt();
        String prompt = rawPrompt == null ? null : rawPrompt.trim();
        if (prompt != null && prompt.isBlank()) prompt = null;
        return doAnimate(algorithm, prompt, user);
    }

    private ResponseEntity<?> doAnimate(String algorithm, @Nullable String prompt, @Nullable CustomUserPrincipal user) {
        String slug = normalizeSlug(algorithm);
        if (slug.isEmpty()) {
            return ResponseEntity.badRequest()
                    .body(Map.of("error", "invalid_algorithm", "message", "Algorithm name is empty or invalid after normalization"));
        }

        boolean hasPrompt = prompt != null && !prompt.isBlank();

        // Only check cache when there is no custom prompt
        if (!hasPrompt) {
            String s3Key = s3KeyForSlug(slug);
            boolean cacheHit = s3StorageService.objectExists(s3Key);

            if (cacheHit) {
                String videoUrl = "https://" + s3Bucket + ".s3.amazonaws.com/" + s3Key;
                log.info("[ANIMATE] cache HIT slug={}", slug);
                return ResponseEntity.ok()
                        .header("X-Cache", "HIT")
                        .body(Map.of("status", "SUCCESS", "videoUrl", videoUrl));
            }
        }

        // Cache MISS or custom prompt — anonymous users cannot trigger generation
        if (user == null) {
            log.info("[ANIMATE] generation required, anonymous user slug={}", slug);
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .header("X-Cache", "MISS")
                    .body(Map.of("error", "login_required", "message", "로그인 후 생성 가능"));
        }

        // Dedup: reuse existing in-progress job for same slug (name-only requests)
        if (!hasPrompt) {
            var existing = analysisJobRepository.findFirstByAlgorithmSlugAndStatusInOrderByIdDesc(
                    slug, java.util.List.of(AnalysisStatus.PENDING, AnalysisStatus.RUNNING));
            if (existing.isPresent()) {
                log.info("[ANIMATE] dedup HIT slug={} existing_job_id={}", slug, existing.get().getId());
                return ResponseEntity.status(HttpStatus.ACCEPTED)
                        .header("X-Cache", "DEDUP")
                        .body(Map.of("status", existing.get().getStatus().name(),
                                     "jobId", existing.get().getId()));
            }
        }

        // Authenticated → create job + dispatch
        AnalysisJob job = AnalysisJob.builder()
                .userId(user.getId())
                .status(AnalysisStatus.PENDING)
                .prompt(hasPrompt ? prompt : algorithm)
                .algorithmSlug(hasPrompt ? null : slug)
                .build();
        analysisJobRepository.save(job);

        log.info("[ANIMATE] dispatching job_id={} slug={} hasPrompt={} userId={}",
                job.getId(), slug, hasPrompt, user.getId());

        // Build dispatch body as JSON string — avoids RestClient serialization issues
        StringBuilder jsonBody = new StringBuilder();
        jsonBody.append("{\"job_id\":").append(job.getId());
        jsonBody.append(",\"algorithm\":\"").append(algorithm.replace("\"", "\\\"")).append("\"");
        if (hasPrompt) {
            jsonBody.append(",\"prompt\":\"").append(prompt.replace("\"", "\\\"").replace("\n", "\\n")).append("\"");
        }
        jsonBody.append("}");

        try {
            RestClient restClient = restClientBuilder.baseUrl(aiServerBaseUrl).build();
            restClient.post()
                    .uri("/animate")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(jsonBody.toString())
                    .retrieve()
                    .toBodilessEntity();
        } catch (Exception e) {
            log.error("[ANIMATE] dispatch to AI server failed job_id={}", job.getId(), e);
            job.setStatus(AnalysisStatus.FAILED);
            job.setErrorMessage("AI server temporarily unavailable");
            analysisJobRepository.save(job);
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                    .body(Map.of("error", "ai_server_unavailable", "message", "AI server is temporarily unavailable"));
        }

        return ResponseEntity.status(HttpStatus.ACCEPTED)
                .header("X-Cache", "MISS")
                .body(Map.of("status", "PENDING", "jobId", job.getId()));
    }

    /**
     * GET /api/v1/animate/status/{jobId}
     *
     * Returns the current status and resultUrl of an animate job.
     * Only the job owner can poll.
     */
    @GetMapping("/status/{jobId}")
    public ResponseEntity<?> getStatus(
            @PathVariable Long jobId,
            @AuthenticationPrincipal @Nullable CustomUserPrincipal user
    ) {
        Long ownerId;
        Map<String, Object> response;

        Map<String, Object> cached = statusCache != null ? statusCache.get(jobId) : null;
        // Treat malformed cache entries (missing userId) as a miss so we don't NPE.
        if (cached != null && !(cached.get("userId") instanceof Number)) {
            cached = null;
        }
        if (cached != null) {
            ownerId = ((Number) cached.get("userId")).longValue();
            Map<String, Object> hit = new java.util.HashMap<>();
            hit.put("jobId", cached.get("jobId"));
            hit.put("status", cached.get("status"));
            hit.put("resultUrl", cached.getOrDefault("resultUrl", ""));
            hit.put("errorMessage", cached.getOrDefault("errorMessage", ""));
            // Map.of disallows nulls; an old cache entry with null fields would 500.
            hit.replaceAll((k, v) -> v == null ? "" : v);
            response = hit;
        } else {
            AnalysisJob job = analysisJobRepository.findById(jobId)
                    .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Job not found"));
            ownerId = job.getUserId();
            response = Map.of(
                    "jobId", job.getId(),
                    "status", job.getStatus().name(),
                    "resultUrl", job.getResultUrl() != null ? job.getResultUrl() : "",
                    "errorMessage", job.getErrorMessage() != null ? job.getErrorMessage() : ""
            );
            if (statusCache != null) {
                Map<String, Object> cacheValue = new java.util.HashMap<>(response);
                cacheValue.put("userId", ownerId);
                statusCache.put(jobId, cacheValue);
            }
        }

        if (user == null || !ownerId.equals(user.getId())) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN)
                    .body(Map.of("error", "forbidden"));
        }

        return ResponseEntity.ok(response);
    }

    /**
     * Mirror of Python normalize_slug() — must produce identical output so
     * both sides compute the same S3 cache key.
     *
     * "A*"            -> "a_star"
     * "Floyd-Warshall"-> "floyd_warshall"
     * "bubble sort"   -> "bubble_sort"
     */
    static String normalizeSlug(String name) {
        if (name == null || name.isBlank()) return "";
        String s = name.toLowerCase();
        s = s.replace("*", "_star").replace("+", "_plus");
        s = s.replace("-", "_").replace("/", "_").replace(" ", "_");
        s = s.replaceAll("[^a-z0-9_]", "");
        s = s.replaceAll("_+", "_").replaceAll("^_+|_+$", "");
        return s.length() > 64 ? s.substring(0, 64) : s;
    }

    /**
     * Compute the deterministic S3 key for a normalized slug.
     * Must match Python: hashlib.sha256(slug.encode()).hexdigest()
     */
    static String s3KeyForSlug(String slug) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(slug.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(64);
            for (byte b : digest) {
                hex.append(String.format("%02x", b));
            }
            return "animations/" + hex + ".mp4";
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 unavailable", e);
        }
    }
}

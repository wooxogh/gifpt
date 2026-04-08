package com.gifpt.analysis.controller;

import com.gifpt.analysis.domain.AnalysisJob;
import com.gifpt.analysis.domain.AnalysisStatus;
import com.gifpt.analysis.dto.GalleryItemResponse;
import com.gifpt.analysis.repository.AnalysisJobRepository;
import com.gifpt.security.auth.user.CustomUserPrincipal;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/gallery")
@RequiredArgsConstructor
public class GalleryController {

    private final AnalysisJobRepository analysisJobRepository;

    /**
     * GET /api/v1/gallery?page=0&size=12
     * Public — all successful algorithm animations, newest first.
     */
    @GetMapping
    public ResponseEntity<?> trending(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "12") int size
    ) {
        var pageable = PageRequest.of(page, Math.min(size, 48), Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<GalleryItemResponse> result = analysisJobRepository
                .findByStatusAndAlgorithmSlugIsNotNull(AnalysisStatus.SUCCESS, pageable)
                .map(GalleryController::toResponse);
        return ResponseEntity.ok(result);
    }

    /**
     * GET /api/v1/gallery/mine?page=0&size=12
     * Authenticated — current user's successful animations.
     */
    @GetMapping("/mine")
    public ResponseEntity<?> mine(
            @AuthenticationPrincipal CustomUserPrincipal user,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "12") int size
    ) {
        if (user == null) {
            return ResponseEntity.status(401).body(java.util.Map.of("error", "login_required"));
        }
        var pageable = PageRequest.of(page, Math.min(size, 48), Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<GalleryItemResponse> result = analysisJobRepository
                .findByUserIdAndStatusAndAlgorithmSlugIsNotNull(user.getId(), AnalysisStatus.SUCCESS, pageable)
                .map(GalleryController::toResponse);
        return ResponseEntity.ok(result);
    }

    private static GalleryItemResponse toResponse(AnalysisJob job) {
        return new GalleryItemResponse(
                job.getId(),
                job.getPrompt(),
                job.getAlgorithmSlug(),
                job.getResultUrl(),
                job.getCreatedAt()
        );
    }
}

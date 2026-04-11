package com.gifpt.analysis.controller;

import com.gifpt.analysis.dto.AnalysisCallbackDTO;
import com.gifpt.analysis.service.AnalysisJobService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.lang.Nullable;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/analysis")
public class AnalysisCallbackController {

    private final AnalysisJobService analysisJobService;
    private final String callbackSecret;
    private final boolean allowUnsignedCallbacks;

    public AnalysisCallbackController(
            AnalysisJobService analysisJobService,
            @Value("${gifpt.callback.secret:}") String callbackSecret,
            @Value("${gifpt.callback.allow-unsigned:false}") boolean allowUnsignedCallbacks
    ) {
        this.analysisJobService = analysisJobService;
        this.callbackSecret = callbackSecret;
        this.allowUnsignedCallbacks = allowUnsignedCallbacks;

        if (!allowUnsignedCallbacks && callbackSecret.isBlank()) {
            throw new IllegalStateException("gifpt.callback.secret must be configured when unsigned callbacks are not allowed");
        }
    }

    @PostMapping("/{jobId}/complete")
    public ResponseEntity<Void> complete(
            @PathVariable Long jobId,
            @RequestHeader(value = "X-Callback-Secret", required = false) @Nullable String secret,
            @RequestBody AnalysisCallbackDTO dto
    ) {
        if (!allowUnsignedCallbacks && !callbackSecret.equals(secret)) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
        }

        if (dto == null || dto.status() == null) {
            return ResponseEntity.badRequest().build();
        }

        analysisJobService.markCompleted(jobId, dto);

        return ResponseEntity.ok().build();
    }
}

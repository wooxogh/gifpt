// src/main/java/com/gifpt/analysis/controller/AnalysisCallbackController.java
package com.gifpt.analysis.controller;

import com.gifpt.analysis.dto.AnalysisCallbackDTO;
import com.gifpt.analysis.service.AnalysisJobService;
import com.gifpt.workspace.service.WorkspaceService;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/analysis")
public class AnalysisCallbackController {

    private final AnalysisJobService analysisJobService;
    private final WorkspaceService workspaceService;
    private final String callbackSecret;

    public AnalysisCallbackController(
            AnalysisJobService analysisJobService,
            WorkspaceService workspaceService,
            @Value("${gifpt.callback.secret:}") String callbackSecret
    ) {
        this.analysisJobService = analysisJobService;
        this.workspaceService = workspaceService;
        this.callbackSecret = callbackSecret;
    }

    @PostMapping("/{jobId}/complete")
    public ResponseEntity<Void> complete(
            @PathVariable Long jobId,
            @RequestHeader(value = "X-Callback-Secret", required = false) String secret,
            @RequestBody AnalysisCallbackDTO dto
    ) {
        // 시크릿이 설정된 경우에만 검증 (로컬 개발 시 미설정 허용)
        if (!callbackSecret.isBlank() && !callbackSecret.equals(secret)) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
        }

        analysisJobService.markCompleted(jobId, dto);

        workspaceService.onAnalysisCompleted(
                jobId,
                dto.status().name(),
                dto.summary(),
                dto.resultUrl()
        );

        return ResponseEntity.ok().build();
    }
}

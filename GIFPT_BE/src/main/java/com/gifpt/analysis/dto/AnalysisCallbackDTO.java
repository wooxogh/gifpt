package com.gifpt.analysis.dto;

import com.gifpt.analysis.domain.AnalysisStatus;
import org.springframework.lang.Nullable;

public record AnalysisCallbackDTO(
    AnalysisStatus status,
    @Nullable String resultUrl,
    @Nullable String summary,
    @Nullable String errorMessage
) {}

package com.gifpt.analysis.dto;

import java.time.Instant;
import org.springframework.lang.Nullable;

public record GalleryItemResponse(
        Long id,
        String algorithm,
        @Nullable String algorithmSlug,
        @Nullable String videoUrl,
        Instant createdAt
) {}

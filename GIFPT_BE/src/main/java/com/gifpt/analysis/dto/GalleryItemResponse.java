package com.gifpt.analysis.dto;

import java.time.Instant;

public record GalleryItemResponse(
        Long id,
        String algorithm,
        String algorithmSlug,
        String videoUrl,
        Instant createdAt
) {}

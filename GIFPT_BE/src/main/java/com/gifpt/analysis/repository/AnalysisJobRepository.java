package com.gifpt.analysis.repository;

import com.gifpt.analysis.domain.AnalysisJob;
import com.gifpt.analysis.domain.AnalysisStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Collection;
import java.util.Optional;

public interface AnalysisJobRepository extends JpaRepository<AnalysisJob, Long> {
    Optional<AnalysisJob> findByIdAndUserId(Long id, Long userId);

    Optional<AnalysisJob> findFirstByAlgorithmSlugAndStatusInOrderByIdDesc(String algorithmSlug, Collection<AnalysisStatus> statuses);

    // Gallery (public): successful jobs from name mode only (algorithmSlug is present)
    Page<AnalysisJob> findByStatusAndAlgorithmSlugIsNotNull(AnalysisStatus status, Pageable pageable);

    // Gallery: current user's successful animations (my gallery) — includes both name and describe modes
    Page<AnalysisJob> findByUserIdAndStatus(Long userId, AnalysisStatus status, Pageable pageable);
}

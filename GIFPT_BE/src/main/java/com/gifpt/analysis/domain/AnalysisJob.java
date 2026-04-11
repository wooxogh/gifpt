package com.gifpt.analysis.domain;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;

@Entity
@Getter @Setter
@NoArgsConstructor @AllArgsConstructor @Builder
@Table(name = "analysis_jobs")
public class AnalysisJob {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  private Long userId;

  @Enumerated(EnumType.STRING)
  private AnalysisStatus status;

  @Column(length = 128)
  private String algorithmSlug;  // normalized algorithm name for dedup (null for custom prompts)

  @Column(length = 4000)
  private String prompt;      // 사용자가 입력한 프롬프트

  @Column(length = 8000)
  private String summary;     // Django worker가 반환한 핵심 요약

  private String resultUrl;   // 생성된 영상 URL

  private String errorMessage; // 에러 메시지

  private Instant startedAt;   // 작업 시작 시간
  private Instant finishedAt;  // 작업 완료 시간
  private Instant createdAt;
  private Instant updatedAt;
}

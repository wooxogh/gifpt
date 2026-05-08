# GIFPT — Algorithm → Manim Animation, in 4 LLM stages

**알고리즘 이름 한 줄로 Manim 애니메이션을 생성하는 서비스.** 사용자가 알고리즘 이름(예: `bubble sort`, `cnn filter`)을 입력하면, 캐시 미스 시 LLM이 4-stage IR 파이프라인 (Pseudocode → Animation IR → Manim Code → Vision QA)을 거쳐 MP4로 응답합니다.

> 🥇 **제3회 연세 GenAI 활용 경진대회 금상** (2025-09 ~ 2025-12)
> 🧪 **회귀 추적**: `weekly_audit.py`가 신규 알고리즘 입력에 대해 4-stage 파이프라인 정확도를 주간 측정
> 🏗 **Refactored with [gstack](https://github.com/santifer/gstack)** — Spring Boot · Django Worker · Next.js 분리

[![대회](https://img.shields.io/badge/연세_GenAI_경진대회-금상-FFD700)]()
[![Stack](https://img.shields.io/badge/4--stage_LLM_pipeline-OpenAI_SDK-412991?logo=openai&logoColor=white)]()
[![Async](https://img.shields.io/badge/Celery_+_Redis-async_queue-DC382D?logo=redis&logoColor=white)]()

---

## 왜 4-stage IR인가 (핵심 결정)

LLM에 "알고리즘 X의 Manim 애니메이션 코드 짜줘"를 한 번에 던지는 zero-shot 접근은 **Manim API 호환성 + 알고리즘 정확성 + 시각화 품질**을 한 모델 호출에 전부 맡기는 구조입니다. 우리는 이를 4단계 IR로 분해했습니다:

| Stage | 역할 | 모델 | 컨텍스트 |
|-------|------|------|---------|
| 1. **도메인 분류** (`llm_domain.py`) | sorting / cnn_matrix / general 라우팅 — 전용 렌더러 우선 | gpt-4o | 알고리즘 이름 + prompt |
| 2. **Pseudocode IR** (`llm_pseudocode.py`) | 자연어 슬러그 → 구조적 의사 코드 (단계 정의) | gpt-4o | — |
| 3. **Animation IR** (`llm_anim_ir.py`) | Pseudocode → Manim 추상 객체·전이 (Scene-agnostic) | gpt-4o | Pseudocode IR |
| 4. **Manim Codegen** (`llm_codegen.py`) | IR → Manim Python 코드 | gpt-4o | Animation IR + `manim_api_ref.md` 주입 |
| 5. **Render + Vision QA** | MP4 렌더 → 결과 영상의 시각 정합성 검증 (최대 3회 재시도, fallback) | manim + Vision LLM | 영상 frame |

**왜 더 나은가:** 각 단계가 작은 책임만 지므로 (a) 실패 지점이 명확하고 (b) 단계별 정확도 측정이 가능하며 (c) 도메인별 전용 렌더러로 hot path를 우회할 수 있습니다 (`render_cnn_matrix.py`, `render_sorting.py`).

**Trade-off:** 한 task 당 OpenAI 호출이 4-14회로 많고, p99 latency가 분 단위. 비동기 큐 (Celery + Redis)로 사용자 응답을 200ms 이하로 고정하고 작업은 백그라운드에서 진행합니다.

---

## 회귀 추적 (`weekly_audit.py`)

LLM 파이프라인의 가장 큰 약점은 **silent regression** — 모델 업데이트나 프롬프트 수정으로 정확도가 조용히 떨어지는 것. 이를 잡기 위해 주간 audit:

- 신규/기존 알고리즘 입력 N개에 대해 4-stage 파이프라인 실행
- 단계별 출력 (Pseudocode IR / Animation IR / Manim Code) 와 최종 영상 Vision QA 결과를 함께 기록
- 이전 주 대비 성공률 / 단계별 실패 분포 차이 출력
- 회귀 발견 시 어느 stage에서 깨졌는지 즉시 식별

→ 이 패턴이 [career-ops](https://github.com/wooxogh/career-ops)의 Harness CI 피봇 ("LLM 파이프라인의 회귀 추적 도구화") 의 출발점.

---

## 시스템 아키텍처 요약

3-tier 모노레포로 분리, 각자 다른 SLO:

| 서비스 | SLO 목표 | 이유 |
|-------|---------|------|
| **Spring Boot** (`GIFPT_BE`) | p99 < 200ms | 사용자 응답 (캐시 조회 + JWT + enqueue) |
| **Django + Celery** (`GIFPT_AI`) | best-effort | LLM 호출 분 단위, 실패 재시도 가능 |
| **Next.js** (`gifpt-fe`) | TTI < 1s | Vercel edge |

**핵심 원칙:** 사용자 응답 path와 LLM 작업 path를 물리적으로 분리. Spring 장애가 LLM 워커에 영향 없음, 반대도 마찬가지. (자세한 컴포넌트 표는 아래 [시스템 아키텍처](#시스템-아키텍처) 섹션.)

---

## 이 프로젝트가 보여주는 것

1. **LLM 파이프라인 분해 사고** — 단일 zero-shot 호출의 한계를 인지하고 IR 단계별로 책임을 분리. 단계별 측정·롤백 가능한 구조.
2. **silent regression 추적 도구화** — `weekly_audit.py`로 회귀를 자동 감지. 동일 패턴이 career-ops Harness CI로 확장됨.
3. **사용자 응답 SLO 분리** — 분 단위 작업을 200ms 응답에 끼워넣지 않고 큐로 분리. Spring/Django/Next.js 각각 다른 SLO 명시.
4. **도메인 특화 hot path** — sorting / cnn_matrix는 전용 렌더러로 LLM 호출 우회. "LLM이 모든 걸 해야 한다"의 반대 방향.

---

## 모노레포 구조

```
gifpt/
├── gifpt-fe/         # Next.js 16 프런트엔드 (Vercel 배포)
├── GIFPT_BE/         # Spring Boot 3.5 백엔드 (Java 17)
├── GIFPT_AI/         # Django + Celery AI 워커 (Python)
├── nginx/            # Reverse proxy 설정
├── docker-compose.yml
├── DESIGN.md         # 디자인 시스템 스펙
└── CLAUDE.md         # Claude Code용 가이드
```

---

## 시스템 아키텍처

```
[Browser]
    │
    ▼
[Next.js (Vercel)] ── rewrites ──▶ [Nginx :80 (EC2)]
                                        │
                                        ▼
                                   [Spring Boot :8080]
                                   JWT 인증, /animate 캐시 조회, 갤러리
                                        │
                                        │ 캐시 MISS + 인증됨 → 작업 큐잉
                                        ▼
                                   [Django :8000] ──enqueue──▶ [Celery Worker]
                                                                    │
                                                                    ▼
                                                       LLM → Manim 렌더 → S3 업로드
                                                                    │
                    [Spring] ◀── POST /api/v1/analysis/{jobId}/complete
```

### 컴포넌트

| 서비스 | 역할 | 기술 |
|--------|------|------|
| **gifpt-fe** | UI, 인증, 애니메이션 요청/폴링 | Next.js 16, TypeScript, Tailwind v4, next-intl |
| **GIFPT_BE** | REST API, JWT 인증, `/animate` 캐시, 갤러리 | Java 17, Spring Boot 3.5, JPA, MySQL |
| **GIFPT_AI** | `/animate` 수신 → Celery 큐잉, 렌더링 파이프라인 | Python, Django, Celery, OpenAI, Manim |
| **Nginx** | Reverse Proxy, CORS | nginx:1.27-alpine |
| **Redis** | Celery 브로커 & 결과 백엔드 | Redis 7 |
| **MySQL** | Spring 영속 데이터 | MySQL (외부 호스트, `DB_HOST`) |
| **AWS S3** | 렌더링된 영상 저장 | 버킷 `gifpt-demo` (us-east-1) |

---

## Animate 플로우

1. FE가 `GET /api/v1/animate?algorithm=<slug>`을 Bearer 토큰과 함께 호출
2. Spring이 슬러그를 정규화(`normalizeSlug`)하고 SHA-256 해시로 S3 키(`animations/{hash}.mp4`) 계산
3. **캐시 HIT** → `200` + `videoUrl` 즉시 반환
4. **캐시 MISS + 비인증** → `401 login_required`
5. **캐시 MISS + 인증** → `202` + `jobId`, Django에 작업 디스패치
6. FE가 `GET /api/v1/animate/status/{jobId}`를 3초 간격으로 폴링 (최대 20회)
7. Worker가 렌더링 완료 후 Spring에 `POST /api/v1/analysis/{jobId}/complete` 콜백

> Spring의 `normalizeSlug()`와 Python 쪽 `normalize_slug()`는 **항상 동일한 S3 키**를 만들어야 하므로 한쪽만 변경하면 캐시가 깨집니다.

---

## AI 렌더링 파이프라인 (Celery Worker)

```
algorithm slug (+ optional prompt)
  │
  ▼
[1] 도메인 분류 (llm_domain.py)
     ├─ cnn_matrix → render_cnn_matrix.py  (전용 렌더러)
     ├─ sorting    → render_sorting.py     (전용 렌더러)
     └─ general    → LLM 생성 경로
  │
  ▼
[2] Pseudocode IR 생성 (llm_pseudocode.py, gpt-4o)
  │
  ▼
[3] Animation IR 생성  (llm_anim_ir.py,   gpt-4o)
  │
  ▼
[4] Manim 코드 생성    (llm_codegen.py,   gpt-4o)
     - manim_api_ref.md을 컨텍스트로 주입
  │
  ▼
[5] Manim 렌더링 → MP4 (최대 3회 재시도, fallback 포함)
  │
  ▼
[6] S3 업로드 → Spring 콜백
```

Celery 태스크 진입점: `studio.animate_algorithm(job_id, algorithm, prompt=None)` (`GIFPT_AI/studio/tasks.py`)

---

## API 엔드포인트

### Spring Boot (`/api/v1`)

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/auth/signup` | 회원가입 |
| `POST` | `/auth/login` | 로그인 (access token + HttpOnly refresh 쿠키) |
| `POST` | `/auth/logout` | 로그아웃 |
| `GET`  | `/auth/me` | 현재 사용자 조회 |
| `GET`  | `/animate?algorithm=<slug>` | 캐시 조회 → 200/202/401 |
| `POST` | `/animate` | 커스텀 프롬프트 기반 생성 요청 |
| `GET`  | `/animate/status/{jobId}` | 작업 상태 조회 |
| `GET`  | `/gallery` | 트렌딩 갤러리 |
| `GET`  | `/gallery/mine` | 내 갤러리 |
| `POST` | `/analysis/{jobId}/complete` | Worker → Spring 결과 콜백 (내부) |
| `GET`  | `/healthz` | 헬스체크 |

### Django (`/`)

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/animate` | 렌더 작업 큐잉 (Spring → Django 내부 호출) |
| `GET`  | `/tasks/{task_id}` | Celery 작업 상태 조회 |

---

## 실행 방법

### 사전 요구사항
- Docker, Docker Compose
- MySQL (외부 또는 호스트에 실행)
- OpenAI API Key
- AWS 자격증명 (S3 버킷 `gifpt-demo`, 리전 `us-east-1`)

### 환경변수

프로젝트 루트에 `.env` 파일 생성:

```env
# DB
DB_HOST=host.docker.internal
DB_USER=root
DB_PASSWORD=your_mysql_password

# Auth
GIFPT_JWT_SECRET=your_jwt_secret
GIFPT_CALLBACK_SECRET=shared_secret_for_worker_callback

# AWS
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# OpenAI
OPENAI_API_KEY=your_openai_api_key
```

### 전체 스택 실행

```bash
mkdir -p shared/uploads shared/results
docker-compose up -d
docker-compose logs -f worker
```

접속: `http://localhost` (Nginx → Spring) · Django 직접 `http://localhost:8000`

---

## 로컬 개발

### Frontend
```bash
cd gifpt-fe
npm install
echo "BACKEND_URL=http://localhost:80" > .env.local
npm run dev          # http://localhost:3000
npm test             # Vitest
npm run lint
```

### Backend
```bash
cd GIFPT_BE
./gradlew bootRun
./gradlew test
./gradlew build
```

### AI Worker
```bash
cd GIFPT_AI
python manage.py runserver
celery -A GIFPT_AI worker -l info -Q gifpt.default
```

---

## 배포

- **Frontend**: Vercel 자동 배포 (push to `main`). `vercel.json`이 모노레포 빌드 설정.
- **Backend / AI**: AWS EC2에서 Docker Compose + Nginx. GitHub Actions로 `ehho/gifpt-spring`, `ehho/gifpt-django`, `ehho/gifpt-worker` 이미지 빌드/푸시.
- **Nginx CORS**: `https://gifpt-front.vercel.app`만 허용 (Vercel 서버사이드 rewrite는 CORS 우회).

---

## 콜백 응답 형식

Worker → Spring:
```json
POST /api/v1/analysis/{jobId}/complete
{
  "status": "SUCCESS",
  "resultUrl": "https://gifpt-demo.s3.amazonaws.com/animations/<hash>.mp4",
  "errorMessage": null
}
```

---

## 참고 문서
- `CLAUDE.md` — 서브프로젝트별 상세 아키텍처 가이드
- `DESIGN.md` — 프런트엔드 디자인 시스템 스펙
- `TODOS.md` — 진행 중인 작업 목록

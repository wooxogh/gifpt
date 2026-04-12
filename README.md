# GIFPT

**알고리즘 이름 한 줄로 Manim 애니메이션을 생성하는 서비스**

사용자가 보고 싶은 알고리즘(예: `bubble sort`, `cnn filter`)을 입력하면, 캐시에 없을 경우 LLM이 Pseudocode → Animation IR → Manim 코드를 생성하고 렌더링하여 MP4로 반환합니다.

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

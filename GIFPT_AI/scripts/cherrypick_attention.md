# Cherrypick — Transformer Attention 영상 5개

`scripts/cherrypick_run.py` + 이 문서 = 트랜스포머 어텐션 30초 영상 5개를 손으로
cherry-pick해서 만들기 위한 복붙용 워크플로. 사이드 프로젝트 모드 — viral 1번 +
면접 demo 30초가 목표.

각 영상은 최대 5번 iterate. 가장 잘 나온 1개가 winner. 5개 영상 × 5번 iterate =
약 25번의 LLM + render 사이클. 전체 3~5시간.

---

## 만들 영상 5개

| # | 슬롯 디렉터리 | 길이 | 영상 내용 |
|---|---|---|---|
| 1 | `01_self_attention` | 30s | 토큰 3개로 Q/K/V 행렬 곱셈 → softmax → 출력 |
| 2 | `02_multi_head` | 30s | 같은 입력이 head 4개로 갈라져 다른 패턴 학습 |
| 3 | `03_causal_mask` | 15s | GPT가 미래 토큰 못 보는 이유 (마스크가 켜지는 순간) |
| 4 | `04_heatmap` | 30s | 실제 문장의 attention weight 히트맵 |
| 5 | `05_full_pipeline` | 60s | 입력 → embedding → attention → softmax → 다음 토큰 샘플 (**viral 후보**) |

5번이 트윗에 들어갈 viral 후보. 1~4번은 면접 demo + 5번을 위한 워밍업.

---

## 1회만 하는 셋업

```bash
cd GIFPT_AI
export OPENAI_API_KEY=sk-...
mkdir -p cherrypick/attention
```

`cherrypick/`은 작업 노트라서 git에 올릴 필요 없음. 한 번 추가:

```bash
echo 'cherrypick/' >> .gitignore
```

헬퍼 스크립트는 `scripts/cherrypick_run.py`. production codegen이 쓰는 것과
**같은 `SYSTEM_PROMPT`와 `post_process_manim_code`를 그대로 씀**. 즉 여기서
cherry-pick한 결과는 production 동작과 동일함.

---

## 1개 영상 cherry-pick하는 법 (반복 단위)

이게 핵심 루프임. 5개 영상마다 똑같이 함.

### 0. 슬롯 root 만들기

영상 1번을 만든다고 치자.

```bash
SLOT_ROOT=cherrypick/attention/01_self_attention
mkdir -p "$SLOT_ROOT"
```

### 1. v01 시도

```bash
mkdir -p "$SLOT_ROOT/v01"
$EDITOR "$SLOT_ROOT/v01/prompt.txt"
```

아래 "스타터 프롬프트" 섹션에서 해당 영상의 v01 프롬프트를 복붙해서 저장.

```bash
python -m scripts.cherrypick_run "$SLOT_ROOT/v01"
```

성공하면 이런 출력이 뜸:

```
[cherrypick] OK (38.4s)
[cherrypick] VIDEO: /Users/.../cherrypick/attention/01_self_attention/v01/media/videos/.../480p15/video.mp4
[cherrypick] open with: open '/Users/.../v01/video.mp4'
```

마지막 줄 `open ...` 명령어 그대로 복붙해서 영상 봄.

### 2. 진단 — 영상 보면서 메모

영상이 도는 동안 깨진 거 1줄씩 적음. **구체적으로**.

좋은 메모:
- `Q 행렬 라벨이 우측 화면 밖으로 잘림`
- `attention 화살표가 토큰 텍스트랑 겹침`
- `8초만에 끝남, 너무 빠름`
- `K 행렬은 모양은 맞는데 값이 다 0임`

나쁜 메모: `별로임`, `구림`, `안 됨`

이 메모가 v02 프롬프트의 fix 입력임. 메모 없으면 다음 iteration이 다시 복권 됨.

`$SLOT_ROOT/v01/notes.md`에 적어둬. 1년 후에 봐도 의미 있는 학습 자산임.

### 3. v02 — fix 반영

```bash
mkdir -p "$SLOT_ROOT/v02"
cp "$SLOT_ROOT/v01/prompt.txt" "$SLOT_ROOT/v02/prompt.txt"
$EDITOR "$SLOT_ROOT/v02/prompt.txt"
```

v01 프롬프트에 메모한 문제마다 명시적 fix 라인 추가. 예시:

- "All matrices must stay within ±5 horizontal and ±3 vertical of screen center."
- "Add `self.wait(0.8)` between every major step. Total scene duration: 30 seconds."
- "Label every matrix; never let labels overlap matrix cells."
- "K matrix values must be non-zero floats (e.g. 0.4, -0.7, 1.2)."

```bash
python -m scripts.cherrypick_run "$SLOT_ROOT/v02"
open "$SLOT_ROOT/v02/video.mp4"
```

### 4. v03, v04, v05 — 반복

같은 패턴. 매번:
1. 새 v폴더 만들고
2. 직전 프롬프트 복사하고
3. 새 fix 추가하고
4. 돌리고
5. 메모하고

### 5. Manual fix 모드 (탈출구)

v04까지 갔는데 코드가 95% 맞고 5%만 stubborn하게 깨지면 — **프롬프트 그만 만지고
파이썬 직접 고침**.

```bash
mkdir -p "$SLOT_ROOT/v05"
cp "$SLOT_ROOT/v04/scene.py" "$SLOT_ROOT/v05/scene.py"
$EDITOR "$SLOT_ROOT/v05/scene.py"
# 깨진 줄 손으로 고침

python -m scripts.cherrypick_run "$SLOT_ROOT/v05" --no-llm
open "$SLOT_ROOT/v05/video.mp4"
```

`--no-llm`은 LLM 호출 건너뛰고 `scene.py` 그대로 렌더. cherry-pick 모드에서는
"AI가 생성한 거 + 손으로 3줄 수정"도 완벽히 valid한 demo임. 트윗에 솔직히
"AI generated, manually polished"라고 써도 viral 됨.

### 6. 우승작 채택

5번 안에 마음에 드는 게 나오면 멈추고 우승작 채택:

```bash
mkdir -p cherrypick/attention/_winners
cp "$SLOT_ROOT/v05/video.mp4" cherrypick/attention/_winners/01_self_attention.mp4
```

다음 영상으로 넘어감.

---

## 멈출 시점

**1개 영상에서 멈출 조건 (셋 중 하나):**

1. **트윗에 올려도 되겠다 싶음.** 직감 믿어. 모르는 사람이 올린 거면 RT할 거 같으면 ship.
2. **5번 iteration 다 씀.** 그 중 best 골라서 우승작. 다음 영상으로.
3. **3번 iteration 동안 같은 버그 fix 안 됨.** Manual fix 모드로 전환 (`--no-llm` + 코드 직접 수정).

**전체 프로젝트 멈출 조건:**

`cherrypick/attention/_winners/`에 영상 5개 모임. 그게 deliverable.

---

## 스타터 프롬프트 5개

각각 해당 영상의 `v01/prompt.txt`에 그대로 복붙.

### 01_self_attention/v01/prompt.txt

```
Create a 30-second educational Manim scene that visualizes ONE layer of
self-attention on 3 input tokens: "the", "cat", "sat".

Show, in order:
1. Display the 3 token labels horizontally near the top of the screen.
2. Below each token, show its embedding as a small column vector (4 rows).
3. Compute Q, K, V by multiplying each embedding with weight matrices W_Q,
   W_K, W_V. Display Q, K, V as 3 small matrices labeled clearly.
4. Compute attention scores: Q @ K^T → 3x3 matrix. Show the matrix product
   visually (highlight the row and column being multiplied).
5. Apply softmax row-wise → highlight the resulting attention weights.
6. Multiply attention weights by V → final output vector for each token.

Layout rules (CRITICAL):
- All elements must stay within x=±6, y=±3 of screen center.
- Minimum 0.5 unit spacing between any two objects; no overlaps ever.
- Use a step_label in the top-left corner that updates each phase
  ("Step 1: Embeddings", "Step 2: Q/K/V", etc.)
- Color encoding: YELLOW_B = currently active, GREEN_B = completed,
  WHITE = inactive.

Pacing:
- Use self.wait(0.8) between every major step.
- Total scene duration: ~30 seconds.

Output ONLY Python code, no markdown.
```

### 02_multi_head/v01/prompt.txt

```
Create a 30-second educational Manim scene that visualizes multi-head
attention with 4 heads on the same input tokens "the cat sat on mat".

Show, in order:
1. Show the 5 input tokens horizontally near the top.
2. Show that the same input is split into 4 parallel "heads" — visualize as
   4 separate rows below the input, each labeled "Head 1" through "Head 4".
3. For each head, show a different attention pattern as a small 5x5 heatmap
   with different highlighted cells. Make each head visually distinct so
   the viewer immediately sees they learn different things:
   - Head 1: diagonal pattern (each token attends mostly to itself)
   - Head 2: previous-token pattern (each token attends to the one before it)
   - Head 3: subject-verb pattern (highlight "cat" → "sat")
   - Head 4: noun-noun pattern (highlight "cat" → "mat")
4. Show the 4 head outputs being concatenated into a single output vector.

Layout rules (CRITICAL):
- All elements within x=±6, y=±3 of screen center.
- Minimum 0.5 unit spacing; no overlaps.
- Use a step_label in the top-left.
- Color encoding: YELLOW_B = active head, GREEN_B = completed.

Pacing:
- self.wait(0.6) between major steps.
- Total scene duration: ~30 seconds.

Output ONLY Python code, no markdown.
```

### 03_causal_mask/v01/prompt.txt

```
Create a 15-second educational Manim scene that explains why GPT-style
language models cannot see future tokens, using a causal attention mask.

Show, in order:
1. Display 5 token labels horizontally: "the", "cat", "sat", "on", "mat".
2. Show a 5x5 attention score matrix below the tokens, with all cells filled
   with example float scores (e.g. 0.3, 0.7, ...).
3. Caption: "Without mask: token 'the' could see all future tokens."
4. Animate a triangular causal mask sliding in from the right: every cell
   above the diagonal becomes -infinity (visualize as a dark gray X or
   "-inf" label).
5. Caption changes to: "With causal mask: each token only sees itself
   and previous tokens."
6. Apply softmax → show that masked cells become 0, unmasked cells form
   a valid probability distribution per row.

Layout rules (CRITICAL):
- All elements within x=±6, y=±3 of screen center.
- 0.5 unit minimum spacing; no overlaps.
- Use a single bottom-aligned caption that updates twice during the scene.
- Color encoding: WHITE = visible, DARK_GRAY = masked, GREEN_B = final
  valid weight.

Pacing:
- Faster than other videos. Total duration: ~15 seconds.
- self.wait(0.5) between steps.

Output ONLY Python code, no markdown.
```

### 04_heatmap/v01/prompt.txt

```
Create a 30-second educational Manim scene showing a real attention weight
heatmap for the sentence "The cat sat on the mat" (6 tokens).

Show, in order:
1. Display the 6 tokens horizontally as the top row AND vertically as the
   left column of a 6x6 grid (so the grid is labeled like a confusion matrix).
2. Title at the top: "Attention weights — layer 4, head 2"
3. Animate the 6x6 grid filling in with attention weight values, using color
   intensity (BLUE_E = low, BLUE_A = medium, YELLOW = high) to show weight.
   Use realistic-looking values: most weights small, a few strong off-diagonal
   peaks.
4. Highlight one row at a time (e.g. row "sat") and show that the strongest
   attention is to "cat" (the subject), illustrating the model has learned
   subject-verb relationship.
5. Highlight a second row ("mat") and show its strongest attention is to "the"
   (the determiner before it).

Layout rules (CRITICAL):
- All elements within x=±6, y=±3 of screen center.
- 0.5 unit spacing minimum.
- Title stays at top throughout; updates highlight which row is being inspected.
- Use a step_label or caption to narrate ("Notice: 'sat' attends mostly to 'cat'")

Pacing:
- self.wait(0.8) between major steps.
- Total duration: ~30 seconds.

Output ONLY Python code, no markdown.
```

### 05_full_pipeline/v01/prompt.txt (viral 후보 — 가장 공들이기)

```
Create a 60-second educational Manim scene that shows the FULL pipeline of
how a transformer language model picks the next token, from input text to
sampled output. This is the "GPT in 60 seconds" video.

Use the example input: "The cat sat on the" — the model should output "mat".

Show, in order:
1. (5s) Input text "The cat sat on the" appears at the top. Each word becomes
   a token.
2. (10s) Each token is converted to an embedding (small column vector
   visualization). Caption: "Step 1 — Embeddings".
3. (15s) Embeddings flow into a "Transformer Block" (drawn as a labeled
   rectangle). Inside: show a simplified attention computation — Q/K/V
   matrices, attention weight matrix, weighted sum. Don't show every detail;
   show enough to indicate "attention is happening here".
   Caption: "Step 2 — Self-attention".
4. (10s) Output of attention block is shown as a refined embedding for the
   LAST token (the position where we predict the next word).
   Caption: "Step 3 — Last token's contextual embedding".
5. (10s) That embedding is multiplied by an output projection matrix to
   produce a logit vector over the vocabulary (show 6-8 candidate words with
   different bar heights: "mat", "floor", "chair", "table", "rug", "ground").
   Caption: "Step 4 — Logits over vocabulary".
6. (10s) Apply softmax → probabilities. Highlight that "mat" has the highest
   probability (e.g. 0.45). Animate a sampling action: arrow pointing to
   "mat". The token "mat" appears at the end of the input sentence.
   Caption: "Step 5 — Sampled token: 'mat'".
7. Final frame: full sentence "The cat sat on the mat" displayed clearly,
   with a small "GIFPT" watermark in the corner.

Layout rules (CRITICAL):
- All elements within x=±6.5, y=±3.5 of screen center.
- 0.5 unit minimum spacing; absolutely no overlapping objects or text.
- Use a single bottom-aligned caption that updates 5 times during the scene.
- Color scheme: WHITE = inactive, YELLOW_B = current step, GREEN_B = completed,
  BLUE_B for matrices, RED_B for the sampled token at the end.
- Step number indicator in the top-left ("1/5", "2/5", ...) that updates.

Pacing:
- self.wait(1.0) between major steps for emphasis.
- Total scene duration: ~60 seconds.

This is a VIRAL DEMO video. Visual polish matters more than technical accuracy
of every step. Make it look smooth and professional.

Output ONLY Python code, no markdown.
```

---

## 자주 깨지는 패턴 + 빠른 fix

| 증상 | 프롬프트에 추가할 fix |
|---|---|
| 객체가 화면 밖으로 나감 | `All elements must stay within x=±6, y=±3.` |
| 텍스트끼리 겹침 | `Place every label at least 0.5 units away from any other object.` |
| 너무 빨리 끝남 | `Add self.wait(0.8) between every major step. Total: 30 seconds.` |
| 잘못된 개념 그림 | 더 구체적으로 다시 적음. `Q is a 3x4 matrix computed as embeddings @ W_Q where W_Q is 4x4.` |
| Manim API 에러 | Deprecated API임. Manual fix 모드로 전환 (`--no-llm`), 코드에서 정확한 호출로 수정 |
| 정의 안 된 변수 참조 | LLM이 hallucinate. Manual fix로 해당 변수 정의 추가 후 `--no-llm` 렌더 |
| LaTeX 수식 깨짐 | `Use Text(...) instead of MathTex; avoid LaTeX entirely.` |
| 색상 에러 | `Use only these colors: YELLOW_B, GREEN_B, BLUE_B, RED_B, WHITE, DARK_GRAY.` |

---

## 학습 로그

매 iteration마다 `cherrypick/attention/learnings.md`에 한 줄씩 적음:

```
## 2026-04-09
- 01_self_attention v02: "0.5 unit spacing" 룰 추가하니 행렬 겹침 사라짐
- 01_self_attention v03: K 행렬 값 0 문제 — 명시적 예시 값 적으니 fix됨
- 01_self_attention v05 (manual): MathTex deprecated, Text으로 다 바꿈
- 02_multi_head v01: 잘 됨. fix 없이 통과
```

이게 너의 진짜 학습 자산임. 5개 영상 끝나면 이 파일이 시스템 프롬프트
개선의 input이 됨 (`SYSTEM_PROMPT`나 `post_process_manim_code`에 룰 추가).

---

## 최종 체크리스트

- [ ] 01_self_attention 우승작 → `_winners/01_self_attention.mp4`
- [ ] 02_multi_head 우승작 → `_winners/02_multi_head.mp4`
- [ ] 03_causal_mask 우승작 → `_winners/03_causal_mask.mp4`
- [ ] 04_heatmap 우승작 → `_winners/04_heatmap.mp4`
- [ ] 05_full_pipeline 우승작 → `_winners/05_full_pipeline.mp4`
- [ ] `learnings.md`에 5개 이상 메모
- [ ] 트윗 카피 초안 1개 작성 (5번 영상 기준, before/after 포맷)
- [ ] 면접용 30초 클립 1개 추출 (5번 영상에서 가장 임팩트 있는 30초)

8개 다 체크되면 사이드 프로젝트 1차 사이클 종료. 트윗 던지고 결과 봄.

---

## 시간 예산

- 1개 영상 × 평균 3 iteration × ~3분/iteration = ~10분/영상 (운 좋을 때)
- 1개 영상 × 5 iteration × ~5분 = ~25분/영상 (현실적)
- 5개 영상 × 25분 = ~2시간

거기에 영상 보고 메모하는 시간 + manual fix 시간 + 트윗 카피 작성 시간 합치면
**총 3~5시간**. 평일 저녁 한 번 + 주말 한 번이면 끝.

5시간 넘기면 scope 줄여라. 영상 5개가 아니라 3개로 줄여도 됨. 영상 5번이 아니라
3번 iteration으로 줄여도 됨. **완성이 완벽보다 우선임.**

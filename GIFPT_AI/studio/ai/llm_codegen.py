# ai/llm_codegen.py
import functools
import os, json, re
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

from studio.ai._tracing import traceable

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Valid Manim colors (from manim.utils.color)
VALID_MANIM_COLORS = [
    "WHITE", "BLACK", "GRAY", "GREY",
    "BLUE", "BLUE_A", "BLUE_B", "BLUE_C", "BLUE_D", "BLUE_E",
    "RED", "RED_A", "RED_B", "RED_C", "RED_D", "RED_E",
    "GREEN", "GREEN_A", "GREEN_B", "GREEN_C", "GREEN_D", "GREEN_E",
    "YELLOW", "YELLOW_A", "YELLOW_B", "YELLOW_C", "YELLOW_D", "YELLOW_E",
    "PURPLE", "PURPLE_A", "PURPLE_B", "PURPLE_C", "PURPLE_D", "PURPLE_E",
    "ORANGE", "PINK", "TEAL", "TEAL_A", "TEAL_B", "TEAL_C", "TEAL_D", "TEAL_E",
    "GOLD", "GOLD_A", "GOLD_B", "GOLD_C", "GOLD_D", "GOLD_E",
    "MAROON", "MAROON_A", "MAROON_B", "MAROON_C", "MAROON_D", "MAROON_E",
    "LIGHT_GRAY", "LIGHT_GREY", "DARK_GRAY", "DARK_GREY",
    "LIGHT_BROWN", "DARK_BROWN", "GRAY_BROWN",
    "LIGHT_PINK", "PURE_RED", "PURE_GREEN", "PURE_BLUE"
]

BASE_DIR = Path(__file__).resolve().parent

# Model constants — change here to upgrade across all codegen calls
MODEL_PRIMARY = "gpt-4o"         # Used for main codegen + QA feedback
MODEL_FAST = "gpt-4.1-mini"     # Used for fixes + few-shot algorithm codegen
MAX_QA_ISSUES = 20               # Cap QA issues injected into retry prompt

# Shared pedagogical rules — single source of truth for all prompts
PEDAGOGICAL_RULES_FULL = """
PEDAGOGICAL ANIMATION RULES (MOST IMPORTANT — these determine whether the video
actually explains the concept or just looks like random motion):

1. CAUSE BEFORE EFFECT: Always highlight/indicate the elements being compared or
   examined BEFORE animating the resulting action (swap, insert, remove).
   Pattern: Indicate(element) → annotation Text → transform animation → self.wait(0.5)
   The viewer must see WHY something happens before seeing it happen.

2. ONE OPERATION PER BEAT: Each self.play() call should animate exactly one logical
   operation. NEVER combine a comparison highlight and a swap in the same self.play().
   Bad:  self.play(Indicate(a), a.animate.move_to(b_pos))
   Good: self.play(Indicate(a), Indicate(b))  # compare
         self.play(a.animate.move_to(b_pos), b.animate.move_to(a_pos))  # swap

3. VISUAL STATE ENCODING: Maintain a consistent color scheme that encodes algorithm
   state throughout the entire animation. Elements change color to reflect state:
   - GRAY or WHITE (default): unprocessed / waiting
   - YELLOW_B: currently being examined / active
   - RED_B: being swapped / modified / rejected
   - GREEN_B: finalized / in correct position / accepted
   Once an element is marked GREEN (finalized), it should STAY green unless the
   algorithm logically revisits it. State colors are permanent markers, not decoration.

4. INVARIANT MARKERS: Visually show the algorithm's invariant or progress. Examples:
   - Sorting: a translucent bracket or background behind the sorted portion that grows
   - Graph: visited nodes stay highlighted, frontier is distinct from unvisited
   - DP: filled cells stay colored, empty cells remain gray
   - Cache: occupied slots vs empty slots clearly distinguishable
   Use a persistent visual element (SurroundingRectangle, Brace, or background color)
   that grows/moves as the algorithm progresses.

5. PROGRESSIVE PACING: First iteration of any loop should be slow with full annotations.
   Subsequent iterations accelerate with fewer annotations:
   - First pass: run_time=1.0-1.5, show comparison text, explain the decision
   - Middle passes: run_time=0.5-0.8, highlight only, skip redundant text
   - Final passes: run_time=0.3-0.5, fast to show the algorithm "clicking into place"

6. STEP LABEL: Maintain a persistent label in the top-left corner showing the current
   phase or iteration (e.g., "Pass 3 of 5", "Inserting key=7", "BFS: depth 2").
   Update this label at each major step. This anchors the viewer in the algorithm's flow.
   step_label = Text("Pass 1", font_size=20, color=GRAY).to_corner(UL)

7. PAUSE AFTER STATE CHANGES: Insert self.wait(0.5-1.0) after every significant state
   transition (swap, insertion, deletion, node visit). The viewer needs processing time.

8. CONCRETE DATA: Use specific small numbers (5-8 elements). Choose values that trigger
   interesting algorithm behavior:
   - Sorting: include duplicates, nearly-sorted subsequences — e.g., [38, 27, 43, 3, 9, 82, 10]
   - Graph: include cycles, varying degree — not just a simple chain
   - DP: values that show overlapping subproblems clearly

9. DIM THE IRRELEVANT: When the algorithm focuses on a sub-problem (partition in
   quicksort, subtree in DFS, window in sliding window):
   - Reduce opacity of elements outside the active range to 0.3
   - Restore full opacity when scope expands back
   element.animate.set_opacity(0.3)  # dim
   element.animate.set_opacity(1.0)  # restore

10. SHOW DATA STRUCTURE FIRST: Always create and display the full data structure
    (array, graph, tree, table) BEFORE starting the algorithm. The viewer needs spatial
    context before temporal action. Pattern:
    - FadeIn the structure with labels
    - self.wait(1) to let viewer absorb
    - Then begin algorithm steps
""".strip()

# Condensed version for few-shot and user prompts (same rules, less detail)
PEDAGOGICAL_RULES_CONDENSED = """
PEDAGOGICAL RULES (the animation must EXPLAIN the algorithm, not just show motion):
1. CAUSE BEFORE EFFECT: Highlight elements being compared BEFORE animating the
   resulting action. Pattern: Indicate → annotate → transform → pause.
2. ONE OPERATION PER BEAT: Each self.play() = one logical operation. Never combine
   a comparison and a swap in one call.
3. VISUAL STATE ENCODING: Color = algorithm state, not decoration.
   GRAY=unprocessed, YELLOW_B=examining, RED_B=swapping, GREEN_B=finalized.
   Finalized elements STAY their color.
4. INVARIANT MARKERS: Show algorithm progress visually (sorted portion grows,
   visited set expands, DP table fills). Use persistent visual elements.
5. PROGRESSIVE PACING: First loop pass slow (run_time=1.0-1.5) with annotations.
   Later passes faster (0.3-0.5) with less annotation.
6. STEP LABEL: Persistent label top-left showing current phase/iteration.
7. PAUSE AFTER STATE CHANGES: self.wait(0.5-1.0) after swaps, insertions, visits.
8. SHOW STRUCTURE FIRST: FadeIn the full data structure, wait(1), then begin.
9. DIM THE IRRELEVANT: set_opacity(0.3) on elements outside the active range.
10. CONCRETE DATA: 5-8 specific elements that trigger interesting behavior.
""".strip()

# 같은 폴더에 있는 render_cnn_matrix.py 를 참조
REFERENCE_PATH = BASE_DIR / "render_cnn_matrix.py"

with open(REFERENCE_PATH, "r", encoding="utf-8") as f:
    CNN_REFERENCE = f.read()

# Manim CE 0.19.0 API reference — injected verbatim into codegen prompts so
# the LLM sees exact signatures instead of hallucinating APIs. Required at
# import time: a missing or empty file would silently strip the API grounding
# from prompts, so we fail fast instead of falling back to an empty string.
MANIM_API_REF_PATH = BASE_DIR / "manim_api_ref.md"

with open(MANIM_API_REF_PATH, "r", encoding="utf-8") as f:
    MANIM_API_REFERENCE = f.read().strip()

if not MANIM_API_REFERENCE:
    raise RuntimeError(
        f"Manim API reference file is empty: {MANIM_API_REF_PATH}"
    )

SYSTEM_PROMPT = f"""
You are a Manim code generator.
You will receive a structured animation IR (entities, layout, actions)
and must produce a complete, executable Python script using Manim.

Below is a **reference example** of excellent Manim code style
(from render_cnn_matrix). Follow this level of structure, clarity, and animation pacing.

<reference_example>
{CNN_REFERENCE}
</reference_example>

SCENE GEOMETRY (CRITICAL — objects outside this zone will be clipped):
- Manim frame: horizontal [-7.1, 7.1], vertical [-4.0, 4.0]
- Safe composition zone: horizontal [-6.0, 6.0], vertical [-3.2, 3.2]
- Title zone: y = 3.2 to 3.8 (reserve top for titles)
- Always leave 0.5-unit margins from scene edges

LAYOUT RULES (CRITICAL — prevents overlapping and clipping):
- ALWAYS use VGroup + .arrange() or .arrange_in_grid() for multi-element layouts.
  NEVER manually position related items with hardcoded move_to() coordinates.
- For N items in a row: total_width = N * item_width + (N-1) * gap.
  If total_width > 12.0, SHRINK item size or use .scale_to_fit_width(12.0).
- Default spacing: buff=0.2 to 0.4 between objects.
- Use .next_to() for labels — never overlap a label with its parent object.
- After building a VGroup, check: if group.width > 12.0 or group.height > 6.0,
  call group.scale_to_fit_width(12.0) or group.scale_to_fit_height(6.0).
- For side-by-side sections (e.g., input matrix + kernel + output), wrap each in
  a VGroup, then arrange the top-level VGroup horizontally with buff=0.8.

SCALING FOR VARIABLE DATA:
- Array of 5 items: cell_size=0.8, font_size=24
- Array of 10 items: cell_size=0.55, font_size=18
- Array of 20+ items: cell_size=0.35, font_size=14, or show subset with "..."
- Matrix up to 5x5: cell_size=0.6, font_size=18
- Matrix 6x6+: cell_size=0.4, font_size=14
- Always compute: total_size = N * cell_size + (N-1) * buff. Scale down if > 12.0.

TEXT READABILITY:
- Title: font_size 32-40, color=YELLOW or WHITE
- Section labels: font_size 22-28
- Data inside cells: font_size 14-22 (scale with cell size)
- Annotations/notes: font_size 16-20
- MINIMUM readable font_size: 14 (anything smaller is invisible at 480p)
- For long text (>20 chars): use scale_to_fit_width() or abbreviate
- Use WHITE text on dark shapes (BLUE_D, PURPLE_D), colored text on BLACK background

COLOR RULES:
Allowed Manim color constants:
- Basic: WHITE, BLACK, GRAY, GREY
- Blue: BLUE, BLUE_A, BLUE_B, BLUE_C, BLUE_D, BLUE_E
- Red: RED, RED_A, RED_B, RED_C, RED_D, RED_E
- Green: GREEN, GREEN_A, GREEN_B, GREEN_C, GREEN_D, GREEN_E
- Yellow: YELLOW, YELLOW_A, YELLOW_B, YELLOW_C, YELLOW_D, YELLOW_E
- Purple: PURPLE, PURPLE_A, PURPLE_B, PURPLE_C, PURPLE_D, PURPLE_E
- Orange: ORANGE
- Pink: PINK, LIGHT_PINK
- Teal: TEAL, TEAL_A, TEAL_B, TEAL_C, TEAL_D, TEAL_E
- Gold: GOLD, GOLD_A, GOLD_B, GOLD_C, GOLD_D, GOLD_E
- Others: MAROON, LIGHT_GRAY, DARK_GRAY

FORBIDDEN COLORS: LIGHT_BLUE, DARK_BLUE, LIGHT_RED, DARK_RED, LIGHT_GREEN,
DARK_GREEN, CYAN, MAGENTA, VIOLET, INDIGO, BROWN
Use _A/_B/_C/_D/_E suffixes for variations (e.g., BLUE_B for lighter blue).

Semantic color assignments (use consistently throughout):
- Primary elements: BLUE_C
- Highlights/active: YELLOW_B
- Success/complete: GREEN_B
- Error/swap: RED_B
- Secondary: PURPLE_B or TEAL_B
- Neutral/borders: GRAY or WHITE

{PEDAGOGICAL_RULES_FULL}

ANIMATION PACING:
- Use LaggedStart with lag_ratio=0.15-0.3 for staggered reveals (looks professional)
- Use ReplacementTransform instead of Transform (avoids ghost mobjects)
- run_time: 0.2-0.4 for small transitions, 0.5-1.0 for major moves, 1.5-2.0 for complex transforms
- Add self.wait(0.3-0.5) between logical sections
- End with self.wait(2)

CODE RULES:
- Always include: `from manim import *`
- NEVER use hex color strings like "#abcdef"
- NEVER compare color objects or convert them to strings
- DO NOT invent custom helper functions not in Manim. Use only built-in mobjects
  and animations (FadeIn, FadeOut, Create, ReplacementTransform, Indicate, MoveToTarget,
  mobject.animate, LaggedStart, Circumscribe, Flash, etc.).
- Define class AlgorithmScene(Scene) with construct(self)
- Output ONLY valid Python code (no markdown, no prose, no trailing explanation text)

SAFE BOUNDS — all content must stay within these coordinates:
  x: [-6.5, 6.5], y: [-3.5, 3.5]
  If placing N elements horizontally, each element width ≤ 13.0 / N.
  If placing N elements vertically, each element height ≤ 7.0 / N.
  Always verify your layout arithmetic stays in bounds before coding.

MANIM CE 0.19.0 API REFERENCE (these are the EXACT signatures — do not
invent method names, kwargs, or classes not listed here):

<manim_api_reference>
{MANIM_API_REFERENCE}
</manim_api_reference>

MANIM CE 0.19.0 API CONSTRAINTS (violating these causes render failures):
- NO LaTeX: Never use Matrix, IntegerTable, MathTex, or Tex. Use only Text() for
  all text and numbers. Build grids/vectors manually with VGroup + Rectangle + Text.
- .deepcopy() does not exist. Use .copy() instead.
- .set_text() does not exist on Text objects. Create a new Text and use
  Transform(old_text, new_text) to update displayed text.
- Line and Arrow start/end must be coordinate arrays, NOT Mobject objects.
  CORRECT: Line(start=rect.get_center(), end=other.get_center())
  WRONG:   Line(start=rect, end=other)
- SurroundingRectangle expects Mobject(s). When selecting a subset of a VGroup,
  wrap in VGroup first: SurroundingRectangle(VGroup(*items), color=YELLOW)
- self.play() must receive at least 1 animation. Before unpacking a list,
  guard it: if anims: self.play(*anims)
- Every self.play() must have run_time > 0. If computing run_time dynamically,
  use max(computed, 0.1).
- Do NOT use DashedLine, DashedArrow, CurvedArrow, ArcBetweenPoints, or TracedPath.
  Use Line or Arrow instead.
- Do NOT access self.camera.frame. The default Scene camera does not have a frame
  attribute. Never use self.camera.frame.animate or self.camera.frame.set().
- Do NOT create a text-only summary phase at the end (e.g., 3 lines of Text on a
  blank screen). It adds no visual value. End the animation after the last
  substantive phase.

MATRIX/GRID HELPER PATTERN (use this when building grids of numbers):
Define as a method on the scene class:

    def make_grid(self, rows_data, cell_w=1.0, cell_h=0.6, color=WHITE, font_size=22):
        rows = VGroup()
        for r, row in enumerate(rows_data):
            row_group = VGroup()
            for c, val in enumerate(row):
                rect = Rectangle(width=cell_w, height=cell_h, stroke_color=color, stroke_width=1)
                txt = Text(str(val), font_size=font_size, color=color)
                cell = VGroup(rect, txt)
                cell.move_to([c * cell_w, -r * cell_h, 0])
                row_group.add(cell)
            rows.add(row_group)
        return rows

Access: grid[row][col] -> VGroup(rect, txt). grid[row][col][0] = Rectangle,
grid[row][col][1] = Text. Highlight a row: SurroundingRectangle(grid[1], color=YELLOW).
Always call make_grid THEN move_to THEN place labels relative to the grid.

ROW/COLUMN LABEL ALIGNMENT (labels must line up with their row or column):
- Row label for row i: label.move_to(grid[i].get_center()).align_to(grid, LEFT).shift(LEFT * 0.8)
- Column label for col j: label.move_to(grid[0][j].get_center()).align_to(grid, UP).shift(UP * 0.6)
  Do NOT place all labels as a single VGroup arranged independently — each label
  must be anchored to the y-center of its row or x-center of its column.

VERTICAL SPACING FOR MULTIPLE MATRICES:
- When stacking 3+ matrices vertically (e.g., Q/K/V), use at least 2.0 units
  between each center y-position. With cell_h=0.5 and 3 rows, each grid is ~1.5
  tall, so y spacing of 1.8 causes overlap. Use y offsets like 2.2, 0.0, -2.2.

3D DEPTH STYLE (for stacked layers like multi-head or encoder layers):
Use this ONLY when showing "same structure repeated in layers" (e.g., multiple
attention heads, encoder/decoder layer stacks). Do NOT use for Q/K/V side-by-side.

How it works:
1. Build each layer as a normal make_grid.
2. Apply skew to each grid: grid.apply_matrix([[1, 0.15], [0, 1]])
3. Stack layers with slight diagonal offset (RIGHT * 0.3 + UP * 0.3 per layer).
4. Add layers back-to-front so the frontmost layer renders on top.
5. Labels go OUTSIDE the grid, positioned AFTER skew and shift:
     label.next_to(grid, RIGHT, buff=0.3)
6. To move a layer, group grid + label into a VGroup and move the group.
7. Do NOT add Polygon side/top faces. Depth comes only from skew + overlap.

PHASE TRANSITION RULES:
- Do NOT impose a total time limit on the animation. Let each phase take as long
  as it needs. The prompt specifies Wait times per phase — follow those, but do not
  compress or rush content to fit a target duration.
- Between phases, clear the ENTIRE screen with this exact pattern:
    self.play(*[FadeOut(mob) for mob in self.mobjects])
  This removes ALL elements. Then re-add title and caption fresh for the new phase.
  Do NOT try to FadeOut individual elements — you WILL forget some.
- Caption is a single Text(font_size=20) at y=-2.8, updated via Transform(caption, new_cap).
  new_cap must use font_size=20 and .move_to(DOWN*2.8) before Transform.
- Title label at top-left corner (UL). Re-create it each phase after clearing.
- When using Transform on Text inside grid cells, use ReplacementTransform
  instead of Transform to avoid ghost text artifacts.
"""

# Experiment A (Week 3) — FULL vs CONDENSED pedagogical rules.
# The FULL prompt is SYSTEM_PROMPT above; the CONDENSED variant is derived
# on demand inside `_get_condensed_system_prompt()` via a string replace on
# the pedagogical rules block. Both variants are byte-identical except for
# that block, so any delta LangSmith reports across runs isolates the effect
# of the prompt cut.
SYSTEM_PROMPT_FULL = SYSTEM_PROMPT


@functools.lru_cache(maxsize=1)
def _get_condensed_system_prompt() -> str:
    """Derive the CONDENSED system prompt lazily and cache the result.

    Moved out of module import so that an unrelated edit to
    PEDAGOGICAL_RULES_FULL formatting does not crash every caller of
    llm_codegen at import time. The substitution is still verified — but
    only when a condensed run is actually requested.
    """
    condensed = SYSTEM_PROMPT_FULL.replace(
        PEDAGOGICAL_RULES_FULL, PEDAGOGICAL_RULES_CONDENSED
    )
    if condensed == SYSTEM_PROMPT_FULL:
        raise RuntimeError(
            "SYSTEM_PROMPT_CONDENSED substitution failed — "
            "PEDAGOGICAL_RULES_FULL text no longer appears verbatim in "
            "SYSTEM_PROMPT_FULL. Update PEDAGOGICAL_RULES_FULL to match the "
            "block embedded in SYSTEM_PROMPT, or regenerate both together."
        )
    return condensed


def _get_system_prompt() -> str:
    """Return FULL or CONDENSED system prompt based on GIFPT_PROMPT_VARIANT.

    Read at call time (not import time) so experiment runners can flip
    the env var between LangSmith runs without reloading the module.
    The CONDENSED variant is constructed lazily on first condensed call.
    """
    variant = (os.getenv("GIFPT_PROMPT_VARIANT") or "full").strip().lower()
    if variant == "condensed":
        return _get_condensed_system_prompt()
    return SYSTEM_PROMPT_FULL


def build_prompt_codegen(anim_ir: dict) -> str:
    return f"""
You are a Manim expert. Convert the following structured animation IR into a **complete** Manim Scene.

IR:
{json.dumps(anim_ir, indent=2, ensure_ascii=False)}

CRITICAL Requirements:
0. Shapes: The examples below cover common shapes (matrix, array, rectangle, circle) but you are NOT limited to these. If the IR contains an unrecognized shape, choose the closest Manim primitive (Rectangle, Circle, Line, Arrow, Dot, Polygon) and render it with available label/data/dimensions.
0b. DO NOT call or reference undefined helper functions (e.g., AddPointToGraph, PlotPoint, CreateGraph). Only use Manim core classes and animations. For points on axes, create a Dot and position it via Axes.coords_to_point(x, y).
1. **Render shapes according to their type:**
   
   A) For "matrix" shape with "data" field:
   ```python
   values = [[1,2,3], [4,5,6], [7,8,9]]  # from IR data field
   cells = []
   for r in range(len(values)):
       for c in range(len(values[0])):
           sq = Square(side_length=0.5, color=BLUE_B, fill_opacity=0.3)
           txt = Text(str(values[r][c]), font_size=20, color=WHITE)
           cells.append(VGroup(sq, txt))
   matrix = VGroup(*cells).arrange_in_grid(rows=len(values), cols=len(values[0]), buff=0.05)
   label = Text("Input", font_size=24, color=WHITE).next_to(matrix, UP)
   matrix_group = VGroup(matrix, label).move_to([x, y, 0])
   ```
   
   B) For "array" shape with "data" field:
   ```python
   values = [10, 20, 30, 40]  # from IR data field
   items = []
   for val in values:
       sq = Square(side_length=0.6, color=RED_B, fill_opacity=0.3)
       txt = Text(str(val), font_size=20, color=WHITE)
       items.append(VGroup(sq, txt))
   array = VGroup(*items).arrange(RIGHT, buff=0.1)
   label = Text("Array", font_size=24, color=WHITE).next_to(array, UP)
   array_group = VGroup(array, label).move_to([x, y, 0])
   ```
   
   C) For "rectangle" or "circle" with "label" field only:
   ```python
   rect = Rectangle(width=2.0, height=1.0, color=YELLOW, fill_opacity=0.3)
   label = Text("Q", font_size=24, color=WHITE)
   obj = VGroup(rect, label).move_to([x, y, 0])
   ```
   
   D) For shapes without "label" (decorative):
   ```python
   circle = Circle(radius=0.5, color=ORANGE).move_to([x, y, 0])
   ```

2. **Use "dimensions" field if present** (e.g., "3×3", "(seq_len, d_model)"):
   - Add as small text annotation below or next to the object

3. **Must visualize every operation sequentially** — no skipping.

4. **Pedagogical structure** (the animation must TEACH, not just move objects):
   a) Show the full data structure first (FadeIn all elements), then self.wait(1).
   b) Add a step_label = Text("Step 1: ...", font_size=20, color=GRAY).to_corner(UL)
      that updates at each major phase of the algorithm.
   c) For each operation: FIRST highlight/Indicate the elements being examined (cause),
      THEN animate the resulting action (effect), THEN self.wait(0.5).
   d) Use color to encode state: YELLOW_B for "currently examining", RED_B for "swapping
      or modifying", GREEN_B for "finalized / in correct position". Once GREEN, stay GREEN.
   e) Show the algorithm's invariant: if a region grows (sorted portion, visited set),
      keep it visually distinct (colored background, bracket, or persistent highlight).
   f) First iteration of a loop: slow (run_time=1.0+), with annotation text explaining
      the decision. Later iterations: faster (run_time=0.3-0.5), minimal annotation.
   g) When focused on a sub-problem, dim elements outside the active range (set_opacity=0.3).

5. End with a completion state: all elements in final state (e.g., all GREEN for sorted),
   a brief "Done!" or summary label, then self.wait(2).

Output:
- Write **only Python code** that defines `class AlgorithmScene(Scene)`.
- Do not include markdown (no ```python or ```).
- Code must be directly executable by `manim`.
"""

_INVALID_COLOR_MAP = {
    'LIGHT_BLUE': 'BLUE_B',
    'DARK_BLUE': 'BLUE_D',
    'LIGHT_RED': 'RED_B',
    'DARK_RED': 'RED_D',
    'LIGHT_GREEN': 'GREEN_B',
    'DARK_GREEN': 'GREEN_D',
    'LIGHT_YELLOW': 'YELLOW_B',
    'DARK_YELLOW': 'YELLOW_D',
    'CYAN': 'TEAL',
    'MAGENTA': 'PINK',
    'VIOLET': 'PURPLE',
    'INDIGO': 'PURPLE_D',
    'BROWN': 'MAROON',
    'LIME': 'GREEN_B',
    'NAVY': 'BLUE_D',
}

_UNKNOWN_HELPERS = [
    'AddPointToGraph', 'PlotPoint', 'CreateGraph', 'AnimateCurvePoint',
    'DrawArrowBetween', 'ShowValueOnPlot',
    # LLM-hallucinated animation/class names
    'Highlight', 'Focus', 'Emphasize',
    'MobjectTable', 'IntegerTable',
]


def post_process_manim_code(code: str) -> str:
    """Clean up LLM-generated Manim code.

    - Strips markdown fences and trailing prose
    - Replaces invalid color names with valid Manim equivalents
    - Removes hex color strings
    - Forces class name to AlgorithmScene
    - Removes unknown helper calls
    - Fixes common Manim CE 0.19.0 API mistakes (.deepcopy, DashedLine, etc.)
    """
    code = code.replace("```python", "").replace("```", "").strip()

    # Remove trailing non-code text after the class definition
    # Find the last line that's part of the Python code (indented or empty)
    lines = code.split('\n')
    last_code_line = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        raw_line = lines[i]
        stripped = raw_line.strip()
        # Indented lines or empty lines are part of the code body
        if stripped == '' or raw_line[0:1] in (' ', '\t'):
            last_code_line = i + 1
            break
        # Top-level Python constructs are valid code
        if stripped.startswith(('#', 'from ', 'import ', 'class ', 'def ', '@')):
            last_code_line = i + 1
            break
        # If we hit a line that looks like prose (top-level, not a Python keyword), trim from here
        _CODE_KEYWORDS = ('if ', 'for ', 'while ', 'return ', 'self.', 'try:', 'except ', 'else:', 'elif ', 'with ', 'raise ', 'yield ', 'pass', 'break', 'continue')
        if not any(stripped.startswith(kw) for kw in _CODE_KEYWORDS):
            last_code_line = i
            break
    code = '\n'.join(lines[:last_code_line]).rstrip()

    for invalid, valid in _INVALID_COLOR_MAP.items():
        code = re.sub(rf'\bcolor\s*=\s*{invalid}\b', f'color={valid}', code)
        code = re.sub(rf'\b{invalid}\b(?=\s*[,\)])', valid, code)

    code = re.sub(r'color\s*=\s*["\']#[0-9A-Fa-f]{6}["\']', 'color=BLUE', code)
    # Normalize scene class name — preserve ThreeDScene base class
    if re.search(r'class\s+\w+\s*\(ThreeDScene\)', code):
        code = re.sub(r'class\s+\w+\s*\(ThreeDScene\)', 'class AlgorithmScene(ThreeDScene)', code)
    else:
        code = re.sub(r'class\s+\w+\s*\(Scene\)', 'class AlgorithmScene(Scene)', code)

    for name in _UNKNOWN_HELPERS:
        code = re.sub(
            rf'^(\s*)self\.play\(\s*{name}\([^)]*\)\s*\)\s*$',
            r'\1self.wait(0.1)',
            code,
            flags=re.M,
        )
        code = re.sub(
            rf'^(\s*){name}\([^)]*\)\s*$',
            r'\1self.wait(0.1)',
            code,
            flags=re.M,
        )

    # Fix .deepcopy() → .copy()
    code = code.replace('.deepcopy()', '.copy()')

    # Fix DashedLine → Line, DashedArrow → Arrow
    code = re.sub(r'\bDashedLine\b', 'Line', code)
    code = re.sub(r'\bDashedArrow\b', 'Arrow', code)
    code = re.sub(r'\bCurvedArrow\b', 'Arrow', code)

    # Remove dash_length kwarg (not supported in Manim CE)
    code = re.sub(r',\s*dash_length\s*=\s*[^,\)]+', '', code)

    return code


def _build_few_shot_system_prompt(examples: list[dict]) -> str:
    """Build a SYSTEM_PROMPT that injects few-shot Manim examples."""
    examples_text = ""
    for i, ex in enumerate(examples, 1):
        examples_text += (
            f"\n<example_{i} tag=\"{ex.get('tag', '')}\" "
            f"pattern=\"{ex.get('pattern_type', '')}\" "
            f"quality=\"{ex.get('quality_score', '')}\">\n"
            f"{(ex.get('code') or '').strip()}\n"
            f"</example_{i}>\n"
        )

    return f"""
You are a Manim code generator. Generate complete, executable Manim Python code
for the requested algorithm.

Below are reference examples of high-quality Manim code. Follow their visual style,
animation pacing, and structural patterns closely.

<reference_examples>
{examples_text}
</reference_examples>

SCENE GEOMETRY (objects outside this zone will be clipped):
- Safe composition zone: horizontal [-6.0, 6.0], vertical [-3.2, 3.2]
- Title zone: y = 3.2 to 3.8 (reserve for title)
- Leave 0.5-unit margins from edges

LAYOUT RULES:
- ALWAYS use VGroup + .arrange() or .arrange_in_grid() for multi-element layouts.
- For N items in a row: if total_width > 12.0, scale down with .scale_to_fit_width(12.0).
- Use .next_to() for labels — never overlap a label with its parent object.
- For side-by-side sections, wrap each in VGroup, arrange with buff=0.8.
- Array of 5 items: cell_size=0.8. Array of 10+: cell_size=0.55. Array of 20+: cell_size=0.35.

TEXT READABILITY:
- Title: 32-40pt. Labels: 22-28pt. Data in cells: 14-22pt.
- Minimum readable: 14pt (smaller is invisible at 480p)
- WHITE text on dark shapes, colored text on BLACK background

COLOR RULES:
Allowed: WHITE, BLACK, GRAY/GREY, BLUE(_A-E), RED(_A-E), GREEN(_A-E), YELLOW(_A-E),
PURPLE(_A-E), ORANGE, PINK, TEAL(_A-E), GOLD(_A-E), MAROON, LIGHT_GRAY, DARK_GRAY
FORBIDDEN: LIGHT_BLUE, DARK_BLUE, CYAN, MAGENTA, VIOLET, INDIGO, BROWN

{PEDAGOGICAL_RULES_CONDENSED}

ANIMATION PACING:
- Use LaggedStart(lag_ratio=0.15-0.3) for staggered reveals
- Use ReplacementTransform instead of Transform
- run_time: 0.2-0.4 small, 0.5-1.0 major, 1.5-2.0 complex
- self.wait(0.3-0.5) between sections, self.wait(2) at end

CODE RULES:
- Always: `from manim import *`
- NEVER use hex colors like "#abcdef"
- DO NOT invent custom helper functions not in Manim
- Class: AlgorithmScene(Scene) with construct(self)
- Output ONLY valid Python code (no markdown, no trailing prose)

MANIM CE 0.19.0 API REFERENCE (exact signatures — do not invent methods):

<manim_api_reference>
{MANIM_API_REFERENCE}
</manim_api_reference>

MANIM CE 0.19.0 API CONSTRAINTS:
- NO LaTeX: Never use Matrix, IntegerTable, MathTex, or Tex. Use Text() only.
  Build grids manually with VGroup + Rectangle + Text.
- .deepcopy() → use .copy(). .set_text() → create new Text + Transform.
- Line/Arrow start/end must be coordinates, NOT Mobjects.
- SurroundingRectangle expects Mobject(s), wrap subsets in VGroup.
- self.play() must have at least 1 animation and run_time > 0.
- No DashedLine, DashedArrow, CurvedArrow. Use Line or Arrow.
- FadeOut previous phase elements before showing new ones.
"""


def call_llm_codegen_with_qa_feedback(anim_ir: dict, qa_issues: list[str]) -> str:
    """Regenerate Manim code with Vision QA feedback injected.

    Instead of blindly retrying codegen, this feeds the specific quality issues
    (overlapping elements, unreadable text, missing steps, etc.) into the prompt
    so the LLM can address them directly.
    """
    max_qa_issues = MAX_QA_ISSUES
    if qa_issues is None:
        normalized_issues = []
    elif isinstance(qa_issues, str):
        normalized = qa_issues.strip()
        normalized_issues = [normalized] if normalized else []
    else:
        try:
            normalized_issues = [
                str(issue).strip()
                for issue in qa_issues
                if str(issue).strip()
            ]
        except TypeError:
            issue_text = str(qa_issues).strip()
            normalized_issues = [issue_text] if issue_text else []

    normalized_issues = normalized_issues[:max_qa_issues]
    issues_text = "\n".join(f"- {issue}" for issue in normalized_issues)
    if not normalized_issues:
        # No actual issues — fall back to standard codegen
        return call_llm_codegen(anim_ir)
    prompt = build_prompt_codegen(anim_ir)
    prompt += (
        f"\n\nIMPORTANT — The previous rendering had these quality issues detected by Vision QA:\n"
        f"{issues_text}\n\n"
        f"You MUST fix ALL of these issues. Apply these specific remedies:\n\n"
        f"OVERLAP FIXES:\n"
        f"- Wrap all related items in VGroup and use .arrange(RIGHT/DOWN, buff=0.4)\n"
        f"- For side-by-side sections, increase buff to 0.8-1.2\n"
        f"- After grouping, add: if group.width > 12: group.scale_to_fit_width(12)\n"
        f"- Move labels with .next_to(obj, UP/DOWN, buff=0.3) — never stack on top\n\n"
        f"TEXT READABILITY FIXES:\n"
        f"- Data in cells: minimum font_size=14, increase to 18-22 if cells are large\n"
        f"- Labels: minimum font_size=20\n"
        f"- Use WHITE text on colored shapes, ensure contrast\n"
        f"- Long text: call .scale_to_fit_width(max_width) after creation\n\n"
        f"BOUNDARY FIXES:\n"
        f"- All objects must stay within x=[-6.0, 6.0], y=[-3.2, 3.2]\n"
        f"- Title at y=3.5, main content centered around y=0\n"
        f"- After building full scene, verify no group exceeds safe zone\n\n"
        f"ANIMATION FIXES:\n"
        f"- If static: add LaggedStart animations, Indicate() for highlights\n"
        f"- If steps missing: animate EVERY action in the IR sequentially\n"
        f"- Use self.wait(0.3) between sections for visual clarity\n\n"
        f"Output ONLY the corrected Python code."
    )
    resp = client.chat.completions.create(
        model=MODEL_PRIMARY,
        messages=[
            {"role": "system", "content": _get_system_prompt()},
            {"role": "user", "content": prompt},
        ],
        timeout=90,
    )
    return post_process_manim_code(resp.choices[0].message.content)


def _build_intent_context(
    algorithm_name: str | None = None,
    anim_ir: dict | None = None,
) -> str:
    """Build a concise description of the original animation intent."""
    parts: list[str] = []
    if algorithm_name:
        parts.append(f"Algorithm: {algorithm_name}")
    if anim_ir and isinstance(anim_ir, dict):
        meta = anim_ir.get("metadata", {})
        if isinstance(meta, dict):
            title = meta.get("title") or meta.get("domain", "")
            if title:
                parts.append(f"Topic: {title}")
        layout = anim_ir.get("layout", [])
        actions = anim_ir.get("actions", [])
        if isinstance(layout, list) and layout:
            shapes = [item.get("shape", "?") for item in layout[:6] if isinstance(item, dict)]
            layout_line = f"Layout: {len(layout)} elements"
            if shapes:
                layout_line += f" ({', '.join(shapes)})"
            parts.append(layout_line)
        if isinstance(actions, list) and actions:
            anims = [act.get("animation", "?") for act in actions[:6] if isinstance(act, dict)]
            actions_line = f"Actions: {len(actions)} steps"
            if anims:
                actions_line += f" ({', '.join(anims)})"
            parts.append(actions_line)
    return "\n".join(parts)


def _build_attempt_history_context(attempt_history: list[dict] | None) -> str:
    """Build a summary of previous failed attempts to avoid repeating mistakes."""
    if not attempt_history:
        return ""
    lines = ["Previous failed attempts (do NOT repeat these mistakes):"]
    for entry in attempt_history[-3:]:  # cap at last 3 to avoid prompt bloat
        attempt_num = entry.get("attempt", "?")
        err_type = entry.get("error_type", "unknown")
        stderr = entry.get("stderr", "")
        # Truncate stderr to key line
        err_lines = [l for l in stderr.split("\n") if "Error" in l]
        err_summary = err_lines[-1][:200] if err_lines else stderr[:200]
        lines.append(f"  Attempt {attempt_num}: {err_type} — {err_summary}")
    return "\n".join(lines)


def call_llm_codegen_fix(
    original_code: str,
    error_type: str,
    stderr_snippet: str,
    *,
    algorithm_name: str | None = None,
    anim_ir: dict | None = None,
    attempt_history: list[dict] | None = None,
) -> str:
    """Ask LLM to fix Manim code based on a render error.

    Used by the self-healing codegen loop: when run_manim_code raises
    ManimRenderError, we send the broken code + error back to the LLM.

    Enhanced context parameters help the LLM preserve the original animation
    intent and avoid repeating previous mistakes:
        algorithm_name: The algorithm being visualized (e.g. "bubble sort")
        anim_ir: The Animation IR that drove codegen (layout + actions)
        attempt_history: List of previous attempt dicts with error_type/stderr
    """
    intent_ctx = _build_intent_context(algorithm_name, anim_ir)
    history_ctx = _build_attempt_history_context(attempt_history)

    fix_prompt_parts = []

    if intent_ctx:
        fix_prompt_parts.append(
            f"ORIGINAL INTENT (preserve this while fixing):\n{intent_ctx}\n"
        )

    fix_prompt_parts.append(
        f"The following Manim code failed to render.\n\n"
        f"Error type: {error_type}\n"
        f"Error output (last 1500 chars):\n```\n{stderr_snippet[-1500:]}\n```\n"
    )

    if history_ctx:
        fix_prompt_parts.append(f"\n{history_ctx}\n")

    fix_prompt_parts.append(
        f"Original code:\n```python\n{original_code}\n```\n\n"
        f"Fix the code so it renders successfully. "
        f"Keep the same visual intent — the animation must still teach the concept described above. "
        f"Output ONLY the corrected Python code, no markdown."
    )

    fix_prompt = "\n".join(fix_prompt_parts)

    resp = client.chat.completions.create(
        model=MODEL_FAST,
        messages=[
            {"role": "system", "content": _get_system_prompt()},
            {"role": "user", "content": fix_prompt},
        ],
        timeout=60,
    )
    return post_process_manim_code(resp.choices[0].message.content)


def call_llm_codegen_for_algorithm(algorithm: str, examples: list[dict]) -> str:
    """Generate Manim code for a named algorithm using few-shot examples.

    Used by the animate_algorithm Celery task (direct endpoint path).
    Not used by the PDF pipeline.
    """
    system_prompt = _build_few_shot_system_prompt(examples)
    user_prompt = (
        f"Generate a complete Manim scene that TEACHES the '{algorithm}' algorithm.\n\n"
        f"Structure your animation as an educational explanation:\n"
        f"1. Show the full data structure first (FadeIn + wait), with a title.\n"
        f"2. Add a step_label in the top-left corner that updates each phase.\n"
        f"3. For each operation: HIGHLIGHT the elements being examined first (cause),\n"
        f"   THEN animate the action (effect), THEN pause briefly.\n"
        f"4. Use color to encode state: YELLOW_B=examining, RED_B=swapping, GREEN_B=finalized.\n"
        f"5. Show the algorithm's invariant growing (sorted region, visited set, etc.).\n"
        f"6. First loop iteration slow with annotations, later iterations faster.\n"
        f"7. End with all elements in final state + completion label.\n\n"
        f"Use 5-8 concrete data elements. Follow the reference examples above.\n"
        f"Output ONLY Python code, no markdown."
    )
    resp = client.chat.completions.create(
        model=MODEL_FAST,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        timeout=60,
    )
    code = resp.choices[0].message.content
    return post_process_manim_code(code)


def call_llm_codegen(anim_ir: dict):
    prompt = build_prompt_codegen(anim_ir)
    resp = client.chat.completions.create(
        model=MODEL_PRIMARY,
        messages=[
            {"role": "system", "content": _get_system_prompt()},
            {"role": "user", "content": prompt},
        ],
    )
    code = resp.choices[0].message.content
    return post_process_manim_code(code)


@traceable(name="codegen", run_type="chain")
def call_llm_codegen_with_usage(anim_ir: dict):
    prompt = build_prompt_codegen(anim_ir)
    resp = client.chat.completions.create(
        model=MODEL_PRIMARY,
        messages=[
            {"role": "system", "content": _get_system_prompt()},
            {"role": "user", "content": prompt},
        ],
    )
    code = post_process_manim_code(resp.choices[0].message.content)

    usage = getattr(resp, "usage", None)
    if usage:
        usage_dict = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None) or (usage.get("prompt_tokens") if hasattr(usage, "get") else None),
            "completion_tokens": getattr(usage, "completion_tokens", None) or (usage.get("completion_tokens") if hasattr(usage, "get") else None),
            "total_tokens": getattr(usage, "total_tokens", None) or (usage.get("total_tokens") if hasattr(usage, "get") else None),
        }
    else:
        usage_dict = None

    return code, usage_dict

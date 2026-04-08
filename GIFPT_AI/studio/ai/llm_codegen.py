# ai/llm_codegen.py
import os, json, re
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

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

# 같은 폴더에 있는 render_cnn_matrix.py 를 참조
REFERENCE_PATH = BASE_DIR / "render_cnn_matrix.py"

with open(REFERENCE_PATH, "r", encoding="utf-8") as f:
    CNN_REFERENCE = f.read()

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
  mobject.animate, LaggedStart, etc.).
- Define class AlgorithmScene(Scene) with construct(self)
- Output ONLY valid Python code (no markdown, no prose)
"""

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

4. Add subtle pauses (`self.wait(0.3)`) between major steps.

5. End with fade-out of all objects.

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
]


def post_process_manim_code(code: str) -> str:
    """Clean up LLM-generated Manim code.

    - Strips markdown fences
    - Replaces invalid color names with valid Manim equivalents
    - Removes hex color strings
    - Forces class name to AlgorithmScene
    - Removes unknown helper calls (replaces with self.wait(0.1))
    """
    code = code.replace("```python", "").replace("```", "").strip()

    for invalid, valid in _INVALID_COLOR_MAP.items():
        code = re.sub(rf'\bcolor\s*=\s*{invalid}\b', f'color={valid}', code)
        code = re.sub(rf'\b{invalid}\b(?=\s*[,\)])', valid, code)

    code = re.sub(r'color\s*=\s*["\']#[0-9A-Fa-f]{6}["\']', 'color=BLUE', code)
    # Normalize scene class name — preserve ThreeDScene base class
    if re.search(r'class\s+\w+\s*\(ThreeDScene\)', code):
        code = re.sub(r'class\s+\w+\s*\(ThreeDScene\)', 'class AlgorithmScene(ThreeDScene)', code)
    else:
        code = re.sub(r'class\s+\w+Scene\s*\(Scene\)', 'class AlgorithmScene(Scene)', code)

    for name in _UNKNOWN_HELPERS:
        code = re.sub(
            rf'^\s*self\.play\(\s*{name}\([^)]*\)\s*\)\s*$',
            '        self.wait(0.1)',
            code,
            flags=re.M,
        )
        code = re.sub(
            rf'^\s*{name}\([^)]*\)\s*$',
            '        self.wait(0.1)',
            code,
            flags=re.M,
        )

    return code


def _build_few_shot_system_prompt(examples: list[dict]) -> str:
    """Build a SYSTEM_PROMPT that injects few-shot Manim examples."""
    examples_text = ""
    for i, ex in enumerate(examples, 1):
        examples_text += (
            f"\n<example_{i} tag=\"{ex.get('tag', '')}\" "
            f"pattern=\"{ex.get('pattern_type', '')}\" "
            f"quality=\"{ex.get('quality_score', '')}\">\n"
            f"{ex.get('code', '').strip()}\n"
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
- Output ONLY valid Python code (no markdown)
"""


def call_llm_codegen_with_qa_feedback(anim_ir: dict, qa_issues: list[str]) -> str:
    """Regenerate Manim code with Vision QA feedback injected.

    Instead of blindly retrying codegen, this feeds the specific quality issues
    (overlapping elements, unreadable text, missing steps, etc.) into the prompt
    so the LLM can address them directly.
    """
    max_qa_issues = 20
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
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        timeout=90,
    )
    return post_process_manim_code(resp.choices[0].message.content)


def call_llm_codegen_fix(original_code: str, error_type: str, stderr_snippet: str) -> str:
    """Ask LLM to fix Manim code based on a render error.

    Used by the self-healing codegen loop: when run_manim_code raises
    ManimRenderError, we send the broken code + error back to the LLM.
    """
    fix_prompt = (
        f"The following Manim code failed to render.\n\n"
        f"Error type: {error_type}\n"
        f"Error output (last 1500 chars):\n```\n{stderr_snippet[-1500:]}\n```\n\n"
        f"Original code:\n```python\n{original_code}\n```\n\n"
        f"Fix the code so it renders successfully. "
        f"Keep the same visual intent. Output ONLY the corrected Python code, no markdown."
    )
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
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
        f"Generate a complete Manim scene that visually demonstrates the "
        f"'{algorithm}' algorithm. Animate step-by-step. "
        f"Follow the style and patterns of the reference examples above. "
        f"Output ONLY Python code, no markdown."
    )
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
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
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    code = resp.choices[0].message.content
    return post_process_manim_code(code)


def call_llm_codegen_with_usage(anim_ir: dict):
    prompt = build_prompt_codegen(anim_ir)
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
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

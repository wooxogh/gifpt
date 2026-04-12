# ai/llm_anim_ir.py
import os, json
from openai import OpenAI
from dotenv import load_dotenv

from studio.ai._tracing import traceable

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an animation structure planner.
Convert a pseudocode JSON into a structured animation representation
that describes what entities to draw, where to place them, and how to animate each step.

Your output must be ONLY JSON with these fields:
- metadata: { domain, title }
- layout: list of { id, shape, position: [x, y], color (optional), label (optional), data (optional), dimensions (optional) }
- actions: list of { step, target, animation, description }

POSITIONING CONSTRAINTS (CRITICAL — objects outside safe zone will be clipped):
- Scene frame: horizontal [-7.1, 7.1], vertical [-4.0, 4.0]
- Safe zone for positions: x in [-5.5, 5.5], y in [-2.8, 2.8]
- Reserve y = 3.0 to 3.5 for the title (do not place layout items there)
- Minimum gap between adjacent objects: 1.0 units (center-to-center)

LAYOUT SPACING RULES:
- For N objects in a horizontal row:
  start_x = -(N-1) * spacing / 2, then x[i] = start_x + i * spacing
  where spacing = max(object_width + 0.5, 1.5)
  Ensure the rightmost x + object_half_width < 5.5
- For vertical arrangements: same logic on y axis, ensure y > -2.8
- When placing a label near an object, offset by 0.4-0.6 units (not on top of it)
- Matrices/arrays need extra space: estimate width = cols * 0.5, height = rows * 0.5

Shape field:
- Prefer standard Manim primitives: Rectangle, Circle, Line, Arrow, Dot, Polygon
  or semantic tokens: "matrix", "array"
- If using a non-standard shape, provide enough context via label/data/dimensions

Data field guidelines:
- "matrix" shape: 2D array, e.g., "data": [[1,2,3], [4,5,6]]
- "array" shape: 1D array, e.g., "data": [10, 20, 30, 40]
- Operations: formula string, e.g., "data": "Q·K^T / √d_k"
- Add "dimensions" for size labels, e.g., "3×3" or "(seq_len, d_model)"

Label guidelines:
- Add "label" for identifiers (e.g., "Input", "Q", "K", "V", "Output")
- Skip "label" for purely decorative elements

Animation types: "fade_in", "move", "highlight", "swap", "fade_out"
Output valid JSON only.

Example output:
{
  "metadata": {"domain": "cnn_param", "title": "CNN Convolution"},
  "layout": [
    {"id": "input", "shape": "matrix", "position": [-4, 0], "color": "blue",
     "label": "Input", "data": [[1,2,3,4], [5,6,7,8], [9,10,11,12], [13,14,15,16]], "dimensions": "4×4"},
    {"id": "kernel", "shape": "matrix", "position": [0, 0], "color": "red",
     "label": "Kernel", "data": [[1,0,-1], [1,0,-1], [1,0,-1]], "dimensions": "3×3"},
    {"id": "output", "shape": "matrix", "position": [4, 0], "color": "green",
     "label": "Output", "dimensions": "2×2"}
  ],
  "actions": [
    {"step": 1, "target": "input", "animation": "fade_in", "description": "Show input matrix"},
    {"step": 2, "target": "kernel", "animation": "fade_in", "description": "Show convolution kernel"}
  ]
}
"""

def build_prompt_anim_ir(pseudocode_json: dict) -> str:
    return f"""
Convert the following pseudocode into a structured animation plan JSON:

{json.dumps(pseudocode_json, ensure_ascii=False, indent=2)}
"""

def call_llm_anim_ir(pseudocode_json: dict):
    prompt = build_prompt_anim_ir(pseudocode_json)
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return json.loads(resp.choices[0].message.content)

@traceable(name="anim_ir", run_type="chain")
def call_llm_anim_ir_with_usage(pseudocode_json: dict):
    prompt = build_prompt_anim_ir(pseudocode_json)
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    result = json.loads(resp.choices[0].message.content)
    usage = getattr(resp, "usage", None)
    if usage:
        # OpenAI SDK v1 returns attributes; keep fallback for dict-like
        usage_dict = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None) or (usage.get("prompt_tokens") if hasattr(usage, "get") else None),
            "completion_tokens": getattr(usage, "completion_tokens", None) or (usage.get("completion_tokens") if hasattr(usage, "get") else None),
            "total_tokens": getattr(usage, "total_tokens", None) or (usage.get("total_tokens") if hasattr(usage, "get") else None),
        }
    else:
        usage_dict = None
    return result, usage_dict
    
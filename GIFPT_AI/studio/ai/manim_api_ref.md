# Manim CE 0.19.0 — API Reference

Extracted from library source. Use these exact signatures.

---

## Geometry

### Rectangle
```python
Rectangle(color=WHITE, height=2.0, width=4.0, grid_xstep=None, grid_ystep=None, **kwargs)
```
- `rect.set_fill(color, opacity)`
- `rect.set_stroke(color, width, opacity)`

### Square
```python
Square(side_length=2.0, **kwargs)
```
Inherits Rectangle.

### RoundedRectangle
```python
RoundedRectangle(corner_radius=0.5, **kwargs)
```
Inherits Rectangle params via `**kwargs`.

### Polygon
```python
Polygon(*vertices, **kwargs)
```
Vertices are `Point3D`: e.g. `Polygon([0,0,0], [1,0,0], [1,1,0], [0,1,0])`

### Line
```python
Line(start=LEFT, end=RIGHT, buff=0, path_arc=None, **kwargs)
```
`start`/`end`: coordinate arrays or `Point3D`.

### Arrow
```python
Arrow(*args, stroke_width=6, buff=MED_SMALL_BUFF, max_tip_length_to_length_ratio=0.25, **kwargs)
```
`*args` passed to Line (start, end). e.g. `Arrow(start=point1, end=point2)`

### Circle
```python
Circle(radius=None, color=RED, **kwargs)
```

### Dot
```python
Dot(point=ORIGIN, radius=DEFAULT_DOT_RADIUS, stroke_width=0, fill_opacity=1.0, color=WHITE, **kwargs)
```

### Arc
```python
Arc(radius=1.0, start_angle=0, angle=TAU/4, arc_center=ORIGIN, **kwargs)
```

### SurroundingRectangle
```python
SurroundingRectangle(*mobjects, color=YELLOW, buff=SMALL_BUFF, corner_radius=0.0, **kwargs)
```
Accepts one or more Mobjects directly. VGroup wrapping optional.

---

## Text

### Text
```python
Text(text, fill_opacity=1.0, stroke_width=0, color=None, font_size=DEFAULT_FONT_SIZE,
     line_spacing=-1, font="", slant=NORMAL, weight=NORMAL,
     t2c=None, t2f=None, t2g=None, t2s=None, t2w=None, **kwargs)
```
- `t2c`: dict mapping substring to color, e.g. `{"hello": RED}`
- NO `.set_text()` method. Create new `Text` + `Transform` to update.

---

## Groups

### VGroup
```python
VGroup(*vmobjects, **kwargs)
```
Supports indexing: `vgroup[0]`, `vgroup[1]`.

---

## Animations

| Class | Signature |
|-------|-----------|
| `FadeIn` | `FadeIn(*mobjects, shift=None, target_position=None, scale=1)` |
| `FadeOut` | `FadeOut(*mobjects, shift=None, target_position=None, scale=1)` |
| `Create` | `Create(mobject, lag_ratio=1.0)` — for VMobjects (lines, shapes) |
| `Write` | `Write(vmobject, rate_func=linear, reverse=False)` — for text |
| `Transform` | `Transform(mobject, target_mobject, path_arc=0)` — original ref stays |
| `ReplacementTransform` | `ReplacementTransform(mobject, target_mobject)` — replaces in scene |
| `Indicate` | `Indicate(mobject, scale_factor=1.2, color=YELLOW)` |
| `LaggedStart` | `LaggedStart(*animations, lag_ratio=0.05)` |

---

## Scene

```python
Scene.play(*args, subcaption=None, **kwargs)
# args: Animation objects. Must have at least 1. run_time kwarg controls duration.

Scene.wait(duration=DEFAULT_WAIT_TIME, stop_condition=None)
```

---

## Mobject Methods

| Method | Signature |
|--------|-----------|
| `.shift` | `.shift(*vectors) -> Self` |
| `.move_to` | `.move_to(point_or_mobject, aligned_edge=ORIGIN) -> Self` |
| `.next_to` | `.next_to(mobject_or_point, direction=RIGHT, buff=DEFAULT_BUFF) -> Self` |
| `.align_to` | `.align_to(mobject_or_point, direction=ORIGIN) -> Self` |
| `.get_center` | `.get_center() -> Point3D` |
| `.get_corner` | `.get_corner(direction) -> Point3D` e.g. `UL`, `DR` |
| `.get_left` | `.get_left() -> Point3D` |
| `.get_right` | `.get_right() -> Point3D` |
| `.get_top` | `.get_top() -> Point3D` |
| `.get_bottom` | `.get_bottom() -> Point3D` |
| `.apply_matrix` | `.apply_matrix(matrix) -> Self` — 2x2 or 3x3 array |
| `.copy` | `.copy() -> Self` — NO `.deepcopy()` |
| `.set_fill` | `.set_fill(color, opacity) -> Self` |
| `.set_stroke` | `.set_stroke(color, width, opacity) -> Self` |
| `.to_corner` | `.to_corner(corner) -> Self` e.g. `UL` |
| `.to_edge` | `.to_edge(edge) -> Self` e.g. `LEFT` |
| `.scale` | `.scale(factor) -> Self` |
| `.rotate` | `.rotate(angle) -> Self` |

---

## Color Utils

```python
interpolate_color(color1, color2, alpha)
# alpha=0 -> color1, alpha=1 -> color2
```

---

## Exists But Requires LaTeX (AVOID)

- `Matrix`, `DecimalMatrix`, `IntegerMatrix`, `MobjectMatrix` — default `element_to_mobject=MathTex`
- `Table`, `MathTable`, `MobjectTable`, `IntegerTable`, `DecimalTable` — use `make_grid` instead

---

## Do NOT Use

| Forbidden | Reason |
|-----------|--------|
| `.deepcopy()` | Does not exist. Use `.copy()` |
| `.set_text()` | Does not exist on Text |
| `DashedLine`, `DashedArrow`, `CurvedArrow` | Use `Line` or `Arrow` |
| `ArcBetweenPoints`, `TracedPath` | Not reliably available |
| `self.camera.frame` | Scene camera has no `frame` attribute |
| `Highlight`, `Focus`, `Emphasize` | Do not exist (LLM hallucination) |

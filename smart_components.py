"""Reproduce what Glyphs.app's UFO export does to outlines.

Glyphs applies corner and cap components and decomposes mirrored components on
export. glyphsLib can't do the former faithfully (it doesn't support caps, and
its corner filter only rotates), so we do all of it to the GSFont before
converting to UFO. The rules here were matched against UFOs exported by Glyphs 4.

Points are complex numbers, so rotating is multiplying by a unit complex.
"""

import cmath

from fontTools.misc.bezierTools import splitCubicAtTC
from fontTools.misc.roundTools import otRound
from fontTools.misc.transform import Transform
from glyphsLib.builder import preflight_glyphs
from glyphsLib.classes import GSComponent, GSNode, GSPath
from glyphsLib.types import Transform as GSTransform

OFF, LINE, CURVE = "offcurve", "line", "curve"


def prepare_for_export(font):
    # Copy anchors into composites first, so decomposed glyphs keep them.
    preflight_glyphs(font)
    for glyph in font.glyphs:
        for layer in glyph.layers:
            apply_smart_components(font, layer)
    for glyph in font.glyphs:
        for layer in glyph.layers:
            decompose_mirrored(font, layer)


def apply_smart_components(font, layer):
    hints = [h for h in layer.hints if h.type in ("Corner", "Cap")]
    if not hints:
        return
    # Glyphs fits every component to the original outline, so resolve target
    # nodes and stroke directions before changing anything.
    directions = {node: tangents(path, node) for path in layer.paths for node in path.nodes}
    targets = []
    for hint in hints:
        shape, index = hint.origin.value[:2]
        path = layer.shapes[shape]
        targets.append((hint, path, path.nodes[index]))
    for hint, path, node in targets:
        source = font.glyphs[hint.name].layers[layer.associatedMasterId]
        apply = apply_corner if hint.type == "Corner" else apply_cap
        apply(path, node, source, hint, directions)
    layer.hints = [h for h in layer.hints if h not in hints]


def apply_corner(path, node, source, hint, directions):
    sx, sy = (hint.scale.x, hint.scale.y) if hint.scale else (1, 1)
    pts = component_points(source, anchor(source, "origin", 0), sx, sy)

    # Rotate rigidly per the alignment option: 0 aligns the corner's end with the
    # outgoing stroke, 1 its start with the incoming stroke, 2 splits the difference.
    v_in, v_out = directions[node]
    a_in, a_out = cmath.phase(-v_in / pts[0][0]), cmath.phase(v_out / pts[-1][0])
    middle = a_in + cmath.phase(cmath.rect(1, a_out - a_in)) / 2
    turn = cmath.rect(1, {0: a_out, 1: a_in}.get((hint.options or 0) & 3, middle))
    p = position(node)
    placed = [[p + z * turn, t] for z, t in pts]
    swing(placed, 0, p, -v_in)
    swing(placed, -1, p, v_out)
    splice(path, node, node, placed)


def apply_cap(path, node, source, hint, directions):
    fit = (hint.options or 0) & 8
    sx, sy = (hint.scale.x, hint.scale.y) if hint.scale else (1, 1)
    if fit:  # The cap is stretched along the stroke end instead.
        sx, sy = abs(sy) if sx > 0 else -abs(sy), 1 if sy > 0 else -1
    pts = component_points(source, 0, sx, sy)
    n1, n2 = (scale(anchor(source, name), sx, sy) for name in ("node1", "node2"))
    if sx * sy < 0:
        n1, n2 = n2, n1

    # The cap replaces the segment from `node` to the next on-curve node.
    nodes = list(path.nodes)
    k = (nodes.index(node) + 1) % len(nodes)
    while nodes[k].type == OFF:
        k = (k + 1) % len(nodes)
    last = nodes[k]
    p1, p2 = position(node), position(last)
    stretch = abs(p2 - p1) / abs(n2 - n1) if fit else 1

    def place(z):
        local = (z - n1) / unit(n2 - n1)  # Stroke end along the x axis.
        return p1 + scale(local, stretch, 1) * unit(p2 - p1)

    placed = [[place(z), t] for z, t in pts]
    swing(placed, 0, p1, -directions[node][0])
    if fit:
        swing(placed, -1, p2, directions[last][1])
    splice(path, node, last, placed)


def decompose_mirrored(font, layer):
    """Replace mirrored components with their (reversed) outlines, in shape order."""

    def flatten(name, transform):
        shapes = []
        for shape in font.glyphs[name].layers[layer.associatedMasterId].shapes:
            if not isinstance(shape, GSComponent):
                shapes.append(transformed_path(shape, transform))
            elif font.glyphs[shape.name].smartComponentAxes:
                # glyphsLib interpolates smart components itself; just carry the transform.
                nested = shape.clone()
                nested.transform = GSTransform(*transform.transform(Transform(*shape.transform)))
                nested.smartComponentValues = dict(shape.smartComponentValues or {})
                shapes.append(nested)
            else:
                shapes += flatten(shape.name, transform.transform(Transform(*shape.transform)))
        return shapes

    shapes = []
    for shape in layer.shapes:
        if isinstance(shape, GSComponent) and determinant(Transform(*shape.transform)) < 0:
            shapes += flatten(shape.name, Transform(*shape.transform))
        else:
            shapes.append(shape)
    layer.shapes = shapes


def component_points(source, origin, sx, sy):
    """The component's first path as [point, type] pairs, scaled, in host direction."""
    pts = [[scale(position(n) - origin, sx, sy), n.type] for n in source.paths[0].nodes]
    if sx * sy >= 0:
        return pts
    # Mirrored: reverse, moving each segment type to the segment's new end.
    on = [p for p in pts if p[1] != OFF]
    seg_type = {id(a): b[1] for a, b in zip(on, on[1:])}
    return [[z, OFF if t == OFF else seg_type.get(id(p), LINE)] for p in pts[::-1] for z, t in [p]]


def transformed_path(path, transform):
    """A transformed copy of a closed path, reversed (as Glyphs does) if mirrored."""
    nodes = path.nodes
    if determinant(transform) > 0:
        order, types = range(len(nodes)), [n.type for n in nodes]
    else:
        on = [i for i, n in enumerate(nodes) if n.type != OFF]
        seg_type = {i: nodes[on[(k + 1) % len(on)]].type for k, i in enumerate(on)}
        order = [*reversed(range(len(nodes) - 1)), len(nodes) - 1]
        types = [OFF if n.type == OFF else seg_type[i] for i, n in enumerate(nodes)]
    copy = GSPath()
    copy.closed = path.closed
    copy.nodes = [GSNode(transform.transformPoint(tuple(nodes[i].position)), types[i]) for i in order]
    return copy


def swing(pts, end, pivot, direction):
    """Rotate an endpoint (and its handle) about pivot until it lies along direction."""
    turn = unit(direction / (pts[end][0] - pivot))
    handle = 1 if end == 0 else -2
    for i in (end, handle) if pts[handle][1] == OFF else (end,):
        pts[i][0] = pivot + (pts[i][0] - pivot) * turn


def splice(path, first, last, inserted):
    """Replace on-curve nodes first..last with the open path `inserted`.

    Curved neighbouring segments are split where the inserted path's ends land.
    """
    original = list(path.nodes)
    in_len = 4 if first.type == CURVE else 2
    # Rotate so the incoming segment starts at index 0.
    shift = original.index(first) - (in_len - 1)
    nodes = original[shift:] + original[:shift]
    n, j = len(nodes), nodes.index(last)
    out_len = 4 if nodes[(j + 1) % n].type == OFF else 2
    in_head = split([position(nd) for nd in nodes[:in_len]], inserted[0][0])[0]
    out_tail = split([position(nodes[(j + i) % n]) for i in range(out_len)], inserted[-1][0])[1]

    new = [(z, OFF) for z in in_head[1:-1]] + [(inserted[0][0], first.type)]
    new += [(z, t) for z, t in inserted[1:]] + [(z, OFF) for z in out_tail[1:-1]]
    new = [GSNode((otRound(round(z.real, 6)), otRound(round(z.imag, 6))), t) for z, t in new]
    result = nodes[:1] + new + nodes[j + out_len - 1 :]

    # Glyphs keeps the inserted path's first node at the replaced node's index.
    start = new[len(in_head) - 2]
    kept = set(result)
    index = original.index(first)
    removed_before = [nd for nd in original[:index] if nd not in kept and nd not in nodes[1:in_len]]
    k = (result.index(start) - (index - len(removed_before))) % len(result)
    path.nodes = result[k:] + result[:k]


def split(seg, p):
    """Split a line or cubic segment at the point closest to p."""
    if len(seg) == 2:
        mid = seg[0] + (seg[1] - seg[0]) * ((p - seg[0]) / (seg[1] - seg[0])).real
        return [seg[0], mid], [mid, seg[1]]

    def dist(t):
        a, b, c, d = seg
        return abs((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t**2 * c + t**3 * d - p)

    # Coarse search, then refine by ternary search.
    best = min((i / 100 for i in range(101)), key=dist)
    lo, hi = max(0.0, best - 0.01), min(1.0, best + 0.01)
    for _ in range(50):
        m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
        lo, hi = (lo, m2) if dist(m1) < dist(m2) else (m1, hi)
    return splitCubicAtTC(*seg, (lo + hi) / 2)


def tangents(path, node):
    """Unit directions of the path arriving at and leaving `node`."""
    nodes = list(path.nodes)
    i, p = nodes.index(node), position(node)

    def toward(step):
        for k in range(1, len(nodes)):
            q = position(nodes[(i + step * k) % len(nodes)])
            if q != p:
                return unit(q - p)
        return 1

    return -toward(-1), toward(1)


def anchor(layer, name, default=None):
    return next((position(a) for a in layer.anchors if a.name == name), default)


def position(obj):
    return complex(obj.position.x, obj.position.y)


def scale(z, sx, sy):
    return complex(z.real * sx, z.imag * sy)


def unit(z):
    return z / abs(z)


def determinant(t):
    return t[0] * t[3] - t[1] * t[2]

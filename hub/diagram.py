"""Auto-generates an SVG wiring diagram from a project's Connection rows."""
from html import escape

BOX_W, HEAD, ROW, GAP, PAD = 190, 34, 28, 26, 16
W = 760


def _layout(parts, x):
    """parts: ordered dict name -> ordered list of pins. Returns boxes and pin anchor map."""
    boxes, anchors, y = [], {}, 10
    for name, pins in parts.items():
        h = HEAD + ROW * len(pins) + 8
        boxes.append((name, pins, x, y, h))
        for i, pin in enumerate(pins):
            anchors[(name, pin)] = y + HEAD + ROW * i + ROW / 2
        y += h + GAP
    return boxes, anchors, y - GAP + 10


def wiring_svg(connections):
    left, right = {}, {}
    for c in connections:
        left.setdefault(c.from_part, [])
        right.setdefault(c.to_part, [])
        if c.from_pin not in left[c.from_part]:
            left[c.from_part].append(c.from_pin)
        if c.to_pin not in right[c.to_part]:
            right[c.to_part].append(c.to_pin)
    if not left:
        return ""
    lx, rx = 12, W - BOX_W - 12
    lboxes, lanch, lh = _layout(left, lx)
    rboxes, ranch, rh = _layout(right, rx)
    H = max(lh, rh) + 10
    out = [f'<svg class="wiring" viewBox="0 0 {W} {H}" role="img" aria-label="Wiring diagram" xmlns="http://www.w3.org/2000/svg">']

    def box(name, pins, x, y, h, side):
        s = [f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{h}" rx="10" class="d-box"/>',
             f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{HEAD}" rx="10" class="d-head"/>',
             f'<text x="{x + BOX_W / 2}" y="{y + 22}" text-anchor="middle" class="d-title">{escape(name)}</text>']
        for i, pin in enumerate(pins):
            py = y + HEAD + ROW * i + ROW / 2
            dot = x + BOX_W if side == "L" else x
            tx = x + BOX_W - PAD if side == "L" else x + PAD
            anchor = "end" if side == "L" else "start"
            s.append(f'<text x="{tx}" y="{py + 4}" text-anchor="{anchor}" class="d-pin">{escape(pin)}</text>')
            s.append(f'<circle cx="{dot}" cy="{py}" r="5" class="d-dot"/>')
        return "".join(s)

    for name, pins, x, y, h in lboxes:
        out.append(box(name, pins, x, y, h, "L"))
    for name, pins, x, y, h in rboxes:
        out.append(box(name, pins, x, y, h, "R"))
    for c in connections:
        y1 = lanch[(c.from_part, c.from_pin)]
        y2 = ranch[(c.to_part, c.to_pin)]
        x1, x2 = lx + BOX_W, rx
        mid = (x2 - x1) / 2
        out.append(
            f'<path d="M{x1},{y1} C{x1 + mid},{y1} {x2 - mid},{y2} {x2},{y2}" fill="none" '
            f'stroke="{escape(c.wire_color)}" stroke-width="3" stroke-linecap="round" class="d-wire">'
            f'<title>{escape(c.from_part)} {escape(c.from_pin)} → {escape(c.to_part)} {escape(c.to_pin)}</title></path>')
    out.append("</svg>")
    return "".join(out)

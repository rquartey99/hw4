"""Generate the repeating crest background (public/crests.svg and public/crests-light.svg).

Original heraldic-style shields labeled with the initials of Yale's 14 residential colleges and 12 professional
schools. They are not copies of any official arms (those are trademarks); each shield gets one of a few simple
designs so the pattern has variety.
"""

from pathlib import Path

COLLEGES = ["BF", "BK", "BR", "DC", "ES", "GH", "JE", "MC", "PC", "PM", "SY", "SM", "TD", "TC"]
SCHOOLS = ["SOM", "LAW", "MED", "ART", "DIV", "MUS", "NUR", "SPH", "ARC", "ENG", "ENV", "DRA"]
LABELS = COLLEGES + SCHOOLS  # 26 shields

COLS, ROWS = 7, 4  # 28 slots: 26 shields + 2 bulldog paw prints
CELL_W, CELL_H = 110, 130
W, H = COLS * CELL_W, ROWS * CELL_H
SHIELD = "M0 0 H44 V28 C44 44 22 54 22 54 C22 54 0 44 0 28 Z"  # 44 x 54

# Simple heraldic designs, kept clear of the middle band where the initials go.
DESIGNS = [
    "",  # plain
    '<rect x="0" y="0" width="44" height="11" stroke="none" fill-opacity="0.45"/>',  # chief (top band)
    '<path d="M5 47 L22 38 L39 47" fill="none" stroke-width="2.5"/>',  # low chevron
    '<path d="M5 4 H39 V27 C39 39 22 47 22 47 C22 47 5 39 5 27 Z" fill="none" stroke-width="1.4"/>',  # inner border
    '<path d="M0 41 H44 M0 46 H44" stroke-width="2"/>',  # base stripes
    '<path d="M14 0 L22 12 L30 0 Z" stroke="none" fill-opacity="0.45"/>',  # small point at the top
]

PAW = (
    '<g transform="translate(-14 -14)"><ellipse cx="14" cy="18" rx="7" ry="6"/>'
    '<circle cx="5" cy="9" r="3"/><circle cx="11" cy="4" r="3"/><circle cx="18" cy="4" r="3"/><circle cx="24" cy="9" r="3"/></g>'
)


def shield(label: str, design: str, x: float, y: float, clip_id: str) -> str:
    size = 13 if len(label) == 2 else 10.5
    return f"""<g transform="translate({x - 22} {y - 27})">
  <clipPath id="{clip_id}"><path d="{SHIELD}"/></clipPath>
  <g clip-path="url(#{clip_id})">{design}</g>
  <path d="{SHIELD}" fill="none" stroke-width="2.2"/>
  <text x="22" y="31" text-anchor="middle" font-size="{size}" stroke="none">{label}</text>
</g>"""


def build(color: str, opacity: float) -> str:
    items, i = [], 0
    for row in range(ROWS):
        offset = CELL_W / 2 if row % 2 else 0  # brick layout
        for col in range(COLS):
            x, y = col * CELL_W + CELL_W / 2 + offset, row * CELL_H + CELL_H / 2
            slot = row * COLS + col
            for dx in ((0, -W) if x > W - 30 else (0,)):  # repeat shields cut off at the right edge on the left
                if slot in (10, 25):
                    items.append(f'<g transform="translate({x + dx} {y})">{PAW}</g>')
                else:
                    label = LABELS[i % len(LABELS)]
                    items.append(shield(label, DESIGNS[(i * 5) % len(DESIGNS)], x + dx, y, f"c{slot}{'w' if dx else ''}"))
            if slot not in (10, 25):
                i += 1
    body = "\n".join(items)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
        f'<g fill="{color}" stroke="{color}" opacity="{opacity}" font-family="Georgia, \'Times New Roman\', serif" '
        f'font-weight="700" letter-spacing="0.5">\n{body}\n</g>\n</svg>\n'
    )


public = Path(__file__).resolve().parent.parent / "public"
(public / "crests.svg").write_text(build("#00356b", 0.07))  # on light backgrounds
(public / "crests-light.svg").write_text(build("#ffffff", 0.09))  # on navy backgrounds
print(f"wrote crests.svg and crests-light.svg ({W}x{H}, {len(LABELS)} shields)")

from PIL import Image, ImageDraw

BG = (27, 67, 50, 255)      # #1b4332
ACCENT = (111, 211, 154, 255)  # #6fd39a
ACCENT2 = (76, 175, 125, 255)  # #4caf7d


def draw_mark(draw, cx, cy, r):
    # Outer ring
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT2)
    # Inner droplet-like arrow shape suggesting upward pumped flow
    w = r * 0.9
    h = r * 1.3
    points = [
        (cx, cy - h * 0.55),
        (cx + w * 0.42, cy + h * 0.15),
        (cx + w * 0.20, cy + h * 0.15),
        (cx + w * 0.20, cy + h * 0.55),
        (cx - w * 0.20, cy + h * 0.55),
        (cx - w * 0.20, cy + h * 0.15),
        (cx - w * 0.42, cy + h * 0.15),
    ]
    draw.polygon(points, fill=(255, 255, 255, 255))


def make_icon(size, bg=BG, padding_ratio=0.12, path=None):
    img = Image.new("RGBA", (size, size), bg)
    draw = ImageDraw.Draw(img)
    r = size * (0.5 - padding_ratio)
    draw_mark(draw, size / 2, size / 2, r)
    img.save(path)


make_icon(192, path="icons/icon-192.png")
make_icon(512, path="icons/icon-512.png")
# Maskable: keep the mark within the safe zone (inner ~80% circle), full-bleed background
make_icon(512, padding_ratio=0.22, path="icons/icon-maskable-512.png")
# Apple touch icon: no transparency, square, slightly less padding
make_icon(180, padding_ratio=0.14, path="icons/apple-touch-icon.png")

print("icons written")

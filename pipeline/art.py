"""Drawing for Moon Tales Kids videos: backgrounds, characters, props, overlays.

Everything is drawn with Pillow, no paid tools. Rule from the channel owner:
never draw a rainbow (no rainbow arcs, no rainbow-striped colour bands).
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(HERE, "fonts", "Fredoka.ttf")

FW, FH = 1920, 1080          # output frame
BW, BH = 2112, 1188          # background (10% larger, for slow panning)
SS = 2                       # supersampling for smooth edges


def font(size, weight="SemiBold"):
    f = ImageFont.truetype(FONT_PATH, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    f._mt_weight = weight
    return f


def hexc(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def mix(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(len(c1)))


class Canvas:
    """RGBA canvas drawn at SS x resolution, with 1x coordinates.

    Semi-transparent colours are drawn on a temporary layer and composited,
    because Pillow overwrites (does not blend) pixels on RGBA images.
    """

    def __init__(self, w, h, bg=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w * SS, h * SS), bg)
        self.d = ImageDraw.Draw(self.img)

    @staticmethod
    def _translucent(*cols):
        return any(c is not None and len(c) == 4 and c[3] < 255 for c in cols)

    def _do(self, fn, *cols):
        if self._translucent(*cols):
            layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
            fn(ImageDraw.Draw(layer))
            self.img.alpha_composite(layer)
        else:
            fn(self.d)

    def _p(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def ellipse(self, cx, cy, rx, ry, fill, outline=None, width=0):
        box = [(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS]
        self._do(lambda d: d.ellipse(box, fill=fill, outline=outline, width=width * SS), fill, outline)

    def circle(self, cx, cy, r, fill, **kw):
        self.ellipse(cx, cy, r, r, fill, **kw)

    def rect(self, x0, y0, x1, y1, fill, r=0, outline=None, width=0):
        box = [x0 * SS, y0 * SS, x1 * SS, y1 * SS]
        self._do(lambda d: d.rounded_rectangle(box, radius=r * SS, fill=fill, outline=outline,
                                               width=width * SS), fill, outline)

    def poly(self, pts, fill, outline=None, width=0):
        p = self._p(pts)
        self._do(lambda d: d.polygon(p, fill=fill, outline=outline, width=width * SS), fill, outline)

    def line(self, pts, fill, width=4, joint="curve"):
        p = self._p(pts)
        ends = [pts[0], pts[-1]]

        def fn(d):
            d.line(p, fill=fill, width=width * SS, joint=joint)
            for x, y in ends:
                rr = width / 2 * SS
                d.ellipse([x * SS - rr, y * SS - rr, x * SS + rr, y * SS + rr], fill=fill)
        self._do(fn, fill)

    def arc(self, cx, cy, rx, ry, a0, a1, fill, width=4):
        box = [(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS]
        self._do(lambda d: d.arc(box, a0, a1, fill=fill, width=width * SS), fill)

    def pie(self, cx, cy, rx, ry, a0, a1, fill):
        box = [(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS]
        self._do(lambda d: d.pieslice(box, a0, a1, fill=fill), fill)

    def chord(self, cx, cy, rx, ry, a0, a1, fill):
        box = [(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS]
        self._do(lambda d: d.chord(box, a0, a1, fill=fill), fill)

    def text(self, x, y, s, f, fill, anchor="la", stroke=0, stroke_fill=None):
        f2 = ImageFont.truetype(FONT_PATH, f.size * SS)
        try:
            f2.set_variation_by_name(getattr(f, "_mt_weight", "SemiBold"))
        except Exception:
            pass
        self._do(lambda d: d.text((x * SS, y * SS), s, font=f2, fill=fill, anchor=anchor,
                                  stroke_width=stroke * SS, stroke_fill=stroke_fill), fill)

    def paste(self, other, x, y):
        """Paste another Canvas (or 1x image) at 1x coords."""
        im = other.img if isinstance(other, Canvas) else other.resize(
            (other.width * SS, other.height * SS), Image.LANCZOS)
        self.img.alpha_composite(im, (int(x * SS), int(y * SS)))

    def final(self):
        return self.img.resize((self.w, self.h), Image.LANCZOS)


# ---------------------------------------------------------------- palette
SKY = {
    "day": (hexc("#7EC8F2"), hexc("#D8F1FF")),
    "sunset": (hexc("#F59E7A"), hexc("#FFE3B8")),
    "night": (hexc("#16204A"), hexc("#3B4C8C")),
}
GRASS = {"day": hexc("#7CCB5A"), "sunset": hexc("#8FB357"), "night": hexc("#2F5A45")}
GRASS2 = {"day": hexc("#5DB044"), "sunset": hexc("#6E9A45"), "night": hexc("#244A38")}


def sky(c, time, weather):
    top, bot = SKY[time]
    if weather in ("cloudy", "rain", "windy") and time == "day":
        top, bot = mix(top, hexc("#A9B8C6"), 0.55), mix(bot, hexc("#E3E8EC"), 0.5)
    if weather == "snow" and time == "day":
        top, bot = hexc("#B9CEDF"), hexc("#EEF4F8")
    for y in range(c.h):
        col = mix(top, bot, y / c.h)
        c.d.line([(0, y * SS), (c.w * SS, y * SS)], fill=col, width=SS)


def stars(c, n=70, seed=3):
    r = random.Random(seed)
    for _ in range(n):
        x, y = r.uniform(0, c.w), r.uniform(0, c.h * 0.55)
        s = r.uniform(1.5, 4)
        c.circle(x, y, s, hexc("#FFF6D6", r.randint(150, 255)))


def moon(c, x, y, r=80):
    for i in range(6, 0, -1):
        c.circle(x, y, r + i * 14, hexc("#FFF4C2", 14))
    c.circle(x, y, r, hexc("#FFF1B5"))
    for dx, dy, rr in ((-25, -15, 14), (20, 25, 10), (-5, 35, 7)):
        c.circle(x + dx, y + dy, rr, hexc("#F3E19A"))


def sun(c, x, y, r=85):
    for i in range(5, 0, -1):
        c.circle(x, y, r + i * 18, hexc("#FFE680", 22))
    for k in range(12):
        a = k * math.pi / 6
        c.line([(x + math.cos(a) * (r + 18), y + math.sin(a) * (r + 18)),
                (x + math.cos(a) * (r + 48), y + math.sin(a) * (r + 48))],
               hexc("#FFD23F"), 10)
    c.circle(x, y, r, hexc("#FFD23F"))
    c.circle(x - 28, y - 10, 9, hexc("#7A4B1E"))
    c.circle(x + 28, y - 10, 9, hexc("#7A4B1E"))
    c.arc(x, y + 8, 32, 26, 20, 160, hexc("#7A4B1E"), 6)


def cloud(c, x, y, s=1.0, col=None):
    col = col or hexc("#FFFFFF", 240)
    for dx, dy, r in ((0, 0, 60), (55, -25, 70), (115, 0, 58), (60, 20, 60), (-45, 15, 42), (160, 18, 40)):
        c.circle(x + dx * s, y + dy * s, r * s, col)


def hills(c, time, horizon):
    g1, g2 = GRASS[time], GRASS2[time]
    pts = [(0, c.h)]
    for x in range(0, c.w + 40, 40):
        pts.append((x, horizon - 40 + 30 * math.sin(x / 260.0)))
    pts.append((c.w, c.h))
    c.poly(pts, g2)
    pts = [(0, c.h)]
    for x in range(0, c.w + 40, 40):
        pts.append((x, horizon + 30 + 22 * math.sin(x / 330.0 + 2)))
    pts.append((c.w, c.h))
    c.poly(pts, g1)


def tree(c, x, base, s=1.0, time="day"):
    trunk = hexc("#8A5A34") if time != "night" else hexc("#4C3424")
    leaf = hexc("#4FAF4A") if time != "night" else hexc("#24533A")
    leaf2 = hexc("#6CC65B") if time != "night" else hexc("#2E6647")
    c.rect(x - 22 * s, base - 230 * s, x + 22 * s, base, trunk, r=10 * s)
    for dx, dy, r in ((0, -300, 110), (-80, -240, 85), (80, -240, 85), (-40, -360, 80), (45, -360, 80)):
        c.circle(x + dx * s, base + dy * s, r * s, leaf)
    for dx, dy, r in ((-30, -320, 50), (50, -270, 40)):
        c.circle(x + dx * s, base + dy * s, r * s, leaf2)


def flower(c, x, y, col, s=1.0):
    c.line([(x, y), (x, y + 40 * s)], hexc("#3E8E3A"), int(5 * s) or 1)
    for k in range(5):
        a = k * 2 * math.pi / 5
        c.circle(x + math.cos(a) * 12 * s, y + math.sin(a) * 12 * s, 10 * s, col)
    c.circle(x, y, 8 * s, hexc("#FFD23F"))


def flowers(c, y0, y1, n, seed, time="day"):
    r = random.Random(seed)
    cols = ["#FF8FB1", "#FFFFFF", "#FFB347", "#C9A0FF"]
    for _ in range(n):
        col = hexc(r.choice(cols), 255 if time != "night" else 140)
        flower(c, r.uniform(0, c.w), r.uniform(y0, y1), col, r.uniform(0.8, 1.3))


def house(c, x, base, time):
    wall = hexc("#F6D7A7") if time != "night" else hexc("#8C7A63")
    roof = hexc("#D9604C") if time != "night" else hexc("#7A3A30")
    c.rect(x, base - 330, x + 420, base, wall, r=8)
    c.poly([(x - 40, base - 320), (x + 210, base - 520), (x + 460, base - 320)], roof)
    c.rect(x + 160, base - 190, x + 260, base, hexc("#9A5B34"), r=12)
    c.circle(x + 245, base - 95, 7, hexc("#FFD23F"))
    win = hexc("#BFE6FF") if time != "night" else hexc("#FFE08A")
    for wx in (x + 40, x + 300):
        c.rect(wx, base - 270, wx + 85, base - 180, win, r=8, outline=hexc("#FFFFFF"), width=6)


def fence(c, y, time):
    col = hexc("#FFFFFF") if time != "night" else hexc("#9AA3B5")
    c.rect(0, y + 30, c.w, y + 50, col)
    c.rect(0, y + 85, c.w, y + 105, col)
    for x in range(10, c.w, 70):
        c.poly([(x, y + 150), (x, y + 10), (x + 22, y - 12), (x + 44, y + 10), (x + 44, y + 150)], col)


def sea(c, horizon, time):
    top = hexc("#3FA7D6") if time != "night" else hexc("#1C3566")
    c.rect(0, horizon, c.w, horizon + 260, top)
    for k in range(6):
        y = horizon + 30 + k * 40
        for x in range(0, c.w, 140):
            c.arc(x + (k % 2) * 70, y, 40, 12, 200, 340, hexc("#FFFFFF", 150), 5)
    sand = hexc("#F4D9A0") if time != "night" else hexc("#8D7B5A")
    pts = [(0, c.h), (0, horizon + 250)]
    for x in range(0, c.w + 60, 60):
        pts.append((x, horizon + 240 + 12 * math.sin(x / 150.0)))
    pts.append((c.w, c.h))
    c.poly(pts, sand)


def room(c, wall, floor, horizon):
    c.rect(0, 0, c.w, horizon, wall)
    c.rect(0, horizon, c.w, c.h, floor)
    c.rect(0, horizon - 14, c.w, horizon + 4, hexc("#FFFFFF", 200))


def window(c, x, y, w, h, time, weather):
    c.rect(x - 14, y - 14, x + w + 14, y + h + 14, hexc("#FFFFFF"), r=14)
    inner = Canvas(w, h)
    sky(inner, time, weather)
    if time == "night":
        stars(inner, 18, 9)
        moon(inner, w * 0.65, h * 0.38, 46)
    elif weather == "sunny":
        sun(inner, w * 0.7, h * 0.35, 40)
    else:
        cloud(inner, w * 0.2, h * 0.4, 0.6)
    c.paste(inner, x, y)
    c.rect(x + w / 2 - 6, y, x + w / 2 + 6, y + h, hexc("#FFFFFF"))
    c.rect(x, y + h / 2 - 6, x + w, y + h / 2 + 6, hexc("#FFFFFF"))


# ---------------------------------------------------------------- props
def prop(c, name, x, y, time="day"):
    """Draw a prop with its centre at (x, y) (1x background coords)."""
    if name == "kite":
        c.line([(x, y + 110), (x - 260, y + 520)], hexc("#555555", 200), 3)
        c.poly([(x, y - 110), (x + 85, y), (x, y + 110), (x - 85, y)], hexc("#FF6B6B"))
        c.poly([(x, y - 110), (x + 85, y), (x, y)], hexc("#FFD23F"))
        c.poly([(x, y + 110), (x - 85, y), (x, y)], hexc("#FFD23F"))
        for k in range(4):
            bx, by = x - 15 + k * 8, y + 140 + k * 45
            c.poly([(bx, by), (bx + 22, by + 12), (bx, by + 24)], hexc("#4FA3E3"))
    elif name == "ball":
        c.circle(x, y, 55, hexc("#FF6B6B"))
        c.chord(x, y, 55, 55, 200, 340, hexc("#FFFFFF"))
        c.chord(x, y, 55, 55, 20, 160, hexc("#4FA3E3"))
    elif name == "umbrella":
        c.line([(x, y - 40), (x, y + 150)], hexc("#6B4A2B"), 8)
        c.arc(x + 18, y + 150, 18, 18, 0, 180, hexc("#6B4A2B"), 8)
        c.pie(x, y - 20, 170, 120, 180, 360, hexc("#FFD23F"))
        for k in range(4):
            c.pie(x, y - 20, 170, 120, 180 + k * 45, 180 + k * 45 + 22, hexc("#FF8A5B"))
    elif name == "umbrella_over":
        c.line([(x, y - 60), (x, y + 210)], hexc("#6B4A2B"), 9)
        c.arc(x + 20, y + 210, 20, 20, 0, 180, hexc("#6B4A2B"), 9)
        c.pie(x, y - 30, 230, 150, 180, 360, hexc("#FFD23F"))
        for k in range(4):
            c.pie(x, y - 30, 230, 150, 180 + k * 45, 180 + k * 45 + 22, hexc("#FF8A5B"))
        c.circle(x, y - 182, 10, hexc("#6B4A2B"))
    elif name == "book":
        c.rect(x - 90, y - 60, x + 90, y + 60, hexc("#4FA3E3"), r=8)
        c.rect(x - 5, y - 60, x + 5, y + 60, hexc("#2E6FA8"))
        c.rect(x - 70, y - 35, x - 20, y - 25, hexc("#FFFFFF", 200), r=4)
    elif name == "apple":
        c.circle(x - 22, y, 45, hexc("#E84A4A"))
        c.circle(x + 22, y, 45, hexc("#E84A4A"))
        c.line([(x, y - 40), (x + 8, y - 75)], hexc("#6B4A2B"), 7)
        c.ellipse(x + 30, y - 62, 24, 12, hexc("#4FAF4A"))
    elif name == "cake":
        c.rect(x - 110, y - 40, x + 110, y + 70, hexc("#F7B7C9"), r=16)
        c.rect(x - 110, y - 50, x + 110, y - 10, hexc("#FFFFFF"), r=16)
        for k in range(3):
            cx = x - 50 + k * 50
            c.rect(cx - 6, y - 110, cx + 6, y - 50, hexc("#8EC5FF"), r=4)
            c.ellipse(cx, y - 122, 9, 15, hexc("#FFB020"))
    elif name == "cup":
        c.rect(x - 45, y - 50, x + 45, y + 50, hexc("#FFFFFF"), r=14)
        c.arc(x + 55, y, 25, 25, 270, 90, hexc("#FFFFFF"), 12)
        for k in range(3):
            c.arc(x - 20 + k * 20, y - 80, 8, 20, 90, 270, hexc("#FFFFFF", 160), 4)
    elif name == "star":
        pts = []
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5
            r = 70 if k % 2 == 0 else 30
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
        c.poly(pts, hexc("#FFD23F"))
    elif name == "flower":
        flower(c, x, y, hexc("#FF8FB1"), 2.2)
    elif name == "puddle":
        c.ellipse(x, y, 190, 45, hexc("#7FB7E0", 220))
        c.ellipse(x - 40, y - 8, 70, 12, hexc("#FFFFFF", 120))
    elif name == "boat":
        c.poly([(x - 110, y), (x + 110, y), (x + 70, y + 60), (x - 70, y + 60)], hexc("#E85D5D"))
        c.line([(x, y), (x, y - 160)], hexc("#6B4A2B"), 8)
        c.poly([(x + 6, y - 155), (x + 100, y - 30), (x + 6, y - 30)], hexc("#FFFFFF"))
    elif name == "bed":
        c.rect(x - 330, y - 60, x + 330, y + 120, hexc("#8A5A34"), r=20)
        c.rect(x - 310, y - 100, x + 310, y + 40, hexc("#A7C7F2"), r=30)
        c.rect(x - 300, y - 150, x - 140, y - 70, hexc("#FFFFFF"), r=30)
        for k in range(5):
            c.circle(x - 60 + k * 80, y - 30, 14, hexc("#FFFFFF", 160))
    elif name == "table":
        c.rect(x - 380, y - 30, x + 380, y + 10, hexc("#B7794A"), r=10)
        c.rect(x - 340, y + 10, x - 310, y + 230, hexc("#9A6238"))
        c.rect(x + 310, y + 10, x + 340, y + 230, hexc("#9A6238"))
    elif name == "lamp":
        c.rect(x - 8, y - 160, x + 8, y + 60, hexc("#6B5B4B"))
        c.poly([(x - 80, y - 150), (x + 80, y - 150), (x + 50, y - 250), (x - 50, y - 250)], hexc("#FFCF70"))
        for i in range(5, 0, -1):
            c.circle(x, y - 160, 60 + i * 30, hexc("#FFE7A0", 14))


PROP_SPOT = {  # default placements in background coords
    "kite": (1620, 250), "ball": (1500, 960), "umbrella": (1580, 640), "umbrella_over": (1250, 330), "book": (1560, 930),
    "apple": (1480, 880), "cake": (1050, 790), "cup": (1350, 800), "star": (1700, 260),
    "flower": (1600, 900), "puddle": (1100, 1060), "boat": (1450, 980),
    "bed": (1720, 900), "table": (1056, 840), "lamp": (300, 760),
}


# ---------------------------------------------------------------- backgrounds
def background(setting, time="day", weather="sunny", props=(), seed=1, show_moon=True):
    c = Canvas(BW, BH)
    indoor = setting in ("kitchen", "bedroom", "classroom")
    if indoor:
        if setting == "kitchen":
            room(c, hexc("#FCE9C8"), hexc("#D9B48C"), 760)
            for x in range(0, BW, 120):
                for y in range(380, 640, 120):
                    c.rect(x + 6, y + 6, x + 114, y + 114, hexc("#FFFFFF", 90), r=10)
            window(c, 260, 140, 420, 300, time, weather)
            c.rect(1500, 420, 2112, 760, hexc("#7FB7A8"), r=12)
            c.rect(1480, 400, 2112, 430, hexc("#E9E2D6"), r=8)
            c.circle(1650, 560, 40, hexc("#FFFFFF", 160))
            spot = {"cup": (1640, 345), "apple": (1820, 355), "cake": (1780, 335), "book": (1700, 365)}
            for p in props:
                if p in spot:
                    prop(c, p, *spot[p], time=time)
            props = [p for p in props if p not in spot]
        elif setting == "bedroom":
            wall = hexc("#C9D7F2") if time != "night" else hexc("#5A6A9A")
            floor = hexc("#C9A27C") if time != "night" else hexc("#7A6450")
            room(c, wall, floor, 780)
            for k in range(14):
                r = random.Random(seed + k)
                c.circle(r.uniform(800, 2050), r.uniform(60, 640), 6, hexc("#FFFFFF", 90))
            window(c, 300, 140, 440, 340, time, weather)
            c.ellipse(1056, 1080, 560, 70, hexc("#E98AA8", 200))
            props = list(props) + [p for p in ("bed", "lamp") if p not in props]
        else:  # classroom
            room(c, hexc("#F3E7C9"), hexc("#B98B5E"), 780)
            c.rect(560, 140, 1560, 560, hexc("#2F5E4E"), r=16, outline=hexc("#9A6238"), width=18)
            window(c, 1720, 180, 300, 260, time, weather)
        if time == "night":
            c.rect(0, 0, BW, BH, hexc("#0B1030", 70))
    else:
        sky(c, time, weather)
        if time == "night":
            stars(c, 90, seed)
            if show_moon:
                moon(c, 1700, 230, 95)
        elif time == "sunset":
            c.circle(1650, 600, 120, hexc("#FFB36B"))
        elif weather == "sunny":
            sun(c, 1750, 230)
        if weather in ("cloudy", "rain", "windy", "snow") or time == "day":
            r = random.Random(seed)
            n = 2 if weather == "sunny" else 5
            dark = weather == "rain"
            for i in range(n):
                cloud(c, r.uniform(80, BW - 300), r.uniform(70, 330), r.uniform(0.8, 1.4),
                      hexc("#C9D2DC", 245) if dark else hexc("#FFFFFF", 235))
        if setting == "beach":
            sea(c, 640, time)
        else:
            hills(c, time, 700)
            if setting == "park":
                tree(c, 330, 860, 1.1, time)
                tree(c, 1880, 820, 0.9, time)
                c.rect(1180, 800, 1500, 830, hexc("#B7794A"), r=8)   # bench
                c.rect(1200, 830, 1220, 900, hexc("#8A5A34"))
                c.rect(1460, 830, 1480, 900, hexc("#8A5A34"))
                c.rect(1180, 740, 1500, 770, hexc("#B7794A"), r=8)
            elif setting == "garden":
                house(c, 1480, 820, time)
                fence(c, 760, time)
                tree(c, 230, 880, 0.95, time)
            elif setting == "forest":
                for k, x in enumerate(range(-40, BW + 200, 230)):
                    tree(c, x, 820 + (k % 2) * 40, 0.85 + (k % 3) * 0.12, time)
            elif setting == "street":
                house(c, 200, 800, time)
                house(c, 1500, 800, time)
                c.rect(0, 900, BW, BH, hexc("#9AA3AD"))
                for x in range(0, BW, 220):
                    c.rect(x + 40, 1030, x + 160, 1045, hexc("#FFFFFF"))
            if weather == "snow":
                pts = [(0, BH)] + [(x, 820 + 18 * math.sin(x / 200.0)) for x in range(0, BW + 40, 40)] + [(BW, BH)]
                c.poly(pts, hexc("#F7FBFF"))
            elif setting != "street":
                flowers(c, 880, 1150, 26, seed, time)
    for p in props:
        if p in PROP_SPOT:
            prop(c, p, *PROP_SPOT[p], time=time)
    return c.final()


# ---------------------------------------------------------------- characters
SKIN_LINA = hexc("#C98E63")
SKIN_ADAMS = hexc("#E2B086")
HAIR = hexc("#3A2415")
OUT = hexc("#3A2A20")


def _face(c, cx, cy, r, skin, happy=True):
    c.circle(cx, cy, r, skin)
    for ex in (-0.36, 0.36):
        x = cx + ex * r
        c.ellipse(x, cy + 0.12 * r, 0.14 * r, 0.18 * r, hexc("#2B1B12"))
        c.circle(x + 0.05 * r, cy + 0.04 * r, 0.06 * r, hexc("#FFFFFF"))
        c.circle(x - 0.04 * r, cy + 0.2 * r, 0.025 * r, hexc("#FFFFFF"))
    for ex in (-0.6, 0.6):
        c.ellipse(cx + ex * r, cy + 0.42 * r, 0.16 * r, 0.09 * r, hexc("#FF7F9B", 120))
    if happy:
        c.chord(cx, cy + 0.36 * r, 0.22 * r, 0.2 * r, 0, 180, hexc("#8C2F3A"))
        c.chord(cx, cy + 0.36 * r, 0.22 * r, 0.06 * r, 0, 180, hexc("#FFFFFF"))
    else:
        c.arc(cx, cy + 0.42 * r, 0.16 * r, 0.1 * r, 200, 340, hexc("#8C2F3A"), 5)


def lina():
    """Lina: curly puffs with pink ties, purple dress."""
    W, H = 420, 640
    c = Canvas(W, H)
    cx = 210
    c.rect(168, 500, 196, 600, SKIN_LINA, r=12)
    c.rect(224, 500, 252, 600, SKIN_LINA, r=12)
    c.ellipse(178, 608, 34, 18, hexc("#E85D8A"))
    c.ellipse(242, 608, 34, 18, hexc("#E85D8A"))
    c.line([(158, 350), (102, 470)], SKIN_LINA, 28)
    c.line([(262, 350), (318, 470)], SKIN_LINA, 28)
    c.circle(100, 476, 20, SKIN_LINA)
    c.circle(320, 476, 20, SKIN_LINA)
    c.poly([(150, 320), (270, 320), (318, 528), (102, 528)], hexc("#9B6BD3"))
    c.rect(150, 312, 270, 360, hexc("#9B6BD3"), r=20)
    c.chord(210, 322, 46, 30, 0, 180, hexc("#FFFFFF"))
    for k in range(3):
        c.circle(150 + k * 60, 470, 9, hexc("#FFFFFF", 200))
    c.rect(196, 290, 224, 330, SKIN_LINA, r=8)
    # hair behind head + puffs
    c.circle(cx, 200, 122, HAIR)
    for px in (88, 332):
        c.circle(px, 140, 58, HAIR)
        c.circle(px + (12 if px < cx else -12), 182, 16, hexc("#FF6FA3"))
    _face(c, cx, 215, 108, SKIN_LINA)
    c.chord(cx, 175, 112, 80, 180, 360, HAIR)
    for k in range(5):
        c.circle(130 + k * 40, 120 + (k % 2) * 6, 26, HAIR)
    return c.final()


def adams():
    """Adams: short curly hair, blue shirt with a yellow star, navy shorts."""
    W, H = 420, 640
    c = Canvas(W, H)
    cx = 210
    c.rect(168, 520, 196, 600, SKIN_ADAMS, r=12)
    c.rect(224, 520, 252, 600, SKIN_ADAMS, r=12)
    c.ellipse(178, 608, 36, 18, hexc("#2E6FA8"))
    c.ellipse(242, 608, 36, 18, hexc("#2E6FA8"))
    c.rect(150, 470, 270, 540, hexc("#2C3E66"), r=14)
    c.line([(158, 350), (104, 465)], SKIN_ADAMS, 28)
    c.line([(262, 350), (316, 465)], SKIN_ADAMS, 28)
    c.circle(102, 472, 20, SKIN_ADAMS)
    c.circle(318, 472, 20, SKIN_ADAMS)
    c.rect(145, 318, 275, 490, hexc("#3E8EDE"), r=34)
    c.line([(150, 340), (110, 420)], hexc("#3E8EDE"), 30)
    c.line([(270, 340), (310, 420)], hexc("#3E8EDE"), 30)
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        r = 34 if k % 2 == 0 else 15
        pts.append((cx + math.cos(a) * r, 405 + math.sin(a) * r))
    c.poly(pts, hexc("#FFD23F"))
    c.rect(196, 290, 224, 330, SKIN_ADAMS, r=8)
    _face(c, cx, 215, 104, SKIN_ADAMS)
    for k in range(7):
        c.circle(122 + k * 29, 128 + abs(3 - k) * 7, 30, HAIR)
    c.chord(cx, 170, 106, 66, 185, 355, HAIR)
    c.circle(112, 175, 22, HAIR)
    c.circle(308, 175, 22, HAIR)
    return c.final()


def milo():
    """Milo the orange cat, sitting."""
    W, H = 340, 340
    c = Canvas(W, H)
    org, dark = hexc("#F39A3D"), hexc("#D9762A")
    c.line([(250, 300), (310, 250), (300, 180)], org, 26)
    c.ellipse(170, 255, 105, 80, org)
    c.ellipse(170, 280, 55, 50, hexc("#FFE2C2"))
    c.circle(170, 140, 82, org)
    c.poly([(100, 100), (112, 22), (160, 76)], org)
    c.poly([(240, 100), (228, 22), (180, 76)], org)
    c.poly([(112, 88), (118, 46), (146, 76)], hexc("#FFB6C1"))
    c.poly([(228, 88), (222, 46), (194, 76)], hexc("#FFB6C1"))
    for k in range(3):
        c.line([(140 + k * 30, 70), (140 + k * 30, 92)], dark, 8)
    for ex in (140, 200):
        c.ellipse(ex, 140, 12, 17, hexc("#2B1B12"))
        c.circle(ex + 4, 133, 5, hexc("#FFFFFF"))
    c.poly([(162, 168), (178, 168), (170, 178)], hexc("#E86A7A"))
    c.arc(160, 182, 10, 8, 0, 180, hexc("#5A3A2A"), 4)
    c.arc(180, 182, 10, 8, 0, 180, hexc("#5A3A2A"), 4)
    for s in (-1, 1):
        for k in range(2):
            c.line([(170 + s * 30, 175 + k * 10), (170 + s * 95, 165 + k * 18)], hexc("#FFFFFF", 200), 3)
    c.ellipse(130, 325, 30, 14, org)
    c.ellipse(210, 325, 30, 14, org)
    return c.final()


CHARACTERS = {"lina": lina, "adams": adams, "milo": milo}


# ---------------------------------------------------------------- overlays
def weather_layer(kind, seed=5):
    """Tall/wide RGBA layer for scrolling weather; None if no layer."""
    r = random.Random(seed)
    if kind == "rain":
        im = Image.new("RGBA", (FW, FH * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for _ in range(420):
            x, y = r.uniform(0, FW), r.uniform(0, FH)
            for yy in (y, y + FH):
                d.line([(x, yy), (x - 14, yy + 46)], fill=(210, 230, 255, 190), width=4)
        return im
    if kind == "snow":
        im = Image.new("RGBA", (FW, FH * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for _ in range(260):
            x, y, s = r.uniform(0, FW), r.uniform(0, FH), r.uniform(4, 11)
            for yy in (y, y + FH):
                d.ellipse([x - s, yy - s, x + s, yy + s], fill=(255, 255, 255, 230))
        return im
    if kind == "windy":
        im = Image.new("RGBA", (FW * 2, FH), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for _ in range(26):
            x, y = r.uniform(0, FW), r.uniform(100, 800)
            col = r.choice([(120, 190, 80, 230), (240, 170, 60, 230), (200, 110, 60, 230)])
            for xx in (x, x + FW):
                d.ellipse([xx - 18, y - 8, xx + 18, y + 8], fill=col)
            for xx in (x, x + FW):
                d.arc([xx - 220, y - 40, xx - 40, y + 40], 200, 330, fill=(255, 255, 255, 140), width=4)
        return im
    return None


def cloud_layer(seed=7):
    c = Canvas(FW * 2, 420)
    r = random.Random(seed)
    for i in range(4):
        x = (i * FW / 2) + r.uniform(0, 300)
        for xx in (x, x + FW):
            if xx < FW * 2 - 100:
                cloud(c, xx, r.uniform(80, 260), r.uniform(0.6, 1.0), hexc("#FFFFFF", 210))
    return c.final()


def word_card(word, ar=None):
    f1, f2 = font(34, "Medium"), font(84, "Bold")
    tw = f2.getlength(word)
    w = int(max(360, tw + 110))
    c = Canvas(w, 210)
    c.rect(8, 12, w - 2, 206, hexc("#000000", 50), r=36)
    c.rect(0, 0, w - 10, 196, hexc("#FFFFFF", 245), r=36)
    c.rect(0, 0, w - 10, 196, None, r=36, outline=hexc("#FFB020"), width=8)
    c.text(36, 26, "New word", f1, hexc("#7A6A9A"))
    c.text(36, 70, word, f2, hexc("#FF7A30"))
    c.circle(w - 60, 46, 22, hexc("#FFE26B"))
    return c.final()


def subtitle(text, who=None, highlight=None, maxw=1560):
    f = font(54, "Medium")
    name_col = {"lina": hexc("#9B6BD3"), "adams": hexc("#2E7CD0"), "milo": hexc("#E07A1F")}
    words = text.split()
    lines, cur = [], []
    prefix = (who.capitalize() + ":") if who and who != "narrator" else None
    for wd in words:
        trial = " ".join(([prefix] if prefix and not lines and not cur else []) + cur + [wd])
        if f.getlength(trial) > maxw and cur:
            lines.append(cur)
            cur = [wd]
        else:
            cur.append(wd)
    lines.append(cur)
    lh = 70
    h = 40 + lh * len(lines)
    widths = []
    for i, ln in enumerate(lines):
        s = " ".join(([prefix] if prefix and i == 0 else []) + ln)
        widths.append(f.getlength(s))
    w = int(max(widths) + 80)
    c = Canvas(w, h)
    c.rect(0, 0, w, h, hexc("#FFFFFF", 232), r=28)
    hl = (highlight or "").lower()
    for i, ln in enumerate(lines):
        x = (w - widths[i]) / 2
        y = 20 + i * lh
        tokens = ([prefix] if prefix and i == 0 else []) + ln
        for j, tok in enumerate(tokens):
            col = hexc("#2D2A3E")
            if prefix and i == 0 and j == 0:
                col = name_col.get(who, col)
            elif hl and tok.lower().strip(".,!?;:'\"").startswith(hl):
                col = hexc("#FF6A1F")
            c.text(x, y, tok, f, col)
            x += f.getlength(tok + " ")
    return c.final()


def title_card(story_title, subtitle_text, time="night"):
    bg = background("park", time, "sunny", seed=11, show_moon=False).crop((96, 54, 96 + FW, 54 + FH))
    c = Canvas(FW, FH)
    c.paste(bg, 0, 0)
    c.rect(0, 0, FW, FH, hexc("#0B1030", 90))
    moon(c, 960, 250, 110)
    c.text(960, 470, "Moon Tales Kids", font(110, "Bold"), hexc("#FFE680"), anchor="mm",
           stroke=6, stroke_fill=hexc("#2B2350"))
    c.text(960, 610, story_title, font(80, "SemiBold"), hexc("#FFFFFF"), anchor="mm",
           stroke=5, stroke_fill=hexc("#2B2350"))
    c.text(960, 715, subtitle_text, font(52, "Medium"), hexc("#CFE4FF"), anchor="mm",
           stroke=4, stroke_fill=hexc("#2B2350"))
    return c.final()


def thumbnail(story_title, big_word, setting, time, weather, props, chars):
    bg = background(setting, time, weather, props, seed=21).resize((1408, 792), Image.LANCZOS)
    bg = bg.crop((64, 36, 64 + 1280, 36 + 720))
    c = Canvas(1280, 720)
    c.paste(bg, 0, 0)
    c.rect(0, 0, 1280, 720, hexc("#FFFFFF", 30))
    xs = [700, 960] if len(chars) > 1 else [880]
    for name, x in zip(chars[:2], xs):
        im = CHARACTERS[name]()
        im = im.resize((int(im.width * 0.95), int(im.height * 0.95)), Image.LANCZOS)
        c.paste(im, x - im.width / 2, 720 - im.height + 40)
    words = story_title.split()
    # title text, 2–3 lines, big and outlined
    f = font(86, "Bold")
    lines, cur = [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if f.getlength(t) > 620 and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = t
    lines.append(cur)
    y = 70
    for ln in lines[:3]:
        c.text(50, y, ln, f, hexc("#FFFFFF"), stroke=9, stroke_fill=hexc("#2B2350"))
        y += 100
    c.rect(46, y + 20, 46 + font(56, "Bold").getlength(big_word) + 70, y + 120, hexc("#FF7A30"), r=26)
    c.text(81, y + 30, big_word, font(56, "Bold"), hexc("#FFFFFF"))
    c.rect(40, 600, 430, 685, hexc("#2B2350"), r=24)
    c.text(70, 615, "Learn English!", font(46, "SemiBold"), hexc("#FFE680"))
    moon(c, 1200, 80, 42)
    return c.final().convert("RGB")

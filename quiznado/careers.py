"""QuizNado07 'Who am I? — career path': clubs appear one by one (colour badges, NOT real crests), guess the player.
python3 careers.py short OUT.mp4   -> test Short: hardest path first (hook), 2 warm-ups with answers, hardest again NO answer
"""
import sys, os, math
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from weights import Seg, say, render, txt, bar, fit_font, RED, SOFT
from render import F, tick, ding, whoosh, ease, YELLOW, WHITE, DEEP
from legends import jersey

# club badge = club colours (stripes) + short name — generic design, never the real crest
CLUBS = {
    "SANTOS": ((255, 255, 255), (20, 20, 20), "SAN"), "BARCELONA": ((0, 77, 152), (165, 0, 68), "BAR"),
    "PSG": ((0, 40, 90), (218, 41, 28), "PSG"), "AL HILAL": ((0, 90, 170), (255, 255, 255), "HIL"),
    "SPORTING CP": ((0, 128, 64), (255, 255, 255), "SCP"), "MAN UNITED": ((218, 41, 28), (20, 20, 20), "MUN"),
    "REAL MADRID": ((255, 255, 255), (212, 175, 55), "RMA"), "JUVENTUS": ((20, 20, 20), (255, 255, 255), "JUV"),
    "AL NASSR": ((255, 214, 0), (0, 50, 130), "NAS"), "MONACO": ((220, 30, 40), (255, 255, 255), "MON"),
    "ARSENAL": ((220, 30, 40), (255, 255, 255), "ARS"), "NY RED BULLS": ((0, 40, 90), (220, 30, 40), "NYR"),
}
PLAYERS = {
    "NEYMAR": (["SANTOS", "BARCELONA", "PSG", "AL HILAL", "SANTOS"], ((255, 214, 0), (0, 150, 70), (0, 90, 60), None), "NEYMAR JR", "10"),
    "RONALDO": (["SPORTING CP", "MAN UNITED", "REAL MADRID", "JUVENTUS", "MAN UNITED", "AL NASSR"],
                ((200, 16, 46), (0, 100, 50), (255, 255, 255), None), "RONALDO", "7"),
    "HENRY": (["MONACO", "JUVENTUS", "ARSENAL", "BARCELONA", "NY RED BULLS", "ARSENAL"],
              ((0, 35, 149), (0, 35, 149), (255, 255, 255), None), "HENRY", "12"),
}
SPOKEN = {"PSG": "P S G", "NY RED BULLS": "New York Red Bulls", "MAN UNITED": "Manchester United", "SPORTING CP": "Sporting"}

class GP:
    portrait = True; W, H = 1080, 1920; chip_y = 405
    timer = (180, 1700, 1000, 1735); count = (95, 1717, 50)
    jbox = (360, 655, 720, 1035)
    slots = [(200, 1190), (540, 1190), (880, 1190), (880, 1470), (540, 1470), (200, 1470)]
    r = 100

_bcache = {}
def badge(club, r):
    if (club, r) in _bcache: return _bcache[(club, r)]
    c1, c2, ab = CLUBS[club]; S = 2; R = r * S; im = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
    st = Image.new("RGBA", (2 * R, 2 * R), c1 + (255,)); d = ImageDraw.Draw(st)
    for k in range(5): x = 2 * R * (0.1 + k * 0.2); d.rectangle([x, 0, x + 2 * R * 0.1, 2 * R], fill=c2 + (255,))
    m = Image.new("L", (2 * R, 2 * R), 0); ImageDraw.Draw(m).ellipse([0, 0, 2 * R - 1, 2 * R - 1], fill=255); st.putalpha(m)
    sh = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse([10, 16, 2 * R - 1, 2 * R - 1], fill=(20, 0, 50, 110))
    im.alpha_composite(sh); im.alpha_composite(st); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, 2 * R - 1, 2 * R - 1], outline=WHITE, width=8 * S)
    d.ellipse([R * 0.42, R * 0.62, R * 1.58, R * 1.38], fill=(255, 255, 255, 235))
    d.text((R, R + 2), ab, font=F(int(R * 0.42)), fill=DEEP, anchor="mm")
    im = im.resize((2 * r, 2 * r), Image.LANCZOS); _bcache[(club, r)] = im; return im

def arrow(d, a, b, r):
    (x0, y0), (x1, y1) = a, b; L = math.hypot(x1 - x0, y1 - y0); ux, uy = (x1 - x0) / L, (y1 - y0) / L
    sx, sy, ex, ey = x0 + ux * (r + 12), y0 + uy * (r + 12), x1 - ux * (r + 22), y1 - uy * (r + 22)
    d.line([(sx, sy), (ex, ey)], fill=YELLOW, width=12)
    px, py = -uy, ux; d.polygon([(ex + ux * 26, ey + uy * 26), (ex + px * 20, ey + py * 20), (ex - px * 20, ey - py * 20)], fill=YELLOW)

def draw_path(im, g, clubs, shown, t_pop=None):
    """shown: how many badges are visible; t_pop: (index, age) of the badge popping in"""
    d = ImageDraw.Draw(im)
    for i in range(min(shown, len(clubs)) - 1): arrow(d, g.slots[i], g.slots[i + 1], g.r)
    for i in range(min(shown, len(clubs))):
        sc = 1.0
        if t_pop and t_pop[0] == i: sc = 0.4 + 0.6 * ease(min(1, t_pop[1] / 0.25)) + 0.08 * math.sin(min(1, t_pop[1] / 0.25) * math.pi)
        r = int(g.r * sc); b = badge(clubs[i], g.r).resize((2 * r, 2 * r)) if sc != 1 else badge(clubs[i], g.r)
        cx, cy = g.slots[i]; im.alpha_composite(b, (int(cx - r), int(cy - r)))
        if sc >= 0.99:
            f = fit_font(d, clubs[i], 250, 34)
            d.text((cx, cy + g.r + 30), clubs[i], font=f, fill=WHITE, anchor="mm", stroke_width=4, stroke_fill=DEEP)

def draw_jersey(im, g, key, reveal_p):
    clubs, kit, name, num = PLAYERS[key]; x0, y0, x1, y1 = g.jbox; w, h = x1 - x0, y1 - y0
    p = max(0.0, min(1.0, reveal_p)); sx = abs(math.cos(math.pi * p))
    j = jersey(w, h, kit, name, num, mystery=(p < 0.5))
    if sx < 0.999: j = j.resize((max(2, int(w * max(0.04, sx))), h))
    im.alpha_composite(j, (int((x0 + x1) / 2 - j.width / 2), y0))

def banner(im, g, text, t, dur):
    if t >= dur: return
    a = min(1, (dur - t) / 0.25); lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    f = F(80); w = d.textlength(text, font=f) + 90; cy = 850
    d.rounded_rectangle([g.W / 2 - w / 2, cy - 72, g.W / 2 + w / 2, cy + 72], radius=34, fill=(254, 44, 85), outline=WHITE, width=6)
    d.text((g.W / 2, cy), text, font=f, fill=WHITE, anchor="mm")
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a))); im.alpha_composite(lay)

def player_seg(g, key, chip, *, think=5, reveal=True, instant=False, intro=None, hook=None, q_text="Who am I?"):
    clubs, kit, name, num = PLAYERS[key]; n = len(clubs); snd = []
    read = ", ".join(SPOKEN.get(c, c.title()) for c in clubs)
    vd = say(snd, 0.15, intro or f"{read}. Who am I?")
    gap = 0.0 if instant else max(0.45, min(0.75, (vd - 0.6) / n)); pops = [0.3 + i * gap for i in range(n)]
    if not instant:
        for p_ in pops: snd.append((p_, whoosh() * 0.5))
    t_th = max(vd + 0.3, (pops[-1] + 0.4) if not instant else 0.0)
    if instant: think = max(think, int(math.ceil(vd + 0.4))); t_th = 0.0
    for s in range(think): snd.append((t_th + s, tick() * (1.4 if s >= think - 3 else 1)))
    t_rev = t_th + think
    if reveal:
        snd.append((t_rev, ding())); rv = say(snd, t_rev + 0.4, f"{name.title()}!"); dur = t_rev + max(2.0, rv + 0.8)
    else: dur = t_rev
    def draw(im, t):
        shown = n if instant else sum(1 for p_ in pops if t >= p_)
        pop = None
        if not instant and shown and t - pops[shown - 1] < 0.25: pop = (shown - 1, t - pops[shown - 1])
        rp = (t - t_rev) / 0.4 if (reveal and t >= t_rev) else 0.0
        draw_jersey(im, g, key, rp)
        if reveal and t >= t_rev + 0.2:
            txt(im, (g.W / 2, 520), name + "!", 84, YELLOW, 8); txt(im, (g.W / 2, 605), "Did you get it?", 50, WHITE, 5)
        else:
            txt(im, (g.W / 2, 520), "WHO AM I?", 96, YELLOW, 9); txt(im, (g.W / 2, 605), "I played for all these clubs", 48, WHITE, 5)
        draw_path(im, g, clubs, shown, pop)
        if t >= t_th and t < t_rev or (not reveal and t >= t_th):
            left = min(think, max(0.0, t_rev - t)); bar(im, g, left / think, max(1, math.ceil(left)))
        if hook: banner(im, g, hook[0], t, hook[1])
    def key_(t):
        if hook and t < hook[1]: return None
        if not instant and t < pops[-1] + 0.3: return None
        if t < t_th: return "a"
        if t < t_rev: return ("c", int((t - t_th) * 10))
        return ("r", min(20, int((t - t_rev) * 20)))
    return Seg(dur, draw, key_, snd, chip)

def make_short(out):
    g = GP(); g.footer = ""; segs = []
    segs.append(player_seg(g, "HENRY", "THE HARD ONE", think=1, reveal=False, instant=True, hook=("ONLY REAL FANS KNOW", 2.6),
                           intro="Only real football fans know this one! Two quick ones first!"))
    segs.append(player_seg(g, "NEYMAR", "WARM-UP 1/2", think=4))
    segs.append(player_seg(g, "RONALDO", "WARM-UP 2/2", think=4))
    segs.append(player_seg(g, "HENRY", "THE HARD ONE", think=6, reveal=False,
                           intro="Now the hard one! Monaco, Juventus, Arsenal, Barcelona, New York Red Bulls, Arsenal. Who am I?"))
    snd = []; d = say(snd, 0.1, "Who is it? Comment the name! And subscribe for more football quizzes!") + 0.4
    def d_end(im, t):
        draw_jersey(im, g, "HENRY", 0); draw_path(im, g, PLAYERS["HENRY"][0], 6)
        im.alpha_composite(Image.new("RGBA", im.size, (20, 8, 50, 190)))
        txt(im, (g.W / 2, 860), "Comment the name!", 92, YELLOW, 9); txt(im, (g.W / 2, 970), "Only real fans know it", 60, WHITE, 6)
        dd = ImageDraw.Draw(im); pulse = 1 + 0.04 * math.sin(t * 6); w, h = 720 * pulse, 130 * pulse; y = 1150
        dd.rounded_rectangle([g.W / 2 - w / 2, y - h / 2, g.W / 2 + w / 2, y + h / 2], radius=65, fill=RED, outline=WHITE, width=5)
        dd.text((g.W / 2, y), "SUBSCRIBE & LIKE", font=F(60), fill=WHITE, anchor="mm")
    segs.append(Seg(max(3.6, d), d_end, lambda t: ("e", int(t * 10) % 11), snd, "QuizNado07"))
    total = render(segs, g, out); print("careers short", round(total, 1), "s", flush=True)

if __name__ == "__main__":
    if sys.argv[1] == "short": make_short(sys.argv[2])

"""QuizNado07 'How many triangles / squares?' — line figures, A/B/C, every shape lights up one by one.
Counts are computed by brute force from the drawn segments (never typed by hand).
python3 shapes.py check                          -> verify the counter on known figures
python3 shapes.py long   OUT_DIR PREFIX         -> 24 levels, 10+ min, thumbnail, answers
python3 shapes.py teaser OUT.mp4 THUMB          -> Short (same time as the long video)
python3 shapes.py frames OUT_DIR
"""
import sys, os, math, random, json, itertools
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import F, user_logo, tick, ding, whoosh, ease, shadowed, YELLOW, WHITE, DEEP
from weights import Seg, say, render, txt, bar, card, end_screen_seg, TIERS, RED, SOFT
from findnum import badge_next, hook_banner
from oddemoji import progress
from countfast import options, geo

PAPER = (252, 240, 246); INK = (40, 22, 90); PINK = (254, 44, 85); EPS = 1e-7

# ---------------- figures (unit square coords) ----------------
def fan(p, h):
    A = (0.5, 0.06); L, R, y0 = 0.06, 0.94, 0.94; segs = []
    for k in range(p): segs.append((A, (L + (R - L) * k / (p - 1), y0)))
    for j in range(1, h + 1):
        y = A[1] + (y0 - A[1]) * j / h; f = (y - A[1]) / (y0 - A[1])
        segs.append(((0.5 + (L - 0.5) * f, y), (0.5 + (R - 0.5) * f, y)))
    return segs

def grid(n, m, removed=()):
    c = 0.88 / max(n, m); x0 = 0.5 - n * c / 2; y0 = 0.5 - m * c / 2; segs = []
    for i in range(n):
        for j in range(m + 1):
            if ("h", i, j) not in removed: segs.append(((x0 + i * c, y0 + j * c), (x0 + (i + 1) * c, y0 + j * c)))
    for i in range(n + 1):
        for j in range(m):
            if ("v", i, j) not in removed: segs.append(((x0 + i * c, y0 + j * c), (x0 + i * c, y0 + (j + 1) * c)))
    return segs

def grid_removed(n, m, k, seed):
    rnd = random.Random(seed); inner = [("h", i, j) for i in range(n) for j in range(1, m)] + [("v", i, j) for i in range(1, n) for j in range(m)]
    return grid(n, m, set(rnd.sample(inner, k)))

def square(a=0.06, b=0.94): return [((a, a), (b, a)), ((b, a), (b, b)), ((b, b), (a, b)), ((a, b), (a, a))]
def sqdiag(): return square() + [((0.06, 0.06), (0.94, 0.94)), ((0.94, 0.06), (0.06, 0.94))]
def unionjack(): return sqdiag() + [((0.5, 0.06), (0.5, 0.94)), ((0.06, 0.5), (0.94, 0.5))]

def trigrid(n):
    A, B, C = (0.5, 0.07), (0.05, 0.93), (0.95, 0.93); lerp = lambda p, q, t: (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
    segs = [(A, B), (B, C), (C, A)]
    for k in range(1, n):
        t = k / n
        segs += [(lerp(A, B, t), lerp(A, C, t)), (lerp(B, A, t), lerp(B, C, t)), (lerp(C, A, t), lerp(C, B, t))]
    return segs

def star(pentagon=False):
    P = [(0.5 + 0.46 * math.cos(math.radians(-90 + 72 * k)), 0.53 + 0.46 * math.sin(math.radians(-90 + 72 * k))) for k in range(5)]
    segs = [(P[k], P[(k + 2) % 5]) for k in range(5)]
    if pentagon: segs += [(P[k], P[(k + 1) % 5]) for k in range(5)]
    return segs

def rect2diag():
    a, b, y0, y1 = 0.04, 0.96, 0.26, 0.74; m = 0.5
    return [((a, y0), (b, y0)), ((a, y1), (b, y1)), ((a, y0), (a, y1)), ((b, y0), (b, y1)), ((m, y0), (m, y1)),
            ((a, y0), (m, y1)), ((m, y0), (a, y1)), ((m, y0), (b, y1)), ((b, y0), (m, y1))]

def nested(levels):
    pts = [(0.05, 0.05), (0.95, 0.05), (0.95, 0.95), (0.05, 0.95)]; segs = []
    for _ in range(levels):
        segs += [(pts[k], pts[(k + 1) % 4]) for k in range(4)]
        pts = [((pts[k][0] + pts[(k + 1) % 4][0]) / 2, (pts[k][1] + pts[(k + 1) % 4][1]) / 2) for k in range(4)]
    return segs

def diamond_grid(): return grid(2, 2) + [((0.5, 0.06), (0.94, 0.5)), ((0.94, 0.5), (0.5, 0.94)), ((0.5, 0.94), (0.06, 0.5)), ((0.06, 0.5), (0.5, 0.06))]

# ---------------- counting ----------------
def _key(p): return (round(p[0], 6), round(p[1], 6))

def analyse(segs):
    pts = {}
    def add(p): pts.setdefault(_key(p), p)
    for a, b in segs: add(a); add(b)
    for (a, b), (c, d) in itertools.combinations(segs, 2):
        r = (b[0] - a[0], b[1] - a[1]); s = (d[0] - c[0], d[1] - c[1]); den = r[0] * s[1] - r[1] * s[0]
        if abs(den) < 1e-12: continue
        t = ((c[0] - a[0]) * s[1] - (c[1] - a[1]) * s[0]) / den; u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
        if -EPS <= t <= 1 + EPS and -EPS <= u <= 1 + EPS: add((a[0] + t * r[0], a[1] + t * r[1]))
    P = list(pts.values())
    # merged maximal segments per line
    lines = {}
    for a, b in segs:
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy); dx, dy = dx / L, dy / L
        if dx < -EPS or (abs(dx) < EPS and dy < 0): dx, dy = -dx, -dy
        off = round(dx * a[1] - dy * a[0], 6); k = (round(dx, 6), round(dy, 6), off)
        t0, t1 = sorted((dx * a[0] + dy * a[1], dx * b[0] + dy * b[1])); lines.setdefault(k, []).append([t0, t1])
    for k, iv in lines.items():
        iv.sort(); m = [iv[0]]
        for s, e in iv[1:]:
            if s <= m[-1][1] + 1e-6: m[-1][1] = max(m[-1][1], e)
            else: m.append([s, e])
        lines[k] = m
    n = len(P); cov = [[False] * n for _ in range(n)]
    for i, j in itertools.combinations(range(n), 2):
        a, b = P[i], P[j]; dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy); dx, dy = dx / L, dy / L
        if dx < -EPS or (abs(dx) < EPS and dy < 0): dx, dy = -dx, -dy
        k = (round(dx, 6), round(dy, 6), round(dx * a[1] - dy * a[0], 6))
        if k not in lines:
            continue
        ta, tb = dx * a[0] + dy * a[1], dx * b[0] + dy * b[1]
        if any(s - 1e-6 <= min(ta, tb) and max(ta, tb) <= e + 1e-6 for s, e in lines[k]): cov[i][j] = cov[j][i] = True
    return P, cov

def area(poly): return abs(sum(poly[k][0] * poly[(k + 1) % len(poly)][1] - poly[(k + 1) % len(poly)][0] * poly[k][1] for k in range(len(poly)))) / 2

def triangles(segs):
    P, cov = analyse(segs); out = []
    for i, j, k in itertools.combinations(range(len(P)), 3):
        if cov[i][j] and cov[j][k] and cov[i][k] and area([P[i], P[j], P[k]]) > 1e-5: out.append([P[i], P[j], P[k]])
    return sorted(out, key=area)

def squares(segs):
    P, cov = analyse(segs); idx = {_key(p): i for i, p in enumerate(P)}; seen = set(); out = []
    for i in range(len(P)):
        for j in range(len(P)):
            if i == j or not cov[i][j]: continue
            v = (P[j][0] - P[i][0], P[j][1] - P[i][1]); r = _key((P[j][0] - v[1], P[j][1] + v[0])); s = _key((P[i][0] - v[1], P[i][1] + v[0]))
            if r in idx and s in idx:
                ri, si = idx[r], idx[s]
                if cov[j][ri] and cov[ri][si] and cov[si][i]:
                    f = frozenset((i, j, ri, si))
                    if f not in seen: seen.add(f); out.append([P[i], P[j], P[ri], P[si]])
    return sorted(out, key=area)

def check():
    tests = [("fan(3,1)", triangles(fan(3, 1)), 3), ("fan(4,2)", triangles(fan(4, 2)), 12), ("fan(5,3)", triangles(fan(5, 3)), 30),
             ("sqdiag", triangles(sqdiag()), 8), ("trigrid2", triangles(trigrid(2)), 5), ("trigrid3", triangles(trigrid(3)), 13),
             ("trigrid4", triangles(trigrid(4)), 27), ("star", triangles(star()), 10), ("star+pent", triangles(star(True)), 35),
             ("grid2", squares(grid(2, 2)), 5), ("grid3", squares(grid(3, 3)), 14), ("grid4", squares(grid(4, 4)), 30),
             ("grid5x4", squares(grid(5, 4)), 40), ("grid3x2", squares(grid(3, 2)), 8)]
    ok = True
    for name, got, want in tests:
        print(f"{name:10s} got {len(got):3d} want {want:3d} {'OK' if len(got) == want else 'FAIL'}"); ok &= len(got) == want
    print("ALL OK" if ok else "SOME FAILED"); return ok

# ---------------- levels ----------------
PLAN = [  # (kind, figure, tier, think)
    ("tri", lambda: fan(3, 1), 0, 7), ("sq", lambda: grid(2, 2), 0, 7), ("tri", lambda: fan(4, 1), 0, 8),
    ("sq", lambda: grid(3, 2), 0, 8), ("tri", lambda: trigrid(2), 0, 8),
    ("sq", lambda: grid(3, 1), 1, 6), ("tri", lambda: sqdiag(), 1, 6), ("tri", lambda: fan(2, 3), 1, 6),       # speed round
    ("sq", lambda: grid(3, 3), 2, 12), ("tri", lambda: unionjack(), 2, 13), ("tri", lambda: fan(4, 2), 2, 12),
    ("sq", lambda: grid(4, 3), 2, 13), ("tri", lambda: trigrid(3), 2, 14), ("sq", lambda: diamond_grid(), 2, 14),
    ("tri", lambda: star(), 3, 16), ("sq", lambda: grid(4, 4), 3, 16), ("tri", lambda: rect2diag(), 3, 17),
    ("sq", lambda: grid_removed(4, 4, 4, 7), 3, 17), ("tri", lambda: fan(5, 3), 4, 19), ("sq", lambda: grid(5, 4), 4, 19),
    ("tri", lambda: trigrid(4), 4, 20), ("sq", lambda: grid_removed(5, 5, 6, 3), 5, 23), ("tri", lambda: nested(3), 5, 23),
    ("tri", lambda: star(True), 5, 25),
]
SPEED = (5, 6, 7)

def build_levels():
    rnd = random.Random(77); lvs = []
    for kind, fig, tier, th in PLAN:
        segs = fig(); shapes = triangles(segs) if kind == "tri" else squares(segs); c = len(shapes)
        wrong = rnd.sample(sorted({c - 3, c - 2, c - 1, c + 1, c + 2, c + 3} - {0, c} - {x for x in range(-3, 1)}), 2)
        opts = [c] + wrong; rnd.shuffle(opts)
        lvs.append({"kind": kind, "segs": segs, "shapes": shapes, "count": c, "options": opts, "answer": "ABC"[opts.index(c)]})
    return lvs

# ---------------- drawing ----------------
WORD = {"tri": ("TRIANGLES", "triangles"), "sq": ("SQUARES", "squares")}
_bc = {}
def fig_img(box, lv, hi=None):
    key = (box, id(lv), hi)
    if key in _bc: return _bc[key]
    x0, y0, x1, y1 = box; W, H = x1 - x0, y1 - y0; pad = 46; S = min(W, H) - 2 * pad; ox, oy = (W - S) / 2, (H - S) / 2
    M = lambda p: (ox + p[0] * S, oy + p[1] * S)
    if (box, id(lv), None) in _bc and hi is not None: im = _bc[(box, id(lv), None)].copy()
    else:
        im = Image.new("RGBA", (W + 40, H + 40), (0, 0, 0, 0)); shadowed(im, (0, 0, W, H), 30, PAPER, blur=14, off=8, alpha=90)
        d = ImageDraw.Draw(im); lw = max(7, int(S / 95))
        for a, b in lv["segs"]: d.line([M(a), M(b)], fill=INK, width=lw)
        for a, b in lv["segs"]:
            for p in (a, b): r = lw / 2; d.ellipse([M(p)[0] - r, M(p)[1] - r, M(p)[0] + r, M(p)[1] + r], fill=INK)
        if hi is None: _bc[key] = im; return im
    poly = [M(p) for p in lv["shapes"][hi]]
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.polygon(poly, fill=(250, 204, 21, 150)); od.line(poly + [poly[0]], fill=PINK, width=max(8, int(S / 80)), joint="curve")
    im.alpha_composite(ov); _bc[key] = im; return im

def question(im, g, lv):
    d = ImageDraw.Draw(im); s = f"HOW MANY {WORD[lv['kind']][0]}?"; size = 84 if not g.portrait else 72
    maxw = 800 if not g.portrait else 940
    while d.textlength(s, font=F(size)) + 80 > maxw: size -= 2
    w = d.textlength(s, font=F(size)) + 70; cx, cy = g.find_xy
    shadowed(im, (cx - w / 2, cy - size * 0.8, cx + w / 2, cy + size * 0.8), 40, WHITE, blur=12, off=6, alpha=80)
    ImageDraw.Draw(im).text((cx, cy), s, font=F(size), fill=DEEP, anchor="mm")

def level_seg(g, lv, chip, *, think, intro=None, reveal=True, hold=2.2, instant=False, prog=None, badge=None,
              hook=None, hook_dur=2.4, min_intro=1.6, q_text=None):
    snd = []; W1, w1 = WORD[lv["kind"]]; c = lv["count"]
    q_text = q_text or ("Big and small count!" if lv["kind"] == "tri" else "Every size counts!")
    vd = say(snd, 0.2, intro or f"How many {w1}?")
    if not instant: snd.insert(0, (0.25, whoosh() * 0.6))
    t_think = 0.0 if instant else max(min_intro, vd + 0.4)
    if instant: think = max(think, int(math.ceil(vd + 0.5)))
    for s in range(think): snd.append((t_think + s, tick() * (1.5 if s >= think - 3 else 1)))
    t_rev = t_think + think; step = min(0.45, 6.0 / c)
    if reveal:
        for k in range(c): snd.append((t_rev + 0.2 + k * step, tick() * 0.55))
        t_done = t_rev + 0.2 + c * step; snd.append((t_done, ding()))
        rv = say(snd, t_done + 0.15, f"{c} {w1}! Answer {lv['answer']}!"); total = t_done + max(hold, rv + 0.5)
    else:
        total = t_rev; t_rev = t_done = 1e9
    def cur(t):
        if t < t_rev + 0.2: return None
        return min(c - 1, int((t - t_rev - 0.2) / step))
    def draw(im, t):
        pop = 1.0 if instant else ease(min(1, t / 0.3)); h = cur(t) if t < t_done else None
        a = fig_img(g.box, lv, h)
        if pop < 1: a = a.copy(); a.putalpha(a.getchannel("A").point(lambda v: int(v * pop)))
        im.alpha_composite(a, (g.box[0], g.box[1]))
        question(im, g, lv); options(im, g, lv, "rev" if t >= t_done else None)
        if prog: progress(im, g, *prog)
        if badge: badge_next(im, g, badge)
        if t >= t_rev:
            k = (cur(t) or 0) + 1 if t >= t_rev + 0.2 else 0
            txt(im, g.hint_xy, f"{k}..." if t < t_done else f"{c} {W1}!", 60, YELLOW, 6)
        elif t >= t_think:
            txt(im, g.hint_xy, q_text, 52, YELLOW, 6)
            left = max(0.0, (t_rev if reveal else total) - t); bar(im, g, min(1, left / think), max(1, math.ceil(left)))
        if hook: hook_banner(im, g, hook, t, hook_dur)
    def key(t):
        if t < 0.35 and not instant: return None
        if hook and t < hook_dur: return None
        if t >= t_done: return "done"
        if t >= t_rev: return ("r", cur(t))
        if t < t_think: return "a"
        return ("c", int((t - t_think) * 10))
    return Seg(total, draw, key, snd, chip)

# ---------------- long video ----------------
def make_long(outdir, prefix):
    g = geo(False); lvs = build_levels(); N = len(lvs); segs = []; last = lvs[-1]
    segs.append(level_seg(g, last, f"LEVEL {N} / {N} • IMPOSSIBLE", think=1, reveal=False, instant=True,
                          hook="MOST PEOPLE GET IT WRONG", hook_dur=2.6,
                          intro=f"How many triangles? Most people get it wrong. The answer is at the very end!"))
    for i, (lv, (kind, fig, tier, th)) in enumerate(zip(lvs, PLAN)):
        name, col = TIERS[tier]; chip = f"LEVEL {i + 1} / {N} • " + ("SPEED ROUND" if i in SPEED else name)
        if i == 0:
            segs.append(card(g, [("Let's start easy!", 90, WHITE), ("Count ALL the shapes", 64, SOFT)],
                             "Let's start easy! Count all the shapes, big and small!", 1.8, 0.1, chip))
        elif i == SPEED[0]:
            segs.append(card(g, [("SPEED ROUND!", 120, YELLOW), ("3 levels • 6 seconds each", 70, WHITE)],
                             "Speed round! Three levels, only six seconds each. Go!", 2.0, 0.1, chip))
        elif i not in SPEED:
            segs.append(card(g, [(f"LEVEL {i + 1}", 120, YELLOW), (name, 84, col)], f"Level {i + 1}. {name.lower()}.", 1.2, 0.1, chip))
        segs.append(level_seg(g, lv, chip, think=th, hold=2.0, prog=(i, N),
                              intro=("Here is the one from the start! How many triangles?" if i == N - 1 else
                                     (f"Six seconds! How many {WORD[lv['kind']][1]}?" if i in SPEED else None))))
        if i + 1 in (5, 14):
            segs.append(card(g, [("Still perfect?", 104, YELLOW), ("Type YES in the comments!", 64, WHITE)],
                             "Still perfect? Type yes in the comments!", 2.2, 0.2, chip))
        if i + 1 in (9, 18):
            segs.append(card(g, [(f"LEVEL {N} is coming...", 92, YELLOW), ("the one from the start!", 64, WHITE), ("Stay until the end!", 70, WHITE)],
                             f"Level {N} is coming. The one from the start! Stay until the end to see the answer!", 2.2, 0.2, chip))
        if i + 1 in (8, 16, 21):
            segs.append(card(g, [("Got it right?", 86, WHITE), ("SMASH LIKE", 110, YELLOW), ("and subscribe to QuizNado07", 52, SOFT)],
                             "Got it right? Smash like, and subscribe to QuizNado07!", 3, 0.4, chip))
    segs.append(card(g, [("What's your score?", 96, YELLOW), (f"___ / {N}", 124, WHITE), ("Comment it below!", 60, SOFT)],
                     f"How many did you get right out of {N}? Write your score in the comments!", 3, 0.8))
    segs.append(end_screen_seg(g))
    total = render(segs, g, f"{outdir}/{prefix}.mp4")
    json.dump([{k: v for k, v in lv.items() if k in ("kind", "count", "options", "answer")} for lv in lvs], open(f"{outdir}/{prefix}_answers.json", "w"))
    thumbnail(f"{outdir}/{prefix}_THUMBNAIL.jpg", lvs)
    print("long", round(total, 1), "s", flush=True)

# ---------------- Short ----------------
def make_teaser(out, long_thumb):
    g = geo(True); g.footer = ""; lvs = build_levels(); hi = 14; hard = lvs[hi]; chip = f"LEVEL {hi + 1} • THE STAR"
    segs = [level_seg(g, hard, chip, think=1, reveal=False, instant=True, hook="MOST PEOPLE SAY 5", hook_dur=2.6,
                      intro="How many triangles in this star? Most people say five! Two quick ones first!"),
            level_seg(g, lvs[4], "WARM-UP 1/2", think=5, hold=1.4, badge="NEXT: THE STAR"),
            level_seg(g, lvs[8], "WARM-UP 2/2", think=6, hold=1.4, badge="NEXT: THE STAR"),
            level_seg(g, hard, chip, think=7, reveal=False, q_text="No answer here...", intro="Now the star! How many triangles?")]
    th = Image.open(long_thumb).convert("RGBA"); snd = []
    d = say(snd, 0.1, "A, B or C? Comment! The answer is in the full video, out now on QuizNado07!") + 0.4
    def draw(im, t):
        im.alpha_composite(fig_img(g.box, hard), (g.box[0], g.box[1]))
        im.alpha_composite(Image.new("RGBA", im.size, (20, 8, 50, 200)))
        txt(im, (g.W / 2, 560), "A, B or C? Comment!", 76, YELLOW, 8)
        txt(im, (g.W / 2, 660), "Answer in the full video", 58, WHITE, 6)
        tw = 940; t2 = th.resize((tw, int(tw * th.height / th.width)), Image.LANCZOS)
        shadowed(im, (70, 740, 70 + tw, 740 + t2.height), 24, WHITE, blur=16, off=10, alpha=110)
        m = Image.new("L", t2.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, t2.width - 1, t2.height - 1], radius=24, fill=255)
        im.paste(t2, (70, 740), m)
        dd = ImageDraw.Draw(im); cx, cy = 70 + tw - 70, 740 + t2.height - 55
        dd.ellipse([cx - 48, cy - 48, cx + 48, cy + 48], fill=RED); dd.polygon([(cx - 15, cy - 24), (cx - 15, cy + 24), (cx + 26, cy)], fill=WHITE)
        y = 740 + t2.height + 75; p = 1 + 0.03 * math.sin(t * 6)
        dd.rounded_rectangle([g.W / 2 - 400 * p, y + 10, g.W / 2 + 400 * p, y + 115], radius=52, fill=RED, outline=WHITE, width=5)
        dd.text((g.W / 2, y + 62), "SUBSCRIBE & LIKE", font=F(58), fill=WHITE, anchor="mm")
    segs.append(Seg(max(4.0, d), draw, lambda t: ("e", int(t * 10) % 11), snd, "QuizNado07"))
    total = render(segs, g, out)
    print("teaser", round(total, 1), "s; star =", hard["count"], "answer", hard["answer"], hard["options"], flush=True)

# ---------------- thumbnail (no answer) ----------------
def thumbnail(path, lvs):
    import numpy as np
    y, x = np.mgrid[0:1080, 0:1920]; t = ((y / 1080 + x / 1920) / 2)[..., None]
    im = Image.fromarray((np.array((20, 184, 166)) * (1 - t) + np.array((88, 28, 220)) * t).astype(np.uint8), "RGB").convert("RGBA")
    im.alpha_composite(user_logo(120), (30, 25))
    box = (1000, 90, 1860, 990); im.alpha_composite(fig_img(box, lvs[-1]), box[:2])
    d = ImageDraw.Draw(im); s = "HOW MANY"; f = F(118); w = d.textlength(s, font=f) + 90
    d.rounded_rectangle([490 - w / 2, 230, 490 + w / 2, 400], radius=50, fill=WHITE); d.text((490, 315), s, font=f, fill=DEEP, anchor="mm")
    txt(im, (490, 560), "TRIANGLES?", 150, YELLOW, 13)
    txt(im, (490, 760), "Big and small!", 84, WHITE, 9)
    st = Image.new("RGBA", (560, 130), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
    sd.rounded_rectangle([0, 0, 559, 129], radius=24, fill=(220, 38, 38), outline=WHITE, width=8)
    sd.text((280, 65), "IMPOSSIBLE", font=F(84), fill=WHITE, anchor="mm")
    st = st.rotate(-8, expand=True, resample=Image.BICUBIC); im.alpha_composite(st, (1430 - st.width // 2, 80 - st.height // 2 + 10))
    im.convert("RGB").resize((1280, 720), Image.LANCZOS).save(path, quality=93)

if __name__ == "__main__":
    a = sys.argv
    if a[1] == "check": check()
    elif a[1] == "long": make_long(a[2], a[3])
    elif a[1] == "teaser": make_teaser(a[2], a[3])
    elif a[1] == "frames":
        from weights import background
        lvs = build_levels(); print([(i + 1, l["kind"], l["count"], l["answer"]) for i, l in enumerate(lvs)])
        for i, portrait in ((9, False), (23, False), (14, True)):
            g = geo(portrait); s = level_seg(g, lvs[i], f"LEVEL {i + 1}", think=PLAN[i][3], prog=None if portrait else (i, 24))
            for tt, nm in ((3.0, "ask"), (s.dur - 4.0, "mid"), (s.dur - 0.3, "rev")):
                im = background(g, s.chip); s.draw(im, tt)
                im.convert("RGB").resize((g.W // 2, g.H // 2)).save(f"{a[2]}/s_{i}_{'p' if portrait else 'l'}_{nm}.png")
        thumbnail(f"{a[2]}/thumb.jpg", lvs)

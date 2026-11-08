"""QuizNado07 'Find the number' — a hidden number in a grid of look-alike digits.
python3 findnum.py long   OUT_DIR PREFIX SEED   -> PREFIX.mp4 (24 levels, 10+ min) + 3 thumbnails + PREFIX_answers.json
python3 findnum.py teaser OUT.mp4 SEED THUMB     -> hook-first loop Short (hardest level first, 2 warm-ups, hardest again, no answer)
python3 findnum.py frames OUT_DIR                -> preview stills
"""
import sys, os, math, random, json
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import F, user_logo, tick, ding, whoosh, ease, shadowed, YELLOW, WHITE, DEEP, GREEN
from weights import (Seg, say, card, render, end_screen_seg, background, txt, bar, overlay_rect, emoji,
                     TIERS, RED, SOFT)

PAPER = (252, 228, 236); INK = (20, 20, 28); DIM = (205, 180, 192)
WORDS = "zero one two three four five six seven eight nine".split()
DIRS = {"H": (0, 1), "V": (1, 0), "D": (1, 1)}
ALL8 = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]
PAIRS = [("2", "9"), ("1", "7"), ("6", "9"), ("3", "8"), ("5", "6"), ("0", "8"), ("4", "7"), ("2", "5"), ("1", "4"), ("8", "9")]
# (grid size, allowed directions, tier, think seconds)
PLAN = ([(5, "H", 0, 8)] * 4 + [(6, "HV", 1, 10)] + [(6, "HV", 1, 6)] * 3 + [(6, "HV", 1, 10)] + [(7, "HV", 2, 17)] * 5 +
        [(8, "HVD", 3, 20)] * 5 + [(9, "HVD", 4, 22)] * 3 + [(10, "HVD", 5, 24)] * 2)
SPEED = (5, 6, 7)   # level indexes of the speed round (pattern interrupt around minute 2)
HINT = {"H": "Hidden ACROSS", "HV": "Hidden ACROSS or DOWN", "HVD": "ACROSS, DOWN or DIAGONAL"}

def count(grid, t):
    n = len(grid); L = len(t); c = 0
    for r in range(n):
        for k in range(n):
            for dr, dc in ALL8:
                er, ec = r + dr * (L - 1), k + dc * (L - 1)
                if 0 <= er < n and 0 <= ec < n and all(grid[r + dr * i][k + dc * i] == t[i] for i in range(L)): c += 1
    return c

def occurrences(grid, t):
    n = len(grid); L = len(t); out = []
    for r in range(n):
        for k in range(n):
            for dr, dc in ALL8:
                cells = [(r + dr * i, k + dc * i) for i in range(L)]
                if all(0 <= a < n and 0 <= b < n for a, b in cells) and all(grid[a][b] == t[i] for i, (a, b) in enumerate(cells)): out.append(cells)
    return out

def make_level(n, dirs, rnd, pair):
    while True:
        t = "".join(rnd.choice(pair) for _ in range(4))
        if len(set(t)) == 2 and t != t[::-1] and t[0] != "0": break
    d = rnd.choice(dirs); dr, dc = DIRS[d]
    for _ in range(200):
        g = [[rnd.choice(pair) for _ in range(n)] for _ in range(n)]
        r0 = rnd.randrange(0, n - dr * 3); c0 = rnd.randrange(0, n - dc * 3)
        plant = [(r0 + dr * i, c0 + dc * i) for i in range(4)]
        for i, (a, b) in enumerate(plant): g[a][b] = t[i]
        for _ in range(400):
            occ = [o for o in occurrences(g, t) if sorted(o) != sorted(plant)]
            if not occ: break
            free = [c for c in occ[0] if c not in plant]; a, b = rnd.choice(free)
            g[a][b] = pair[1] if g[a][b] == pair[0] else pair[0]
        if count(g, t) == 1:
            return {"n": n, "dirs": dirs, "target": t, "grid": ["".join(row) for row in g], "cells": plant, "dir": d}
    raise RuntimeError("could not build level")

def where(lv):
    (r, c) = lv["cells"][0]
    if lv["dir"] == "H": return f"row {r + 1}, going across"
    if lv["dir"] == "V": return f"column {c + 1}, going down"
    return f"on the diagonal, starting in row {r + 1}"

def spoken(t): return ", ".join(WORDS[int(ch)] for ch in t)

class G:
    def __init__(self, portrait):
        self.portrait = portrait
        if portrait:
            self.W, self.H = 1080, 1920; self.box = (90, 680, 990, 1580); self.chip_y = 405
            self.find_xy = (540, 530); self.hint_xy = (540, 630); self.q_xy = (540, 1640)
            self.timer = (180, 1690, 1000, 1725); self.count = (95, 1707, 50)
        else:
            self.W, self.H = 1920, 1080; self.box = (70, 150, 990, 1070); self.chip_y = 95
            self.find_xy = (1450, 330); self.hint_xy = (1450, 470); self.q_xy = (1450, 640)
            self.timer = (1180, 760, 1860, 800); self.count = (1110, 780, 52)

def draw_grid(im, g, lv, reveal=0.0):
    x0, y0, x1, y1 = g.box; n = lv["n"]
    shadowed(im, (x0, y0, x1, y1), 30, PAPER, blur=14, off=8, alpha=90)
    pad = 26; cs = (x1 - x0 - 2 * pad) / n; f = F(int(cs * 0.80))
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    cen = lambda a, b: (x0 + pad + (b + 0.5) * cs, y0 + pad + (a + 0.5) * cs)
    if reveal > 0:
        (a0, b0), (a1, b1) = lv["cells"][0], lv["cells"][-1]
        p0, p1 = cen(a0, b0), cen(a1, b1); w = int(cs * 0.92)
        d.line([p0, p1], fill=YELLOW + (int(235 * min(1, reveal)),), width=w)
        for p in (p0, p1): d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2], fill=YELLOW + (int(235 * min(1, reveal)),))
    hit = set(map(tuple, lv["cells"]))
    for a in range(n):
        for b in range(n):
            col = INK if (reveal <= 0 or (a, b) in hit) else DIM
            d.text(cen(a, b), lv["grid"][a][b], font=f, fill=col, anchor="mm")
    im.alpha_composite(lay)

def find_label(im, g, lv):
    s = f"FIND: {lv['target']}"; size = 120 if not g.portrait else 104
    d = ImageDraw.Draw(im); w = d.textlength(s, font=F(size)) + 80; cx, cy = g.find_xy
    shadowed(im, (cx - w / 2, cy - size * 0.75, cx + w / 2, cy + size * 0.75), 40, WHITE, blur=12, off=6, alpha=80)
    ImageDraw.Draw(im).text((cx, cy), s, font=F(size), fill=DEEP, anchor="mm")
    txt(im, g.hint_xy, HINT[lv["dirs"]], 46 if not g.portrait else 44, SOFT, 5)

def progress(im, g, cur, N):
    if g.portrait or cur is None: return
    d = ImageDraw.Draw(im); x0, y, step = 1120, 935, 29
    d.text((x0 - 10, y - 50), "YOUR PROGRESS", font=F(30), fill=SOFT, anchor="lm")
    for k in range(N - 1):
        x = x0 + k * step
        if k < cur: d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=YELLOW)
        elif k == cur: d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=WHITE, outline=YELLOW, width=4)
        else: d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(255, 255, 255, 70))
    e = emoji("🏆", 54 if cur == N - 1 else 44); im.alpha_composite(e, (int(x0 + (N - 1) * step - e.width / 2), int(y - e.height / 2)))

def level_seg(g, lv, chip, *, think, intro=None, reveal=True, hold=4.0, q_text="Can you find it?", instant=False, prog=None):
    snd = []
    vd = say(snd, 0.2, intro or f"Find {spoken(lv['target'])}!")
    if not instant: snd.insert(0, (0.25, whoosh() * 0.6))
    t_think = 0.0 if instant else max(2.4, vd + 0.4)
    if instant: think = max(think, int(math.ceil(vd + 0.5)))
    for s in range(think): snd.append((t_think + s, tick() * (1.5 if s >= think - 3 else 1)))
    t_rev = t_think + think
    if reveal:
        snd.append((t_rev, ding())); rv = say(snd, t_rev + 0.3, f"Here it is! {where(lv)}.")
        total = t_rev + max(hold, rv + 1.0)
    else:
        total = t_rev; t_rev = 1e9
    def draw(im, t):
        pop = 1.0 if instant else ease(min(1, t / 0.35))
        if pop < 1:
            lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); draw_grid(lay, g, lv)
            lay.putalpha(lay.getchannel("A").point(lambda a: int(a * pop))); im.alpha_composite(lay)
        else:
            draw_grid(im, g, lv, reveal=(t - t_rev) / 0.3 if t >= t_rev else 0.0)
        find_label(im, g, lv)
        if prog: progress(im, g, *prog)
        if t >= t_rev:
            txt(im, g.q_xy, "Here it is!", 64, YELLOW, 6)
        elif t >= t_think:
            txt(im, g.q_xy, q_text, 58 if g.portrait else 62, YELLOW, 6)
            left = max(0.0, t_rev - t if reveal else total - t); bar(im, g, left / think, max(1, math.ceil(left)))
    def key(t):
        if t < 0.4 and not instant: return None
        if t >= t_rev: return ("r", min(4, int((t - t_rev) / 0.1)))
        if t < t_think: return "a"
        return ("c", int((t - t_think) * 10))
    return Seg(total, draw, key, snd, chip)

def build_levels(seed):
    rnd = random.Random(seed); pairs = PAIRS[:]; rnd.shuffle(pairs)
    return [make_level(n, dirs, rnd, pairs[i % len(pairs)]) for i, (n, dirs, tier, th) in enumerate(PLAN)]

# ---------------- thumbnails (no answer shown) ----------------
def bright(c1, c2):
    y = np.linspace(0, 1, 1080)[:, None, None]; a = np.array(c1)[None, None, :]; b = np.array(c2)[None, None, :]
    return Image.fromarray((a * (1 - y) + b * y).repeat(1920, axis=1).astype(np.uint8), "RGB").convert("RGBA")

def thumbs(outdir, prefix, lv):
    from render import gradient
    gl = G(False)
    def grid_on(im, box):
        gl.box = box; draw_grid(im, gl, lv)
    # A: brand purple, grid + FIND label
    im = gradient(1920, 1080); im.alpha_composite(user_logo(140), (40, 30))
    grid_on(im, (1000, 90, 1860, 950))
    d = ImageDraw.Draw(im); d.rounded_rectangle([70, 250, 930, 470], radius=50, fill=WHITE)
    d.text((500, 360), f"FIND {lv['target']}", font=F(150), fill=DEEP, anchor="mm")
    txt(im, (500, 640), "CAN YOU", 140, WHITE, 10); txt(im, (500, 810), "SEE IT?", 170, YELLOW, 12)
    im.convert("RGB").resize((1280, 720), Image.LANCZOS).save(f"{outdir}/{prefix}_thumbnail.jpg", quality=92)
    # B: hot gradient, eyes emoji
    im = bright((255, 196, 0), (255, 84, 64)); im.alpha_composite(user_logo(120), (30, 25))
    grid_on(im, (1040, 120, 1840, 920))
    e = emoji("👀", 330); im.alpha_composite(e, (330, 110))
    txt(im, (520, 620), f"{lv['target']}", 230, WHITE, 14); txt(im, (520, 860), "WHERE IS IT?", 120, WHITE, 12)
    im.convert("RGB").resize((1280, 720), Image.LANCZOS).save(f"{outdir}/{prefix}_thumbnail_B.jpg", quality=92)
    # C: cool gradient, shocked face, level badge
    im = bright((40, 200, 255), (110, 60, 255)); im.alpha_composite(user_logo(120), (30, 25))
    grid_on(im, (1000, 100, 1840, 940))
    e = emoji("😱", 380); im.alpha_composite(e, (300, 140))
    txt(im, (500, 690), f"FIND {lv['target']}", 140, WHITE, 12)
    d = ImageDraw.Draw(im); d.rounded_rectangle([110, 830, 890, 980], radius=75, fill=RED)
    d.text((500, 905), "LEVEL 24", font=F(100), fill=WHITE, anchor="mm", stroke_width=4, stroke_fill=(120, 20, 20))
    im.convert("RGB").resize((1280, 720), Image.LANCZOS).save(f"{outdir}/{prefix}_thumbnail_C.jpg", quality=92)

# ---------------- long video ----------------
def make_long(outdir, prefix, seed):
    g = G(False); lvs = build_levels(seed); N = len(lvs); segs = []
    last = lvs[-1]
    segs.append(level_seg(g, last, f"LEVEL {N} / {N} • IMPOSSIBLE", think=1, reveal=False, instant=True, q_text="Can you find it?",
                          intro=f"Can you find {spoken(last['target'])}? Most adults can't. The answer is at the very end!"))
    for i, (lv, (n, dirs, tier, th)) in enumerate(zip(lvs, PLAN)):
        name, col = TIERS[tier]; chip = f"LEVEL {i + 1} / {N} • {name}"
        if i == 0:
            segs.append(card(g, [("Let's start easy!", 90, WHITE), ("LEVEL 1", 120, YELLOW)], "Let's start easy. Level 1!", 1.2, 0.1, chip))
        elif i == SPEED[0]:
            segs.append(card(g, [("SPEED ROUND!", 120, YELLOW), ("3 levels • 6 seconds each", 70, WHITE)],
                             "Speed round! Three levels, only six seconds each. Ready? Go!", 2.0, 0.1, chip))
        elif i not in SPEED:
            segs.append(card(g, [(f"LEVEL {i + 1}", 120, YELLOW), (name, 84, col)], f"Level {i + 1}. {name.lower()}.", 1.2, 0.1, chip))
        if i in (4, 14):
            segs.append(card(g, [("NEW RULE!", 110, YELLOW), (HINT[dirs], 70, WHITE)],
                             "New rule! Now it can also hide going down." if dirs == "HV" else "New rule! Now it can also hide on a diagonal.", 2.0, 0.2, chip))
        segs.append(level_seg(g, lv, chip.replace(name, "SPEED ROUND") if i in SPEED else chip, think=th,
                              hold=2.6 if (tier == 0 or i in SPEED) else 3.6, prog=(i, N),
                              intro=(f"Here is the one from the start! Find {spoken(lv['target'])}!" if i == N - 1 else
                                     (f"Six seconds! Find {spoken(lv['target'])}!" if i in SPEED else None))))
        if i + 1 in (4, 14):
            segs.append(card(g, [("Still perfect?", 104, YELLOW), (f"Found all {i + 1}?", 84, WHITE), ("Type YES in the comments!", 58, SOFT)],
                             f"Did you find all {i + 1} so far? Type yes in the comments!", 2.4, 0.2, chip))
        if i + 1 in (9, 17):
            segs.append(card(g, [(f"LEVEL {N} is coming...", 92, YELLOW), ("the one from the start!", 64, WHITE), ("Stay until the end!", 70, WHITE)],
                             f"Level {N} is coming. The one from the start! Stay until the end to see the answer!", 2.2, 0.2, chip))
        if i + 1 in (11, 20):
            segs.append(card(g, [("Enjoying it?", 86, WHITE), ("SUBSCRIBE & LIKE", 104, YELLOW), ("It really helps QuizNado07", 50, SOFT)],
                             "If you like it so far, subscribe and like! It really helps QuizNado07.", 3, 0.4, chip))
    segs.append(card(g, [("What's your score?", 96, YELLOW), (f"___ / {N}", 124, WHITE), ("Comment it below!", 60, SOFT)],
                     f"How many did you find out of {N}? Write your score in the comments!", 3, 0.8))
    segs.append(end_screen_seg(g))
    total = render(segs, g, f"{outdir}/{prefix}.mp4"); thumbs(outdir, prefix, last)
    json.dump(lvs, open(f"{outdir}/{prefix}_answers.json", "w"))
    print("long", round(total, 1), "s", flush=True)
    for i, lv in enumerate(lvs): print(f"L{i + 1} {lv['target']}: {where(lv)}")

# ---------------- teaser Short (hook-first loop) ----------------
def make_teaser(out, seed, long_thumb, mode="after"):
    """mode 'before': posted the DAY BEFORE the long video (level 24, 'full video tomorrow', bell).
       mode 'after':  posted after the long video (level 24, 'full video out now')."""
    g = G(True); lvs = build_levels(seed); N = len(lvs)
    hi, w1, w2 = (N - 1, 4, 12) if mode == "before" else (N - 1, 7, 15)   # both on level 24 = the thumbnail
    hard = lvs[hi]; chip = f"LEVEL {hi + 1} • {'IMPOSSIBLE' if hi >= N - 2 else 'EXPERT'}"
    segs = [level_seg(g, hard, chip, think=1, reveal=False, instant=True,
                      q_text="New challenge TOMORROW!" if mode == "before" else "Most adults can't find it",
                      intro=(f"New challenge tomorrow! Can you find {spoken(hard['target'])}?" if mode == "before"
                             else f"Most adults can't find {spoken(hard['target'])}!")),
            level_seg(g, lvs[w1], "WARM-UP 1", think=5, hold=2.4, intro="Warm up first. Go!"),
            level_seg(g, lvs[w2], "WARM-UP 2", think=6, hold=2.4, intro="Harder!"),
            level_seg(g, hard, chip, think=6, reveal=False, q_text="Your turn. 6 seconds!",
                      intro=f"Level {hi + 1}. Find {spoken(hard['target'])}!")]
    th = Image.open(long_thumb).convert("RGBA")
    if mode == "before":
        l1, l2, btn = "FULL VIDEO TOMORROW", "Answer + 24 levels inside", "SUBSCRIBE + TURN ON"
        voice = "The answer is in the full video, tomorrow! Subscribe and turn on notifications so you don't miss it!"
    else:
        l1, l2, btn = "FULL VIDEO OUT NOW!", "Watch it to see the answer", "SUBSCRIBE & LIKE"
        voice = "The full video is out now on QuizNado07! Go watch it to see the answer!"
    snd = []; d = say(snd, 0.1, voice) + 0.4
    def draw(im, t):
        txt(im, (g.W / 2, 555), l1, 76, YELLOW, 7)
        txt(im, (g.W / 2, 660), l2, 60, WHITE, 6)
        tw = 940; t2 = th.resize((tw, int(tw * th.height / th.width)), Image.LANCZOS)
        shadowed(im, (70, 740, 70 + tw, 740 + t2.height), 24, WHITE, blur=16, off=10, alpha=110)
        m = Image.new("L", t2.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, t2.width - 1, t2.height - 1], radius=24, fill=255)
        im.paste(t2, (70, 740), m)
        dd = ImageDraw.Draw(im); cx, cy = 70 + tw - 70, 740 + t2.height - 55
        dd.ellipse([cx - 48, cy - 48, cx + 48, cy + 48], fill=RED); dd.polygon([(cx - 15, cy - 24), (cx - 15, cy + 24), (cx + 26, cy)], fill=WHITE)
        y = 740 + t2.height + 75
        dd.rounded_rectangle([130, y + 10, 950, y + 115], radius=52, fill=RED)
        bx = g.W / 2 - (38 if mode == "before" else 0)
        dd.text((bx, y + 62), btn, font=F(56), fill=WHITE, anchor="mm")
        if mode == "before":
            e = emoji("🔔", 64); im.alpha_composite(e, (int(bx + dd.textlength(btn, font=F(56)) / 2 + 12), int(y + 62 - e.height / 2)))
    segs.append(Seg(max(3.8, d), draw, lambda t: "s", snd, "QuizNado07"))
    total = render(segs, g, out)
    print("teaser", mode, round(total, 1), "s; warm-ups", lvs[w1]["target"], lvs[w2]["target"], "; level", hi + 1, hard["target"], where(hard), flush=True)

# ---------------- TikTok series (3 parts, 60-90 s, cliffhanger -> "Follow for Part N") ----------------
# No YouTube talk inside parts 1-2 (TikTok wants people to follow on TikTok); part 3 ends on the full video.
TT_PARTS = [  # (payoff level from the previous part or None, answered levels, cliffhanger level, think)
    (None, [0, 2, 4, 7], 12, 6),
    (12, [9, 14, 17], 23, 8),
    (23, [19, 21], 22, 10),
]
def end_card(g, l1, l2, btn, voice, sub=None):
    snd = []; d = say(snd, 0.1, voice) + 0.5
    def draw(im, t):
        txt(im, (g.W / 2, 760), l1, 96, YELLOW, 9)
        txt(im, (g.W / 2, 880), l2, 64, WHITE, 6)
        if sub: txt(im, (g.W / 2, 980), sub, 54, SOFT, 5)
        dd = ImageDraw.Draw(im); pulse = 1 + 0.04 * math.sin(t * 6); w, h = 640 * pulse, 130 * pulse; y = 1180
        dd.rounded_rectangle([g.W / 2 - w / 2, y - h / 2, g.W / 2 + w / 2, y + h / 2], radius=65, fill=(254, 44, 85))
        dd.text((g.W / 2, y), btn, font=F(64), fill=WHITE, anchor="mm")
    return Seg(max(3.5, d), draw, lambda t: ("e", int(t * 10) % 11), snd, "QuizNado07")

def make_tiktok(outdir, prefix, seed):
    lvs = build_levels(seed); N = len(lvs); res = []
    for pi, (pay, ans, cliff, th) in enumerate(TT_PARTS, 1):
        g = G(True); g.footer = "@QuizNado07 • Follow for more!" if pi < len(TT_PARTS) else "@QuizNado07"
        chip = lambda i: f"PART {pi} • LEVEL {i + 1}"
        segs = []
        if pay is None:   # part 1 hook: the cliffhanger grid in the first frame
            segs.append(level_seg(g, lvs[cliff], chip(cliff), think=1, reveal=False, instant=True, q_text="Can you find it?",
                                  intro=f"Can you find {spoken(lvs[cliff]['target'])}? Warm up first!"))
        else:             # payoff first: the answer they followed for
            segs.append(level_seg(g, lvs[pay], f"PART {pi - 1} ANSWER", think=1, instant=True, hold=3.2, q_text="Did you find it?",
                                  intro=f"Part {pi}! Did you find {spoken(lvs[pay]['target'])}?"))
        for k, i in enumerate(ans):
            segs.append(level_seg(g, lvs[i], chip(i), think=th, hold=2.4, intro=("Go!" if k == 0 else None)))
        last = pi == len(TT_PARTS)
        segs.append(level_seg(g, lvs[cliff], chip(cliff), think=th, reveal=False,
                              q_text="Comment the row!" if last else "Last one. Find it!",
                              intro=f"{'Final one' if last else 'Last one'}! Find {spoken(lvs[cliff]['target'])}!"))
        if not last:
            segs.append(end_card(g, f"Answer in PART {pi + 1}!", "Follow so you don't miss it", "+ FOLLOW",
                                 f"The answer is in part {pi + 1}! Follow so you don't miss it!", "Comment where you think it is"))
        else:
            segs.append(end_card(g, "Comment the row!", "Full video: 24 levels", "+ FOLLOW",
                                 "Comment the row! Want all 24 levels? Search QuizNado07 on YouTube. And follow for more!",
                                 "Search QuizNado07 on YouTube"))
        out = f"{outdir}/{prefix}_Part{pi}.mp4"; total = render(segs, g, out)
        res.append((out, round(total, 1), lvs[cliff]["target"], where(lvs[cliff])))
        print("tiktok part", pi, round(total, 1), "s; cliff", lvs[cliff]["target"], where(lvs[cliff]), flush=True)
    return res

if __name__ == "__main__":
    if sys.argv[1] == "long": make_long(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    elif sys.argv[1] == "teaser": make_teaser(sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "after")
    elif sys.argv[1] == "tiktok": make_tiktok(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    elif sys.argv[1] == "frames":
        o = sys.argv[2]; lvs = build_levels(11)
        for portrait in (False, True):
            g = G(portrait)
            for li in (3, 23):
                s = level_seg(g, lvs[li], f"LEVEL {li + 1} / 24 • TEST", think=10)
                for tt, nm in ((5.0, "ask"), (s.dur - 0.5, "rev")):
                    im = background(g, s.chip); s.draw(im, tt); im.convert("RGB").save(f"{o}/fn_{'p' if portrait else 'l'}{li}_{nm}.png")
        thumbs(o, "fn", lvs[-1])

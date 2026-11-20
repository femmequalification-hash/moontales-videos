"""QuizNado07 'Count Fast' — emojis scattered on screen, "HOW MANY 🐶?", 3 options, animated count reveal.
python3 countfast.py long   OUT_DIR PREFIX SEED   -> 30 levels, 10+ min, thumbnail, answers
python3 countfast.py teaser OUT.mp4 SEED THUMB    -> Short posted at the same time (big clear emojis in frame 1)
python3 countfast.py frames OUT_DIR SEED
"""
import sys, os, math, random, json
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import F, user_logo, tick, ding, whoosh, ease, shadowed, YELLOW, WHITE, DEEP, GREEN
from weights import Seg, say, render, txt, bar, card, end_screen_seg, TIERS, RED, SOFT
from findnum import G, badge_next, hook_banner
from oddemoji import emo, progress

PAPER = (252, 240, 246); PINK = (254, 44, 85)
NAMES = {"🍎": "apples", "🐶": "dogs", "⚽": "footballs", "🚗": "cars", "⭐": "stars", "🍓": "strawberries", "🐱": "cats",
         "🌻": "sunflowers", "🍊": "oranges", "🐸": "frogs", "🐕": "dogs", "🍏": "green apples", "😀": "smiley faces",
         "💖": "hearts", "🌕": "full moons", "🐟": "fish", "🦋": "butterflies", "🍩": "donuts", "🐤": "chicks", "🎈": "balloons"}
SETS = {   # target, distractors (look-alike as it gets harder)
    0: [("🍎", ["🍌"]), ("🐶", ["🐟"]), ("⚽", ["🏀"]), ("🚗", ["✈️"[0]]), ("⭐", ["🌙"]), ("🎈", ["🎁"])],
    1: [("🍓", ["🍒", "🍎"]), ("🐱", ["🐶", "🐭"]), ("🌻", ["🌼", "🌷"]), ("🍊", ["🍋", "🍑"]), ("🐸", ["🐢", "🐍"]), ("🦋", ["🐝", "🐞"])],
    2: [("🐶", ["🐕", "🐩"]), ("🍏", ["🍐", "🥝"]), ("🍩", ["🍪", "🥯"]), ("🐤", ["🐥", "🐣"])],
    3: [("😀", ["😃", "😄"]), ("💖", ["💗", "💓"]), ("🐟", ["🐠", "🐡"])],
    4: [("😀", ["😃", "😄", "😁"]), ("🌕", ["🌝", "🌖"]), ("💖", ["💗", "💓", "💞"])],
}
# (items, set level, target count range, think s, tier)
PLAN = ([(10, 0, (3, 5), 7, 0)] * 5 + [(14, 1, (4, 6), 10, 1)] + [(12, 1, (3, 5), 5, 1)] * 3 + [(14, 1, (4, 7), 10, 1)] +
        [(20, 2, (5, 8), 12, 2)] * 6 + [(26, 2, (6, 9), 14, 3)] * 3 + [(30, 3, (7, 10), 15, 3)] * 3 +
        [(36, 3, (8, 11), 17, 4)] * 5 + [(44, 4, (9, 13), 20, 5)] * 3)
SPEED = (6, 7, 8)

def place(n, rnd):
    """normalized centers (0..1) with a minimum distance; returns positions and the item size (fraction of the box)"""
    s = min(0.2, math.sqrt(0.42 / n)); pts = []
    for _ in range(4000):
        if len(pts) == n: break
        p = (rnd.uniform(s / 2 + 0.02, 1 - s / 2 - 0.02), rnd.uniform(s / 2 + 0.02, 1 - s / 2 - 0.02))
        if all(math.hypot(p[0] - q[0], p[1] - q[1]) > s * 1.08 for q in pts): pts.append(p)
    if len(pts) < n: return place_grid(n, rnd)
    return pts, s

def place_grid(n, rnd):
    k = math.ceil(math.sqrt(n)); s = 0.9 / k; cells = [(i, j) for i in range(k) for j in range(k)]; rnd.shuffle(cells)
    return [((j + .5) / k + rnd.uniform(-.1, .1) / k, (i + .5) / k + rnd.uniform(-.1, .1) / k) for i, j in cells[:n]], s * 0.85

def make_level(items, sl, rng, rnd, used):
    opts = [x for x in SETS[sl] if x[0] not in used[-2:]] or SETS[sl]; tgt, dis = rnd.choice(opts); used.append(tgt)
    c = rnd.randint(*rng); kinds = [tgt] * c + [rnd.choice(dis) for _ in range(items - c)]
    for dd in dis:                                   # every distractor shows up at least once
        if dd not in kinds[c:] and items - c > len(dis): kinds[c + dis.index(dd)] = dd
    rnd.shuffle(kinds); pts, s = place(items, rnd)
    wrong = sorted({c - 2, c - 1, c + 1, c + 2} - {0}); w = rnd.sample(wrong, 2)
    opts_ = [c] + w; rnd.shuffle(opts_)
    return {"kinds": kinds, "pts": pts, "s": s, "target": tgt, "count": c, "options": opts_, "answer": "ABC"[opts_.index(c)]}

def build_levels(seed):
    rnd = random.Random(seed); used = []
    return [make_level(n, sl, rng, rnd, used) for (n, sl, rng, th, tier) in PLAN]

_ac = {}
def area_img(box, lv, shown=0, reveal=False):
    """paper card with scattered emojis; when reveal: others dimmed, first `shown` targets ringed and numbered"""
    key = (box, id(lv), shown, reveal)
    if key in _ac: return _ac[key]
    x0, y0, x1, y1 = box; W, H = x1 - x0, y1 - y0
    im = Image.new("RGBA", (W + 40, H + 40), (0, 0, 0, 0)); shadowed(im, (0, 0, W, H), 30, PAPER, blur=14, off=8, alpha=90)
    es = int(min(W, H) * lv["s"]); order = targets_order(lv); rank = {i: k for k, i in enumerate(order)}
    d = ImageDraw.Draw(im)
    for i, (k, (px, py)) in enumerate(zip(lv["kinds"], lv["pts"])):
        e = emo(k, es)
        if reveal and k != lv["target"]:
            e = e.copy(); e.putalpha(e.getchannel("A").point(lambda v: int(v * 0.25)))
        cx, cy = px * W, py * H; im.alpha_composite(e, (int(cx - es / 2), int(cy - es / 2)))
        if reveal and i in rank and rank[i] < shown:
            R = es * 0.62; d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=YELLOW, width=max(5, es // 14))
            r2 = max(18, es // 4); bx, by = cx + R * 0.7, cy - R * 0.7
            d.ellipse([bx - r2, by - r2, bx + r2, by + r2], fill=PINK, outline=WHITE, width=3)
            d.text((bx, by), str(rank[i] + 1), font=F(int(r2 * 1.2)), fill=WHITE, anchor="mm")
    _ac[key] = im; return im

def targets_order(lv):
    idx = [i for i, k in enumerate(lv["kinds"]) if k == lv["target"]]
    return sorted(idx, key=lambda i: (round(lv["pts"][i][1] * 4), lv["pts"][i][0]))

def question(im, g, lv):
    d = ImageDraw.Draw(im); size = 96 if not g.portrait else 84; s = "HOW MANY"
    tw = d.textlength(s, font=F(size)); es = int(size * 1.25); w = tw + es + 120; cx, cy = g.find_xy
    shadowed(im, (cx - w / 2, cy - size * 0.8, cx + w / 2, cy + size * 0.8), 40, WHITE, blur=12, off=6, alpha=80)
    d = ImageDraw.Draw(im); x = cx - w / 2 + 40
    d.text((x, cy), s, font=F(size), fill=DEEP, anchor="lm")
    im.alpha_composite(emo(lv["target"], es), (int(x + tw + 15), int(cy - es / 2)))
    d.text((x + tw + es + 25, cy), "?", font=F(size), fill=DEEP, anchor="lm")

def options(im, g, lv, state):
    """state: None (neutral) or 'rev' (correct green, others faded)"""
    d = ImageDraw.Draw(im)
    if g.portrait: cy, w, h, gap, cx0 = 1625, 270, 100, 40, 540
    else: cy, w, h, gap, cx0 = 585, 220, 110, 30, 1450
    for k, val in enumerate(lv["options"]):
        cx = cx0 + (k - 1) * (w + gap); L = "ABC"[k]; ok = val == lv["count"]
        fill = (34, 197, 94) if (state == "rev" and ok) else ((255, 255, 255, 90) if state == "rev" else WHITE)
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        od.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=28, fill=fill,
                             outline=YELLOW if (state == "rev" and ok) else None, width=6)
        im.alpha_composite(ov); d = ImageDraw.Draw(im)
        col = WHITE if (state == "rev" and ok) else DEEP
        d.text((cx - w / 2 + 28, cy), L + ")", font=F(int(h * 0.42)), fill=col, anchor="lm")
        d.text((cx + 30, cy), str(val), font=F(int(h * 0.6)), fill=col, anchor="mm")

def level_seg(g, lv, chip, *, think, intro=None, reveal=True, hold=2.2, instant=False, prog=None,
              badge=None, hook=None, hook_dur=2.4, min_intro=1.6, q_text="Count fast!"):
    snd = []; nm = NAMES.get(lv["target"], "of them")
    vd = say(snd, 0.2, intro or f"How many {nm}?")
    if not instant: snd.insert(0, (0.25, whoosh() * 0.6))
    t_think = 0.0 if instant else max(min_intro, vd + 0.4)
    if instant: think = max(think, int(math.ceil(vd + 0.5)))
    for s in range(think): snd.append((t_think + s, tick() * (1.5 if s >= think - 3 else 1)))
    t_rev = t_think + think; c = lv["count"]; step = min(0.32, 2.2 / c)
    if reveal:
        for k in range(c): snd.append((t_rev + 0.15 + k * step, tick() * 0.6))
        t_done = t_rev + 0.15 + c * step; snd.append((t_done, ding()))
        rv = say(snd, t_done + 0.15, f"{c}! Answer {lv['answer']}!"); total = t_done + max(hold, rv + 0.5)
    else:
        total = t_rev; t_rev = t_done = 1e9
    def draw(im, t):
        pop = 1.0 if instant else ease(min(1, t / 0.3))
        shown = 0 if t < t_rev else min(c, int((t - t_rev - 0.15) / step) + 1 if t >= t_rev + 0.15 else 0)
        a = area_img(g.box, lv, shown, t >= t_rev)
        if pop < 1: a = a.copy(); a.putalpha(a.getchannel("A").point(lambda v: int(v * pop)))
        im.alpha_composite(a, (g.box[0], g.box[1]))
        question(im, g, lv)
        options(im, g, lv, "rev" if t >= t_done else None)
        if prog: progress(im, g, *prog)
        if badge: badge_next(im, g, badge)
        hy = (g.hint_xy[0], g.hint_xy[1] + (0 if g.portrait else 0))
        if t >= t_rev:
            txt(im, hy, f"{shown} {nm}..." if t < t_done else f"{c} {nm}!", 56, YELLOW, 6)
        elif t >= t_think:
            txt(im, hy, q_text, 56, YELLOW, 6)
            left = max(0.0, (t_rev if reveal else total) - t); bar(im, g, min(1, left / think), max(1, math.ceil(left)))
        if hook: hook_banner(im, g, hook, t, hook_dur)
    def key(t):
        if t < 0.35 and not instant: return None
        if hook and t < hook_dur: return None
        if t >= t_rev: return ("r", 999 if t >= t_done else int((t - t_rev - 0.15) / step))
        if t < t_think: return "a"
        return ("c", int((t - t_think) * 10))
    return Seg(total, draw, key, snd, chip)

def geo(portrait):
    g = G(portrait)
    if portrait: g.box = (90, 690, 990, 1540); g.find_xy = (540, 520); g.hint_xy = (540, 625); g.timer = (180, 1735, 1000, 1765); g.count = (95, 1750, 46)
    else: g.find_xy = (1450, 300); g.hint_xy = (1450, 430); g.timer = (1180, 770, 1860, 810); g.count = (1110, 790, 52)
    return g

# ---------------- long video ----------------
def make_long(outdir, prefix, seed):
    g = geo(False); lvs = build_levels(seed); N = len(lvs); segs = []; last = lvs[-1]
    segs.append(level_seg(g, last, f"LEVEL {N} / {N} • IMPOSSIBLE", think=1, reveal=False, instant=True,
                          hook="MOST PEOPLE COUNT WRONG", hook_dur=2.6,
                          intro=f"How many {NAMES[last['target']]}? Most people count wrong. The answer is at the very end!"))
    for i, (lv, (n, sl, rng, th, tier)) in enumerate(zip(lvs, PLAN)):
        name, col = TIERS[tier]; chip = f"LEVEL {i + 1} / {N} • " + ("SPEED ROUND" if i in SPEED else name)
        if i == 0:
            segs.append(card(g, [("Let's start easy!", 90, WHITE), ("LEVEL 1", 120, YELLOW)], "Let's start easy. Level 1!", 1.2, 0.1, chip))
        elif i == SPEED[0]:
            segs.append(card(g, [("SPEED ROUND!", 120, YELLOW), ("3 levels • 5 seconds each", 70, WHITE)],
                             "Speed round! Three levels, only five seconds each. Go!", 2.0, 0.1, chip))
        elif i not in SPEED:
            more = PLAN[i - 1][0] != n; look = PLAN[i - 1][1] != sl and sl >= 2
            label = "LOOK-ALIKES!" if look else (f"{n} EMOJIS NOW" if more else name)
            segs.append(card(g, [(f"LEVEL {i + 1}", 120, YELLOW), (label, 76, col)],
                             f"Level {i + 1}." + (" Careful, they look alike!" if look else (" More emojis!" if more else "")), 1.2, 0.1, chip))
        segs.append(level_seg(g, lv, chip, think=th, hold=2.0 if (tier == 0 or i in SPEED) else 2.4, prog=(i, N),
                              intro=(f"Here is the one from the start! How many {NAMES[lv['target']]}?" if i == N - 1 else
                                     (f"Five seconds! How many {NAMES[lv['target']]}?" if i in SPEED else None))))
        if i + 1 in (5, 16):
            segs.append(card(g, [("Still perfect?", 104, YELLOW), (f"{i + 1} out of {i + 1}?", 84, WHITE), ("Type YES in the comments!", 58, SOFT)],
                             f"Still perfect? Type yes in the comments!", 2.4, 0.2, chip))
        if i + 1 in (11, 22):
            segs.append(card(g, [(f"LEVEL {N} is coming...", 92, YELLOW), ("the one from the start!", 64, WHITE), ("Stay until the end!", 70, WHITE)],
                             f"Level {N} is coming. The one from the start! Stay until the end to see the answer!", 2.2, 0.2, chip))
        if i + 1 in (9, 19, 26):
            segs.append(card(g, [("Counting fast?", 86, WHITE), ("SMASH LIKE", 110, YELLOW), ("and subscribe to QuizNado07", 52, SOFT)],
                             "Counting fast? Smash like, and subscribe to QuizNado07!", 3, 0.4, chip))
    segs.append(card(g, [("What's your score?", 96, YELLOW), (f"___ / {N}", 124, WHITE), ("Comment it below!", 60, SOFT)],
                     f"How many did you get right out of {N}? Write your score in the comments!", 3, 0.8))
    segs.append(end_screen_seg(g))
    total = render(segs, g, f"{outdir}/{prefix}.mp4")
    json.dump(lvs, open(f"{outdir}/{prefix}_answers.json", "w"), ensure_ascii=False)
    thumbnail(f"{outdir}/{prefix}_THUMBNAIL.jpg", seed)
    print("long", round(total, 1), "s", flush=True)

# ---------------- Short (same time as the long video) ----------------
def make_teaser(out, seed, long_thumb):
    g = geo(True); g.footer = ""; lvs = build_levels(seed); N = len(lvs)
    hi = 12; hard = lvs[hi]; chip = f"LEVEL {hi + 1} • HARD"         # 20 big clear emojis = readable in frame 1
    segs = [level_seg(g, hard, chip, think=1, reveal=False, instant=True, hook="MOST PEOPLE COUNT WRONG", hook_dur=2.6,
                      intro=f"How many {NAMES[hard['target']]}? Most people count wrong! Two quick ones first!"),
            level_seg(g, lvs[1], "WARM-UP 1/2", think=4, hold=1.4, badge=f"NEXT: LEVEL {hi + 1}"),
            level_seg(g, lvs[6], "WARM-UP 2/2", think=4, hold=1.4, badge=f"NEXT: LEVEL {hi + 1}"),
            level_seg(g, hard, chip, think=6, reveal=False, q_text="No answer here...",
                      intro=f"Level {hi + 1}! How many {NAMES[hard['target']]}?")]
    th = Image.open(long_thumb).convert("RGBA"); snd = []
    d = say(snd, 0.1, "A, B or C? Comment! The answer is in the full video, out now on QuizNado07!") + 0.4
    def draw(im, t):
        im.alpha_composite(area_img(g.box, hard), (g.box[0], g.box[1]))
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
    print("teaser", round(total, 1), "s; level", hi + 1, hard["target"], "count", hard["count"], "answer", hard["answer"], hard["options"], flush=True)

# ---------------- thumbnail: few BIG emojis, readable on a phone ----------------
def thumbnail(path, seed):
    import numpy as np
    rnd = random.Random(seed + 100)
    y, x = np.mgrid[0:1080, 0:1920]; t = ((y / 1080 + x / 1920) / 2)[..., None]
    im = Image.fromarray((np.array((255, 196, 0)) * (1 - t) + np.array((255, 84, 64)) * t).astype(np.uint8), "RGB").convert("RGBA")
    im.alpha_composite(user_logo(120), (30, 25))
    kinds = ["🐶"] * 6 + ["🐕"] * 4 + ["🐩"] * 2; rnd.shuffle(kinds)
    box = (980, 90, 1860, 990); W, H = box[2] - box[0], box[3] - box[1]
    shadowed(im, box, 34, PAPER, blur=14, off=8, alpha=90)
    pts, _ = place(len(kinds), rnd); es = 175
    for k, (px, py) in zip(kinds, pts):
        im.alpha_composite(emo(k, es), (int(box[0] + px * W - es / 2), int(box[1] + py * H - es / 2)))
    d = ImageDraw.Draw(im)
    tw = d.textlength("HOW MANY", font=F(110)); qw = d.textlength("?", font=F(110)); W2 = tw + 150 + qw + 110; x0 = 495 - W2 / 2
    d.rounded_rectangle([x0, 255, x0 + W2, 465], radius=60, fill=WHITE)
    d.text((x0 + 40, 360), "HOW MANY", font=F(110), fill=DEEP, anchor="lm")
    im.alpha_composite(emo("🐶", 140), (int(x0 + 50 + tw), 290))
    d.text((x0 + 60 + tw + 145, 360), "?", font=F(110), fill=DEEP, anchor="lm")
    txt(im, (495, 640), "COUNT", 150, WHITE, 12)
    d = ImageDraw.Draw(im); d.text((495, 820), "FAST!", font=F(180), fill=WHITE, anchor="mm", stroke_width=14, stroke_fill=(60, 20, 120))
    st = Image.new("RGBA", (520, 120), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
    sd.rounded_rectangle([0, 0, 519, 119], radius=24, fill=(220, 38, 38), outline=WHITE, width=8)
    sd.text((260, 60), "IMPOSSIBLE", font=F(84), fill=WHITE, anchor="mm")
    st = st.rotate(-8, expand=True, resample=Image.BICUBIC); im.alpha_composite(st, (1420 - st.width // 2, 70 - st.height // 2 + 10))
    im.convert("RGB").resize((1280, 720), Image.LANCZOS).save(path, quality=93)

if __name__ == "__main__":
    a = sys.argv
    if a[1] == "long": make_long(a[2], a[3], int(a[4]))
    elif a[1] == "teaser": make_teaser(a[2], int(a[3]), a[4])
    elif a[1] == "thumb": thumbnail(a[2], int(a[3]))
    elif a[1] == "frames":
        from weights import background
        lvs = build_levels(int(a[3]))
        for i, portrait in ((0, False), (13, False), (29, False), (12, True)):
            g = geo(portrait); s = level_seg(g, lvs[i], f"LEVEL {i + 1}", think=PLAN[i][3], prog=None if portrait else (i, 30))
            for tt, nm in ((3.0, "ask"), (s.dur - 0.3, "rev")):
                im = background(g, s.chip); s.draw(im, tt)
                im.convert("RGB").resize((g.W // 2, g.H // 2)).save(f"{a[2]}/c_{i}_{'p' if portrait else 'l'}_{nm}.png")
        thumbnail(f"{a[2]}/thumb.jpg", int(a[3]))

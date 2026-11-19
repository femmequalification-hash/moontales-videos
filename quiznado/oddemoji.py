"""QuizNado07 'Find the odd emoji' — a grid of identical emojis hides ONE different one.
python3 oddemoji.py long   OUT_DIR PREFIX SEED   -> 30 levels (5x5 -> 10x10), 10+ min, thumbnail, answers
python3 oddemoji.py teaser OUT.mp4 SEED THUMB    -> Short posted at the same time: level 30 first, 2 warm-ups, level 30 again NO answer
python3 oddemoji.py frames OUT_DIR SEED          -> preview stills
"""
import sys, os, math, random, json
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import F, user_logo, tick, ding, whoosh, ease, shadowed, YELLOW, WHITE, DEEP
from weights import Seg, say, render, txt, bar, card, end_screen_seg, EMO, TIERS, RED, SOFT
from findnum import G, badge_next, hook_banner
from weights import emoji

def progress(im, g, cur, N):
    if g.portrait or cur is None: return
    d = ImageDraw.Draw(im); x0, y, x1 = 1120, 935, 1830; step = (x1 - x0) / (N - 1)
    d.text((x0 - 10, y - 50), "YOUR PROGRESS", font=F(30), fill=SOFT, anchor="lm")
    for k in range(N - 1):
        x = x0 + k * step
        if k < cur: d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=YELLOW)
        elif k == cur: d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=WHITE, outline=YELLOW, width=4)
        else: d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(255, 255, 255, 70))
    e = emoji("🏆", 52 if cur == N - 1 else 42); im.alpha_composite(e, (int(x1 - e.width / 2), int(y - e.height / 2)))

PAPER = (252, 240, 246)
PAIRS = {  # base, odd — difficulty grows
    0: [("🍎", "🍏"), ("🐶", "🐱"), ("⚽", "🏀"), ("🍓", "🍒"), ("🚗", "🚕")],
    1: [("😀", "😃"), ("🐻", "🐨"), ("🌻", "🌼"), ("🍊", "🍑"), ("🐭", "🐹")],
    2: [("😃", "😄"), ("💛", "🧡"), ("🙂", "😊"), ("😗", "😙"), ("🌑", "🌚"), ("😮", "😯")],
    3: [("😐", "😑"), ("😚", "😙"), ("😄", "😁"), ("😔", "😞"), ("😟", "🙁")],
    4: [("🕐", "🕜"), ("🕓", "🕟"), ("😐", "😑"), ("😗", "😚")],
}
# (grid n, pair level, think s, tier)
PLAN = ([(5, 0, 8, 0)] * 5 + [(6, 1, 10, 1)] + [(6, 1, 5, 1)] * 3 + [(6, 1, 10, 1)] +
        [(7, 2, 13, 2)] * 6 + [(8, 2, 14, 3)] * 3 + [(8, 3, 14, 3)] * 3 + [(9, 3, 17, 4)] * 5 + [(10, 4, 22, 5)] * 3)
SPEED = (6, 7, 8)

_ec = {}
def emo(ch, size):
    """same footprint for every emoji (no crop) so the odd one is never given away by its size"""
    k = (ch, size)
    if k not in _ec:
        im = Image.new("RGBA", (140, 140), (0, 0, 0, 0)); ImageDraw.Draw(im).text((2, 4), ch, font=EMO, embedded_color=True)
        _ec[k] = im.resize((size, size), Image.LANCZOS)
    return _ec[k]

def make_level(n, pl, rnd, used):
    opts = [p for p in PAIRS[pl] if p not in used] or PAIRS[pl]
    a, b = rnd.choice(opts); used.append((a, b))
    if rnd.random() < 0.5 and pl >= 2: a, b = b, a
    return {"n": n, "base": a, "odd": b, "cell": [rnd.randrange(n), rnd.randrange(n)]}

def build_levels(seed):
    rnd = random.Random(seed); used = []
    return [make_level(n, pl, rnd, used) for (n, pl, th, tier) in PLAN]

def where(lv):
    r, c = lv["cell"]; return f"row {r + 1}, column {c + 1}"

_gc = {}
def grid_img(g, lv, reveal):
    """paper card with the emoji grid; reveal 0..1 dims the others and rings the odd one"""
    key = (g.box, lv["n"], lv["base"], lv["odd"], tuple(lv["cell"]), round(min(1, reveal), 1))
    if key in _gc: return _gc[key]
    x0, y0, x1, y1 = g.box; W, H = x1 - x0, y1 - y0; n = lv["n"]
    im = Image.new("RGBA", (W + 40, H + 40), (0, 0, 0, 0)); shadowed(im, (0, 0, W, H), 30, PAPER, blur=14, off=8, alpha=90)
    pad = 22; cs = (W - 2 * pad) / n; es = int(cs * 0.84); rv = min(1.0, reveal)
    for r in range(n):
        for c in range(n):
            odd = [r, c] == lv["cell"]; e = emo(lv["odd"] if odd else lv["base"], es)
            if rv > 0 and not odd:
                e = e.copy(); e.putalpha(e.getchannel("A").point(lambda v: int(v * (1 - 0.7 * rv))))
            im.alpha_composite(e, (int(pad + c * cs + (cs - es) / 2), int(pad + r * cs + (cs - es) / 2)))
    if rv > 0:
        r, c = lv["cell"]; cx, cy = pad + (c + .5) * cs, pad + (r + .5) * cs; R = cs * 0.62
        d = ImageDraw.Draw(im); d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(254, 44, 85, int(255 * rv)), width=max(6, int(cs * 0.09)))
    _gc[key] = im; return im

def find_label(im, g, lv):
    s = "FIND THE ODD ONE!"; size = 92 if not g.portrait else 80
    d = ImageDraw.Draw(im)
    while d.textlength(s, font=F(size)) > (700 if not g.portrait else 900): size -= 2
    w = d.textlength(s, font=F(size)) + 70; cx, cy = g.find_xy
    shadowed(im, (cx - w / 2, cy - size * 0.75, cx + w / 2, cy + size * 0.75), 40, WHITE, blur=12, off=6, alpha=80)
    ImageDraw.Draw(im).text((cx, cy), s, font=F(size), fill=DEEP, anchor="mm")
    txt(im, g.hint_xy, f"{lv['n']} x {lv['n']} • {lv['n'] ** 2} emojis", 46 if not g.portrait else 44, SOFT, 5)

def level_seg(g, lv, chip, *, think, intro=None, reveal=True, hold=3.2, q_text="Can you find it?", instant=False,
              prog=None, badge=None, hook=None, hook_dur=2.4, min_intro=1.6, reveal_say=None):
    snd = []; vd = say(snd, 0.2, intro or "Find the odd one!")
    if not instant: snd.insert(0, (0.25, whoosh() * 0.6))
    t_think = 0.0 if instant else max(min_intro, vd + 0.4)
    if instant: think = max(think, int(math.ceil(vd + 0.5)))
    for s in range(think): snd.append((t_think + s, tick() * (1.5 if s >= think - 3 else 1)))
    t_rev = t_think + think
    if reveal:
        snd.append((t_rev, ding())); rv = say(snd, t_rev + 0.3, reveal_say or f"There! {where(lv).capitalize()}.")
        total = t_rev + max(hold, rv + 0.6)
    else:
        total = t_rev; t_rev = 1e9
    def draw(im, t):
        pop = 1.0 if instant else ease(min(1, t / 0.3))
        gi = grid_img(g, lv, (t - t_rev) / 0.3 if t >= t_rev else 0.0)
        if pop < 1:
            gi = gi.copy(); gi.putalpha(gi.getchannel("A").point(lambda a: int(a * pop)))
        im.alpha_composite(gi, (g.box[0], g.box[1]))
        find_label(im, g, lv)
        if prog: progress(im, g, *prog)
        if badge: badge_next(im, g, badge)
        if t >= t_rev:
            txt(im, g.q_xy, "Here it is!", 64, YELLOW, 6)
        elif t >= t_think:
            txt(im, g.q_xy, q_text, 56 if g.portrait else 62, YELLOW, 6)
            left = max(0.0, (t_rev if reveal else total) - t); bar(im, g, min(1, left / think), max(1, math.ceil(left)))
        if hook: hook_banner(im, g, hook, t, hook_dur)
    def key(t):
        if t < 0.35 and not instant: return None
        if hook and t < hook_dur: return None
        if t >= t_rev: return ("r", min(4, int((t - t_rev) / 0.1)))
        if t < t_think: return "a"
        return ("c", int((t - t_think) * 10))
    return Seg(total, draw, key, snd, chip)

# ---------------- long video ----------------
def make_long(outdir, prefix, seed):
    g = G(False); lvs = build_levels(seed); N = len(lvs); segs = []; last = lvs[-1]
    segs.append(level_seg(g, last, f"LEVEL {N} / {N} • IMPOSSIBLE", think=1, reveal=False, instant=True,
                          hook="MOST PEOPLE MISS IT", hook_dur=2.6,
                          intro=f"Can you find the odd emoji? Level {N} is almost impossible. The answer is at the very end!"))
    for i, (lv, (n, pl, th, tier)) in enumerate(zip(lvs, PLAN)):
        name, col = TIERS[tier]; chip = f"LEVEL {i + 1} / {N} • " + ("SPEED ROUND" if i in SPEED else name)
        if i == 0:
            segs.append(card(g, [("Let's start easy!", 90, WHITE), ("LEVEL 1", 120, YELLOW)], "Let's start easy. Level 1!", 1.2, 0.1, chip))
        elif i == SPEED[0]:
            segs.append(card(g, [("SPEED ROUND!", 120, YELLOW), ("3 levels • 5 seconds each", 70, WHITE)],
                             "Speed round! Three levels, only five seconds each. Go!", 2.0, 0.1, chip))
        elif i not in SPEED:
            label = f"BIGGER GRID: {n} x {n}" if PLAN[i - 1][0] != n else name
            segs.append(card(g, [(f"LEVEL {i + 1}", 120, YELLOW), (label, 76, col)],
                             f"Level {i + 1}." + (f" Bigger grid!" if PLAN[i - 1][0] != n else f" {name.lower()}."), 1.2, 0.1, chip))
        segs.append(level_seg(g, lv, chip, think=th, hold=2.6 if (tier == 0 or i in SPEED) else 3.2, prog=(i, N),
                              intro=("Here is the one from the start! Find the odd emoji!" if i == N - 1 else
                                     ("Five seconds! Go!" if i in SPEED else None))))
        if i + 1 in (5, 16):
            segs.append(card(g, [("Still perfect?", 104, YELLOW), (f"Found all {i + 1}?", 84, WHITE), ("Type YES in the comments!", 58, SOFT)],
                             f"Did you find all {i + 1} so far? Type yes in the comments!", 2.4, 0.2, chip))
        if i + 1 in (11, 22):
            segs.append(card(g, [(f"LEVEL {N} is coming...", 92, YELLOW), ("the one from the start!", 64, WHITE), ("Stay until the end!", 70, WHITE)],
                             f"Level {N} is coming. The one from the start! Stay until the end to see the answer!", 2.2, 0.2, chip))
        if i + 1 in (9, 19, 26):
            segs.append(card(g, [("Found it fast?", 86, WHITE), ("SMASH LIKE 👍".replace(" 👍", ""), 110, YELLOW), ("and subscribe to QuizNado07", 52, SOFT)],
                             "Found it fast? Smash like, and subscribe to QuizNado07!", 3, 0.4, chip))
    segs.append(card(g, [("What's your score?", 96, YELLOW), (f"___ / {N}", 124, WHITE), ("Comment it below!", 60, SOFT)],
                     f"How many did you find out of {N}? Write your score in the comments!", 3, 0.8))
    segs.append(end_screen_seg(g))
    total = render(segs, g, f"{outdir}/{prefix}.mp4")
    json.dump(lvs, open(f"{outdir}/{prefix}_answers.json", "w"), ensure_ascii=False)
    thumbnail(f"{outdir}/{prefix}_THUMBNAIL.jpg", lvs)
    print("long", round(total, 1), "s", flush=True)

# ---------------- Short (posted at the same time; Related video = long) ----------------
def make_teaser(out, seed, long_thumb):
    g = G(True); g.footer = ""; lvs = build_levels(seed); N = len(lvs); hard = lvs[-1]; chip = f"LEVEL {N} • IMPOSSIBLE"
    segs = [level_seg(g, hard, chip, think=1, reveal=False, instant=True, hook="MOST PEOPLE MISS IT", hook_dur=2.6,
                      intro="Most people miss this one! But first, two quick ones!"),
            level_seg(g, lvs[4], "WARM-UP 1/2", think=4, hold=1.6, badge=f"NEXT: LEVEL {N}", reveal_say="There!"),
            level_seg(g, lvs[15], "WARM-UP 2/2", think=5, hold=1.6, badge=f"NEXT: LEVEL {N}", reveal_say="Got it?"),
            level_seg(g, hard, chip, think=6, reveal=False, q_text="No answer here...", intro=f"Now level {N}! Find the odd emoji!")]
    th = Image.open(long_thumb).convert("RGBA"); snd = []
    d = say(snd, 0.1, "Did you find it? The answer is in the full video, out now on QuizNado07!") + 0.4
    def draw(im, t):
        im.alpha_composite(grid_img(g, hard, 0), (g.box[0], g.box[1]))
        im.alpha_composite(Image.new("RGBA", im.size, (20, 8, 50, 200)))
        txt(im, (g.W / 2, 560), "FULL VIDEO OUT NOW!", 76, YELLOW, 8)
        txt(im, (g.W / 2, 660), "Answer + 30 levels inside", 58, WHITE, 6)
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
    print("teaser", round(total, 1), "s; level", N, hard["base"], "->", hard["odd"], where(hard), flush=True)

# ---------------- thumbnail (odd one present, never pointed at) ----------------
def thumbnail(path, lvs):
    import numpy as np
    y, x = np.mgrid[0:1080, 0:1920]; t = ((y / 1080 + x / 1920) / 2)[..., None]
    im = Image.fromarray((np.array((40, 200, 255)) * (1 - t) + np.array((110, 60, 255)) * t).astype(np.uint8), "RGB").convert("RGBA")
    im.alpha_composite(user_logo(120), (30, 25))
    lv = dict(lvs[-6]); lv["n"] = 6; lv["cell"] = [4, 1]           # 6x6 for readability on phones
    g = G(False); g.box = (1000, 110, 1840, 950); im.alpha_composite(grid_img(g, lv, 0), (1000, 110))
    d = ImageDraw.Draw(im); s = "ODD EMOJI"; f = F(110); w = d.textlength(s, font=f) + 90
    e = emo(lv["base"], 200); im.alpha_composite(e, (290, 70)); e2 = emo(lv["odd"], 200); im.alpha_composite(e2, (540, 70))
    d.text((515, 170), "≠", font=F(120), fill=WHITE, anchor="mm", stroke_width=8, stroke_fill=DEEP)
    d.rounded_rectangle([500 - w / 2, 330, 500 + w / 2, 490], radius=50, fill=WHITE); d.text((500, 410), s, font=f, fill=DEEP, anchor="mm")
    txt(im, (500, 640), "CAN YOU", 130, WHITE, 11); txt(im, (500, 800), "FIND IT?", 165, YELLOW, 13)
    pts = [((1 - u) ** 2 * 870 + 2 * (1 - u) * u * 950 + u * u * 1005, (1 - u) ** 2 * 900 + 2 * (1 - u) * u * 1010 + u * u * 860) for u in [i / 40 for i in range(41)]]
    pts = [(px, py - 560) for px, py in pts]                       # arrow into the top rows (the odd one is lower)
    d.line(pts[:-3], fill=WHITE, width=44, joint="curve"); d.line(pts[:-3], fill=(220, 38, 38), width=28, joint="curve")
    ang = math.atan2(pts[-1][1] - pts[-4][1], pts[-1][0] - pts[-4][0]); p2 = pts[-1]
    for s_, col in ((58, WHITE), (42, (220, 38, 38))):
        d.polygon([(p2[0] + s_ * math.cos(ang), p2[1] + s_ * math.sin(ang)),
                   (p2[0] - 1.6 * s_ * math.cos(ang) + s_ * math.cos(ang + math.pi / 2), p2[1] - 1.6 * s_ * math.sin(ang) + s_ * math.sin(ang + math.pi / 2)),
                   (p2[0] - 1.6 * s_ * math.cos(ang) - s_ * math.cos(ang + math.pi / 2), p2[1] - 1.6 * s_ * math.sin(ang) - s_ * math.sin(ang + math.pi / 2))], fill=col)
    st = Image.new("RGBA", (560, 130), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
    sd.rounded_rectangle([0, 0, 559, 129], radius=24, fill=(220, 38, 38), outline=WHITE, width=8)
    sd.text((280, 65), "IMPOSSIBLE", font=F(84), fill=WHITE, anchor="mm")
    st = st.rotate(-10, expand=True, resample=Image.BICUBIC); im.alpha_composite(st, (1440 - st.width // 2, 70 - st.height // 2 + 20))
    im.convert("RGB").resize((1280, 720), Image.LANCZOS).save(path, quality=93)

if __name__ == "__main__":
    a = sys.argv
    if a[1] == "long": make_long(a[2], a[3], int(a[4]))
    elif a[1] == "teaser": make_teaser(a[2], int(a[3]), a[4])
    elif a[1] == "frames":
        from weights import background
        lvs = build_levels(int(a[3]))
        for i in (0, 12, 29):
            g = G(False); s = level_seg(g, lvs[i], f"LEVEL {i + 1}", think=PLAN[i][2], prog=(i, 30))
            for tt, nm in ((3.0, "ask"), (s.dur - 0.4, "rev")):
                im = background(g, s.chip); s.draw(im, tt); im.convert("RGB").resize((960, 540)).save(f"{a[2]}/o_{i}_{nm}.png")
        thumbnail(f"{a[2]}/thumb.jpg", lvs)

"""QuizNado07 'Memory test' — memorize where the colors are, cards flip to numbers, "Where is YELLOW?".
python3 memory.py long   OUT_DIR PREFIX SEED      -> 20 levels (4 -> 16 colors), 10+ min, thumbnail, answers
python3 memory.py teaser OUT.mp4 SEED THUMB       -> hook-first loop Short: hardest grid first, warm-up, hard one, last question NO answer
python3 memory.py short  OUT.mp4 SEED             -> the simple 6-card example Short
"""
import sys, os, math, random, json
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import F, user_logo, tick, ding, whoosh, ease, shadowed, YELLOW, WHITE, DEEP
from weights import Seg, say, render, txt, bar, card, end_screen_seg, emoji, TIERS, RED, SOFT

COLORS = {"RED": (220, 38, 38), "BLUE": (37, 99, 235), "GREEN": (22, 163, 74), "YELLOW": (250, 204, 21),
          "ORANGE": (249, 115, 22), "PINK": (236, 72, 153), "PURPLE": (147, 51, 234), "BROWN": (120, 53, 15),
          "WHITE": (245, 245, 245), "BLACK": (24, 24, 30), "GRAY": (148, 163, 184), "LIGHT BLUE": (56, 189, 248),
          "LIME": (163, 230, 53), "NAVY": (30, 41, 110), "MAROON": (127, 29, 29), "TEAL": (13, 148, 136),
          "GOLD": (202, 150, 4)}
BASIC = ["RED", "BLUE", "GREEN", "YELLOW", "ORANGE", "PINK", "PURPLE", "BROWN", "WHITE", "BLACK",
         "GRAY", "LIGHT BLUE", "LIME", "NAVY", "MAROON", "TEAL"]
LOOKALIKE = ["RED", "MAROON", "PINK", "ORANGE", "GOLD", "YELLOW", "LIME", "GREEN", "TEAL", "LIGHT BLUE",
             "BLUE", "NAVY", "PURPLE", "BROWN", "GRAY", "WHITE"]
NUMC = (109, 40, 217)
# (cards, cols, rows, memorize s, questions, think s, tier, look-alike colors?)
PLAN = ([(4, 2, 2, 5, 2, 4, 0, False)] * 3 + [(6, 3, 2, 3, 2, 4, 1, False)] * 3 +          # 4-6: SPEED ROUND (3 s)
        [(9, 3, 3, 7, 3, 5, 2, False)] * 4 + [(12, 4, 3, 8, 3, 5, 3, False)] * 4 +
        [(16, 4, 4, 9, 3, 6, 4, False)] * 4 + [(16, 4, 4, 7, 4, 6, 5, True)] * 2)
SPEED = (3, 4, 5)

class G:
    def __init__(self, cols=2, rows=3, landscape=False):
        self.landscape = landscape; self.portrait = not landscape; self.cols, self.rows = cols, rows
        if landscape:
            self.W, self.H = 1920, 1080; self.chip_y = 95
            box = (70, 165, 1130, 1045); self.right = 1545
            self.timer = (1240, 790, 1800, 830); self.count = (1860, 810, 44); self.title_y = 400
        else:
            self.W, self.H = 1080, 1920; self.chip_y = 405
            box = (110, 610, 970, 1600); self.right = 540
            self.timer = (180, 1660, 1000, 1695); self.count = (95, 1677, 50); self.title_y = 525
        x0, y0, x1, y1 = box; gap = 30 if cols * rows <= 9 else 22
        cw = (x1 - x0 - gap * (cols - 1)) / cols; ch = (y1 - y0 - gap * (rows - 1)) / rows
        if landscape:   # square cards that always fit the box (smaller grids stay a sensible size)
            cw = ch = min(cw, ch, 330 if cols * rows <= 6 else 999)
        tw, th = cols * cw + gap * (cols - 1), rows * ch + gap * (rows - 1)
        ox, oy = x0 + (x1 - x0 - tw) / 2, y0 + (y1 - y0 - th) / 2
        self.cells = [(ox + c * (cw + gap), oy + r * (ch + gap), ox + c * (cw + gap) + cw, oy + r * (ch + gap) + ch)
                      for r in range(rows) for c in range(cols)]

_face_cache = {}
def face(lv, slot, kind, box):
    w, h = int(box[2] - box[0]), int(box[3] - box[1])
    key = (kind, lv["colors"][slot] if kind == "color" else lv["nums"][slot], w, h)
    if key in _face_cache: return _face_cache[key]
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); rad = max(14, int(min(w, h) * 0.1))
    if kind == "color":
        c = COLORS[lv["colors"][slot]]
        for y in range(h):
            k = 1.08 - 0.2 * y / h; d.line([(0, y), (w, y)], fill=tuple(min(255, int(v * k)) for v in c) + (255,))
        m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=rad, fill=255); im.putalpha(m)
        ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, h - 1], radius=rad, outline=WHITE, width=max(4, w // 55))
    else:
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=rad, fill=WHITE)
        r = min(w, h) * 0.40; cx, cy = w / 2, h / 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=NUMC)
        d.text((cx, cy + 3), str(lv["nums"][slot]), font=F(int(r * (1.25 if lv["nums"][slot] < 10 else 0.95))), fill=WHITE, anchor="mm")
    _face_cache[key] = im; return im

def draw_cards(im, g, lv, revealed, flips, t, glow=None):
    for s, box in enumerate(g.cells):
        kind = "color" if s in revealed else "num"; sx = 1.0
        if s in flips:
            t0, a, b = flips[s]; p = min(1, max(0, (t - t0) / 0.36))
            kind = a if p < 0.5 else b; sx = max(0.04, abs(math.cos(math.pi * p)))
        f = face(lv, s, kind, box)
        if sx < 0.999: f = f.resize((max(2, int(f.width * sx)), f.height))
        x = int((box[0] + box[2]) / 2 - f.width / 2); y = int(box[1])
        if glow == s:
            gl = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).rounded_rectangle(
                [box[0] - 12, box[1] - 12, box[2] + 12, box[3] + 12], radius=30, outline=YELLOW, width=11); im.alpha_composite(gl)
        sh = Image.new("RGBA", f.size, (0, 0, 0, 0)); sh.putalpha(f.getchannel("A").point(lambda v: int(v * .35)))
        im.alpha_composite(sh, (x + 7, y + 10)); im.alpha_composite(f, (x, y))

def color_word(im, xy, color, size):
    c = COLORS[color]; dark = sum(c) < 260 or color in ("BLUE", "PURPLE", "MAROON", "NAVY", "BROWN", "TEAL")
    ImageDraw.Draw(im).text(xy, color + "?", font=F(size), fill=c, anchor="mm", stroke_width=8, stroke_fill=WHITE if dark else DEEP)

def ask_text(im, g, color):
    if g.landscape:
        txt(im, (g.right, g.title_y - 70), "WHERE IS", 78, WHITE, 7); color_word(im, (g.right, g.title_y + 45), color, 104)
    else:
        d = ImageDraw.Draw(im); f = F(74); a = "WHERE IS "; wa = d.textlength(a, font=f); wb = d.textlength(color + "?", font=f)
        x = g.W / 2 - (wa + wb) / 2
        d.text((x, g.title_y), a, font=f, fill=WHITE, anchor="lm", stroke_width=7, stroke_fill=DEEP)
        color_word(im, (x + wa + wb / 2, g.title_y), color, 74)

def title(im, g, s, size=70, col=YELLOW, sub=None):
    if g.landscape:
        d = ImageDraw.Draw(im)
        while size > 36 and d.textlength(s, font=F(size)) > 700: size -= 2
        txt(im, (g.right, g.title_y - 40), s, size, col, 7)
        if sub: txt(im, (g.right, g.title_y + 60), sub, 50, WHITE, 5)
    else:
        txt(im, (g.W / 2, g.title_y), s, size, col, 7)

def progress(im, g, cur, N):
    if not g.landscape or cur is None: return
    d = ImageDraw.Draw(im); x0, y, step = 1250, 960, 29
    d.text((x0 - 10, y - 50), "YOUR PROGRESS", font=F(30), fill=SOFT, anchor="lm")
    for k in range(N - 1):
        x = x0 + k * step
        if k < cur: d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=YELLOW)
        elif k == cur: d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=WHITE, outline=YELLOW, width=4)
        else: d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(255, 255, 255, 70))
    e = emoji("🏆", 54 if cur == N - 1 else 44); im.alpha_composite(e, (int(x0 + (N - 1) * step - e.width / 2), int(y - e.height / 2)))

def hook_banner(im, g, text, t, dur):
    if t >= dur: return
    a = min(1, (dur - t) / 0.25)
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); size = 84
    maxw = (g.cells[-1][2] - g.cells[0][0]) + 40
    while size > 40 and d.textlength(text, font=F(size)) + 90 > maxw: size -= 2
    f = F(size); w = d.textlength(text, font=f) + 90
    cx = (g.cells[0][0] + g.cells[-1][2]) / 2; cy = (g.cells[0][1] + g.cells[-1][3]) / 2; h = size * 1.8
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=34, fill=(254, 44, 85), outline=WHITE, width=6)
    d.text((cx, cy), text, font=f, fill=WHITE, anchor="mm")
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a))); im.alpha_composite(lay)

# ---------------- levels ----------------
def make_level(rnd, n, look=False):
    pool = (LOOKALIKE if look else BASIC)[:]
    colors = rnd.sample(pool[:max(n, 6)] if not look else pool, n) if n < len(pool) else pool[:n]
    if n <= 6 and not look: colors = rnd.sample(BASIC[:8], n)
    rnd.shuffle(colors); nums = list(range(1, n + 1)); rnd.shuffle(nums)
    asks = colors[:]; rnd.shuffle(asks)
    return {"colors": colors, "nums": nums, "asks": asks}

def build_levels(seed):
    rnd = random.Random(seed)
    return [make_level(rnd, n, look) for (n, c, r, m, q, th, tier, look) in PLAN]

# ---------------- segments ----------------
def mem_seg(g, lv, chip, mem, intro, prog=None, banner=None, instant_ticks=True):
    n = len(lv["colors"]); snd = []; vd = say(snd, 0.1, intro); t0 = max(0.0, vd + 0.2 - mem) if False else 0.0
    dur = max(mem, vd + 0.5)
    for s in range(int(math.ceil(mem))): snd.append((dur - mem + s, tick() * (1.4 if s >= mem - 3 else 1)))
    def draw(im, t):
        draw_cards(im, g, lv, set(range(n)), {}, t)
        title(im, g, "MEMORIZE THE COLORS!", 64 if g.landscape else 70, YELLOW, f"{n} colors • {int(mem)} seconds" if g.landscape else None)
        left = min(mem, max(0.0, dur - t)); bar(im, g, left / mem, max(1, math.ceil(left)))
        progress(im, g, *(prog or (None, None)))
        if banner: hook_banner(im, g, banner[0], t, banner[1])
    def key(t):
        if banner and t < banner[1]: return None
        return ("m", int(t * 10))
    return Seg(dur, draw, key, snd, chip)

def flip_seg(g, lv, chip, prog=None):
    n = len(lv["colors"]); snd = [(0.0, whoosh() * 0.8)]; vd = say(snd, 0.45, "Time's up!")
    fl = {s: (0.04 * s, "color", "num") for s in range(n)}
    def draw(im, t):
        draw_cards(im, g, lv, set(range(n)), fl, t); title(im, g, "TIME'S UP!", 84, YELLOW)
        progress(im, g, *(prog or (None, None)))
    return Seg(max(1.3, vd + 0.6), draw, lambda t: ("f", min(30, int(t * 20))), snd, chip)

def q_seg(g, lv, revealed, color, think, reveal, chip, prog=None, last_label=None):
    rv = set(revealed); slot = lv["colors"].index(color); num = lv["nums"][slot]
    snd = []; vd = say(snd, 0.1, f"Where is {color.lower()}?"); t_th = vd + 0.25
    for s in range(think): snd.append((t_th + s, tick() * (1.4 if s >= think - 3 else 1)))
    t_rev = t_th + think
    if reveal:
        snd.append((t_rev, ding())); rvd = say(snd, t_rev + 0.3, f"Number {num}!"); dur = t_rev + max(1.6, rvd + 0.6)
    else: dur = t_rev
    def draw(im, t):
        fl = {slot: (t_rev, "num", "color")} if (reveal and t >= t_rev) else {}
        draw_cards(im, g, lv, rv, fl, t, glow=slot if (reveal and t >= t_rev + 0.3) else None)
        ask_text(im, g, color); progress(im, g, *(prog or (None, None)))
        if t < t_rev or not reveal:
            left = min(think, max(0.0, t_rev - t)); bar(im, g, left / think, max(1, math.ceil(left)))
            if last_label and t >= t_th: txt(im, (g.right, g.title_y + 190) if g.landscape else (g.W / 2, 1745), last_label, 46, WHITE, 5)
        else:
            txt(im, (g.right, 810) if g.landscape else (g.W / 2, 1678), f"NUMBER {num}!", 70 if g.landscape else 64, YELLOW, 6)
    def key(t):
        if t < t_th: return "a"
        if t < t_rev: return ("c", int((t - t_th) * 10))
        return ("r", min(15, int((t - t_rev) * 20)))
    if reveal: revealed.add(slot)
    return Seg(dur, draw, key, snd, chip)

def level_segs(g, lv, spec, chip, prog=None, intro=None, n_q=None, mem=None, banner=None, last_no_answer=False):
    n, c, r, m, q, th, tier, look = spec; revealed = set(); segs = []
    segs.append(mem_seg(g, lv, chip, mem or m, intro or f"Memorize the colors! {int(mem or m)} seconds!", prog, banner))
    segs.append(flip_seg(g, lv, chip, prog))
    asks = lv["asks"][:(n_q or q)]
    for k, col in enumerate(asks):
        no = last_no_answer and k == len(asks) - 1
        segs.append(q_seg(g, lv, revealed, col, th, not no, chip, prog, "No answer here..." if no else None))
    return segs

# ---------------- long video ----------------
def make_long(outdir, prefix, seed):
    lvs = build_levels(seed); N = len(lvs); segs = []
    tot_q = sum(p[4] for p in PLAN); last = lvs[-1]; sp_last = PLAN[-1]
    gl = G(sp_last[1], sp_last[2], True)
    # hook: the final 16 look-alike colors in the first frame
    snd = []; vd = say(snd, 0.1, f"Can you remember sixteen colors? Level {N} is the hardest memory test ever. Stay to the end to try it!")
    def d_hook(im, t):
        draw_cards(im, gl, last, set(range(len(last["colors"]))), {}, t)
        title(im, gl, f"LEVEL {N}: 16 COLORS", 64, YELLOW, "Can you remember them?")
        hook_banner(im, gl, "MOST PEOPLE FAIL THIS", t, 2.6)
    segs.append(Seg(vd + 0.5, d_hook, lambda t: None if t < 2.6 else "h", snd, f"LEVEL {N} / {N} • IMPOSSIBLE"))
    segs.append(card(gl, [("Let's start easy!", 90, WHITE), ("1 point per right answer", 60, SOFT)],
                     f"Let's start easy! One point for every right answer. {tot_q} points in total!", 2.0, 0.2))
    for i, (lv, spec) in enumerate(zip(lvs, PLAN)):
        n, c, r, m, q, th, tier, look = spec; name, col = TIERS[tier]; g = G(c, r, True)
        chip = f"LEVEL {i + 1} / {N} • " + ("SPEED ROUND" if i in SPEED else name)
        if i == SPEED[0]:
            segs.append(card(g, [("SPEED ROUND!", 120, YELLOW), ("only 3 seconds to memorize", 66, WHITE)],
                             "Speed round! Only three seconds to memorize. Ready?", 2.0, 0.1, chip))
        elif i > 0 and PLAN[i - 1][0] != n:
            segs.append(card(g, [("MORE COLORS!", 110, YELLOW), (f"{n} colors now", 76, WHITE)], f"More colors! Now {n} colors!", 1.8, 0.1, chip))
        if look and not PLAN[i - 1][7]:
            segs.append(card(g, [("IMPOSSIBLE LEVELS", 100, RED), ("the colors look alike!", 66, WHITE)],
                             "Impossible levels! Now the colors look alike. Focus!", 2.2, 0.2, chip))
        intro = (f"Level {i + 1}! Memorize! Three seconds!" if i in SPEED else
                 (f"Here it is! Level {N}! Seven seconds!" if i == N - 1 else f"Level {i + 1}. {int(m)} seconds!"))
        segs += level_segs(g, lv, spec, chip, (i, N), intro)
        if i + 1 in (3, 14):
            segs.append(card(g, [("Still perfect?", 104, YELLOW), ("Type YES in the comments!", 64, WHITE)],
                             "Still perfect? Type yes in the comments!", 2.2, 0.2, chip))
        if i + 1 in (8, 16):
            segs.append(card(g, [(f"LEVEL {N} is coming...", 92, YELLOW), ("16 look-alike colors!", 64, WHITE), ("Stay until the end!", 70, WHITE)],
                             f"Level {N} is coming. Sixteen colors that look alike! Stay until the end!", 2.2, 0.2, chip))
        if i + 1 in (6, 12, 18):
            segs.append(card(g, [("Enjoying it?", 86, WHITE), ("SUBSCRIBE & LIKE", 104, YELLOW), ("It really helps QuizNado07", 50, SOFT)],
                             "If you like it so far, subscribe and like! It really helps QuizNado07.", 3, 0.4, chip))
    segs.append(card(gl, [("What's your score?", 96, YELLOW), (f"___ / {tot_q}", 124, WHITE), ("Comment it below!", 60, SOFT)],
                     f"How many points did you get out of {tot_q}? Write your score in the comments!", 3, 0.8))
    segs.append(end_screen_seg(gl))
    total = render(segs, gl, f"{outdir}/{prefix}.mp4")
    json.dump(lvs, open(f"{outdir}/{prefix}_answers.json", "w"))
    thumbnail(f"{outdir}/{prefix}_THUMBNAIL.jpg", last)
    print("long", round(total, 1), "s;", tot_q, "points", flush=True)

# ---------------- teaser Short (posted at the same time, Related video = long) ----------------
def make_teaser(out, seed, long_thumb):
    lvs = build_levels(seed); N = len(lvs); hi = 15          # level 16 (16 colors) — its answers are in the long video
    lv, spec = lvs[hi], PLAN[hi]; g = G(spec[1], spec[2], False); g.footer = ""
    w = lvs[1]; gw = G(PLAN[1][1], PLAN[1][2], False)
    segs = []
    # hook: 16 colors in the first frame + banner, memorize 6 s
    segs.append(mem_seg(g, lv, f"LEVEL {hi + 1} • 16 COLORS", 6, "Most people fail this! Sixteen colors, six seconds. Memorize!",
                        banner=("MOST PEOPLE FAIL THIS", 2.4)))
    segs.append(flip_seg(g, lv, f"LEVEL {hi + 1} • 16 COLORS"))
    rv = set(); asks = lv["asks"][:3]
    segs.append(q_seg(g, lv, rv, asks[0], 4, True, f"LEVEL {hi + 1} • QUESTION 1/3"))
    segs.append(q_seg(g, lv, rv, asks[1], 4, True, f"LEVEL {hi + 1} • QUESTION 2/3"))
    segs.append(q_seg(g, lv, rv, asks[2], 5, False, f"LEVEL {hi + 1} • LAST ONE", last_label="Answer in the full video!"))
    th = Image.open(long_thumb).convert("RGBA"); snd = []
    d = say(snd, 0.1, f"Where is {asks[2].lower()}? The answer is in the full video, out now on QuizNado07! Twenty levels!") + 0.4
    def draw(im, t):
        draw_cards(im, g, lv, rv, {}, t)
        im.alpha_composite(Image.new("RGBA", im.size, (20, 8, 50, 200)))
        txt(im, (g.W / 2, 560), "FULL VIDEO OUT NOW!", 76, YELLOW, 8)
        txt(im, (g.W / 2, 660), "Answer + 20 levels inside", 58, WHITE, 6)
        tw = 940; t2 = th.resize((tw, int(tw * th.height / th.width)), Image.LANCZOS)
        shadowed(im, (70, 740, 70 + tw, 740 + t2.height), 24, WHITE, blur=16, off=10, alpha=110)
        m = Image.new("L", t2.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, t2.width - 1, t2.height - 1], radius=24, fill=255)
        im.paste(t2, (70, 740), m)
        dd = ImageDraw.Draw(im); cx, cy = 70 + tw - 70, 740 + t2.height - 55
        dd.ellipse([cx - 48, cy - 48, cx + 48, cy + 48], fill=RED); dd.polygon([(cx - 15, cy - 24), (cx - 15, cy + 24), (cx + 26, cy)], fill=WHITE)
        y = 740 + t2.height + 75; pulse = 1 + 0.03 * math.sin(t * 6)
        dd.rounded_rectangle([g.W / 2 - 400 * pulse, y + 10, g.W / 2 + 400 * pulse, y + 115], radius=52, fill=RED, outline=WHITE, width=5)
        dd.text((g.W / 2, y + 62), "SUBSCRIBE & LIKE", font=F(58), fill=WHITE, anchor="mm")
    segs.append(Seg(max(4.0, d), draw, lambda t: ("e", int(t * 10) % 11), snd, "QuizNado07"))
    total = render(segs, g, out)
    slot = lv["colors"].index(asks[2])
    print("teaser", round(total, 1), "s; level", hi + 1, "asks", asks, "; last =", asks[2], "number", lv["nums"][slot], flush=True)

# ---------------- thumbnail (no answers) ----------------
def thumbnail(path, lv):
    import numpy as np
    y, x = np.mgrid[0:1080, 0:1920]; t = ((y / 1080 + x / 1920) / 2)[..., None]
    im = Image.fromarray((np.array((40, 200, 255)) * (1 - t) + np.array((110, 60, 255)) * t).astype(np.uint8), "RGB").convert("RGBA")
    im.alpha_composite(user_logo(120), (30, 25))
    g = G(4, 4, True); g.cells = []
    x0, y0, cs, gap = 1010, 110, 196, 18
    g.cells = [(x0 + c * (cs + gap), y0 + r * (cs + gap), x0 + c * (cs + gap) + cs, y0 + r * (cs + gap) + cs) for r in range(4) for c in range(4)]
    shown = {0, 1, 2, 4, 5, 8, 9, 12, 13, 14}               # half colors, half already numbers
    draw_cards(im, g, lv, shown, {}, 0)
    e = emoji("🧠", 250); im.alpha_composite(e, (370, 60))
    d = ImageDraw.Draw(im); s = "MEMORY TEST"; f = F(110); w = d.textlength(s, font=f) + 90
    d.rounded_rectangle([500 - w / 2, 340, 500 + w / 2, 500], radius=50, fill=WHITE)
    d.text((500, 420), s, font=f, fill=DEEP, anchor="mm")
    txt(im, (500, 640), "16 COLORS", 130, WHITE, 11); txt(im, (500, 800), "CAN YOU?", 165, YELLOW, 13)
    # red arrow into the grid + IMPOSSIBLE stamp
    pts = [((1 - u) ** 2 * 760 + 2 * (1 - u) * u * 900 + u * u * 990, (1 - u) ** 2 * 960 + 2 * (1 - u) * u * 1040 + u * u * 900) for u in [i / 40 for i in range(41)]]
    d.line(pts[:-3], fill=WHITE, width=44, joint="curve"); d.line(pts[:-3], fill=(220, 38, 38), width=28, joint="curve")
    ang = math.atan2(pts[-1][1] - pts[-4][1], pts[-1][0] - pts[-4][0]); p2 = pts[-1]
    for s_, col in ((58, WHITE), (42, (220, 38, 38))):
        d.polygon([(p2[0] + s_ * math.cos(ang), p2[1] + s_ * math.sin(ang)),
                   (p2[0] - 1.6 * s_ * math.cos(ang) + s_ * math.cos(ang + math.pi / 2), p2[1] - 1.6 * s_ * math.sin(ang) + s_ * math.sin(ang + math.pi / 2)),
                   (p2[0] - 1.6 * s_ * math.cos(ang) - s_ * math.cos(ang + math.pi / 2), p2[1] - 1.6 * s_ * math.sin(ang) - s_ * math.sin(ang + math.pi / 2))], fill=col)
    st = Image.new("RGBA", (560, 130), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
    sd.rounded_rectangle([0, 0, 559, 129], radius=24, fill=(220, 38, 38), outline=WHITE, width=8)
    sd.text((280, 65), "IMPOSSIBLE", font=F(84), fill=WHITE, anchor="mm")
    st = st.rotate(-10, expand=True, resample=Image.BICUBIC); im.alpha_composite(st, (1440 - st.width // 2, 80 - st.height // 2 + 20))
    im.convert("RGB").resize((1280, 720), Image.LANCZOS).save(path, quality=93)

# ---------------- simple 6-card example Short ----------------
def make_short(out, seed):
    rnd = random.Random(seed); g = G(2, 3); lv = make_level(rnd, 6); n = 6
    segs = [mem_seg(g, lv, "MEMORY TEST • 5 SECONDS", 5, "Memory test! Remember where each color is. Five seconds!"), flip_seg(g, lv, "MEMORY TEST")]
    rv = set()
    for k, c in enumerate(lv["asks"][:3]): segs.append(q_seg(g, lv, rv, c, 4, True, f"QUESTION {k + 1}/4"))
    segs.append(q_seg(g, lv, rv, lv["asks"][3], 5, False, "LAST ONE • NO ANSWER"))
    total = render(segs, g, out); print("example short", round(total, 1), flush=True)

if __name__ == "__main__":
    a = sys.argv
    if a[1] == "long": make_long(a[2], a[3], int(a[4]))
    elif a[1] == "teaser": make_teaser(a[2], int(a[3]), a[4])
    elif a[1] == "short": make_short(a[2], int(a[3]))
    elif a[1] == "thumb":
        lvs = build_levels(int(a[3])); thumbnail(a[2], lvs[-1])
    elif a[1] == "frames":   # quick stills of a few levels (landscape)
        from weights import background
        lvs = build_levels(int(a[3]))
        for i in (0, 6, 10, 19):
            sp = PLAN[i]; g = G(sp[1], sp[2], True); lv = lvs[i]
            s = mem_seg(g, lv, f"LEVEL {i + 1}", sp[3], "Memorize!", (i, 20)); im = background(g, s.chip); s.draw(im, 1.0)
            im.convert("RGB").resize((960, 540)).save(f"{a[2]}/m_{i}_mem.png")
            rv = set(); q = q_seg(g, lv, rv, lv["asks"][0], sp[5], True, f"LEVEL {i + 1}", (i, 20))
            im = background(g, q.chip); q.draw(im, q.dur - 0.3); im.convert("RGB").resize((960, 540)).save(f"{a[2]}/m_{i}_rev.png")

"""QuizNado 'Find the missing weight' scale puzzles.
python3 weights.py long  OUT_DIR PREFIX SEED     -> PREFIX.mp4 (24 levels, 10+ min) + PREFIX_thumbnail.jpg, prints answers
python3 weights.py short OUT.mp4 TYPE SEED TRIO  -> one-puzzle Short (TYPE 4 or 5, TRIO like frog,sheep,horse)
"""
import sys, os, math, random, subprocess, json
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import F, gradient, user_logo, tts, music, tick, ding, whoosh, ease, shadowed, SR, FPS, YELLOW, WHITE, DEEP, PURPLE_T, GREEN

RED = (239, 68, 68); LAV = (196, 181, 253); SOFT = (221, 214, 254)
VOICE = "af_heart"
EMO = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109)
ANIMALS = {  # name: (emoji, weight range kg)
    "frog": ("🐸", (1, 3)), "chicken": ("🐔", (2, 4)), "rabbit": ("🐰", (2, 5)), "cat": ("🐱", (4, 7)),
    "fox": ("🦊", (6, 10)), "turtle": ("🐢", (11, 25)), "dog": ("🐶", (12, 30)), "penguin": ("🐧", (20, 35)),
    "sheep": ("🐑", (40, 70)), "pig": ("🐷", (80, 120)), "panda": ("🐼", (90, 125)), "bear": ("🐻", (150, 300)),
    "horse": ("🐴", (300, 500)), "cow": ("🐮", (400, 700))}
TIERS = [("EASY", (34, 197, 94)), ("MEDIUM", (234, 179, 8)), ("HARD", (249, 115, 22)),
         ("VERY HARD", (234, 88, 12)), ("EXPERT", (220, 38, 38)), ("IMPOSSIBLE", RED)]
# (trio, type, tier index)
LONG_PLAN = [
    (("frog", "cat", "dog"), 1, 0), (("chicken", "rabbit", "fox"), 1, 0), (("frog", "rabbit", "turtle"), 1, 0), (("cat", "fox", "dog"), 1, 0),
    (("cat", "dog", "sheep"), 2, 1), (("rabbit", "penguin", "sheep"), 2, 1), (("chicken", "dog", "pig"), 2, 1), (("fox", "turtle", "sheep"), 2, 1), (("frog", "sheep", "pig"), 2, 1),
    (("cat", "sheep", "pig"), 3, 2), (("dog", "sheep", "panda"), 3, 2), (("rabbit", "pig", "bear"), 3, 2), (("penguin", "sheep", "bear"), 3, 2), (("fox", "dog", "panda"), 3, 2),
    (("frog", "sheep", "horse"), 4, 3), (("cat", "pig", "horse"), 4, 3), (("dog", "bear", "cow"), 4, 3), (("chicken", "panda", "horse"), 4, 3), (("penguin", "pig", "cow"), 4, 3),
    (("frog", "pig", "cow"), 5, 4), (("rabbit", "bear", "horse"), 5, 4), (("cat", "panda", "cow"), 5, 4),
    (("fox", "sheep", "bear"), 5, 5), (("turtle", "pig", "horse"), 5, 5)]
TYPES = {  # three shown scales + question scale, as index lists into (A, B, C)
    1: ([0], [0, 1], [1, 2], [0, 1, 2]),
    2: ([0, 1], [0, 2], [1, 2], [0, 1, 2]),
    3: ([0, 0], [0, 1], [1, 2], [0, 1, 2]),
    4: ([0, 1, 2], [0, 1], [1, 2], [0, 2]),
    5: ([0, 0, 1], [0, 1], [1, 2, 2], [0, 1, 2])}

def make_puzzle(trio, typ, rnd):
    vals = [rnd.randint(*ANIMALS[a][1]) for a in trio]
    while len(set(vals)) < 3: vals = [rnd.randint(*ANIMALS[a][1]) for a in trio]
    sc = TYPES[typ]; sums = [sum(vals[i] for i in s) for s in sc]
    ans = sums[3]; shown = sums[:3]
    cands = {ans + d for d in (vals[0], -vals[0], max(2, round(ans * 0.1)), -max(2, round(ans * 0.1)), sum(shown) - ans)}
    cands |= {sum(shown), ans + 10, ans - 10}
    gap = 2 if ans < 20 else 3
    cands = sorted(c for c in cands if c > 0 and abs(c - ans) >= gap)
    cands = [c for i, c in enumerate(cands) if i == 0 or c - cands[i - 1] >= gap]
    rnd.shuffle(cands); opts = [ans] + cands[:2]; rnd.shuffle(opts)
    return {"trio": list(trio), "type": typ, "vals": vals, "scales": [list(s) for s in sc], "sums": sums,
            "answer": ans, "options": opts, "correct": opts.index(ans)}

# ---------------- drawing ----------------
_ecache = {}
def emoji(ch, size):
    k = (ch, size)
    if k not in _ecache:
        im = Image.new("RGBA", (160, 160), (0, 0, 0, 0)); ImageDraw.Draw(im).text((10, 10), ch, font=EMO, embedded_color=True)
        im = im.crop(im.getbbox()); r = size / max(im.size)
        _ecache[k] = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
    return _ecache[k]

def overlay_rect(im, box, radius, fill):
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(ov).rounded_rectangle(box, radius=radius, fill=fill); im.alpha_composite(ov)

def fit_font(d, text, maxw, size):
    while size > 20 and d.textlength(text, font=F(size)) > maxw: size -= 3
    return F(size)

def draw_scale(im, box, puzzle, idxs, label, mode="normal", pop=1.0):
    """mode: normal | question | answer. pop 0..1 scales the scale in."""
    x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0
    lay = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=30, fill=(255, 255, 255, 34))
    py = h * 0.70
    d.rectangle([w * 0.70, h * 0.30, w * 0.75, py], fill=(78, 80, 100))  # post
    d.rounded_rectangle([w * 0.05, py + h * 0.08, w * 0.81, py + h * 0.18], radius=8, fill=(70, 72, 92))
    d.rounded_rectangle([w * 0.06, py, w * 0.80, py + h * 0.09], radius=8, fill=(132, 136, 156))
    for fx in (0.10, 0.72): d.rectangle([w * fx, py + h * 0.18, w * (fx + 0.04), py + h * 0.22], fill=(50, 50, 66))
    dx0, dy0, dx1, dy1 = w * 0.50, h * 0.05, w * 0.95, h * 0.31
    d.rounded_rectangle([dx0, dy0, dx1, dy1], radius=14, fill=(58, 60, 78))
    lcd = {"normal": (214, 232, 206), "question": (253, 224, 71), "answer": (134, 239, 172)}[mode]
    d.rounded_rectangle([dx0 + 9, dy0 + 9, dx1 - 9, dy1 - 9], radius=8, fill=lcd)
    f = fit_font(d, label, dx1 - dx0 - 36, int((dy1 - dy0) * 0.62))
    d.text(((dx0 + dx1) / 2, (dy0 + dy1) / 2), label, font=f, fill=(30, 40, 30), anchor="mm")
    trio = puzzle["trio"]; n = len(idxs)
    avail = w * 0.62; base = min(h * 0.40, avail / n * 1.05)
    rank = {0: 0.78, 1: 0.92, 2: 1.06}
    sizes = [int(base * rank[i]) for i in idxs]; tot = sum(sizes) * 0.92
    x = w * 0.07 + (avail - tot) / 2
    for i, s in zip(idxs, sizes):
        e = emoji(ANIMALS[trio[i]][0], s); lay.alpha_composite(e, (int(x), int(py + 6 - e.height))); x += s * 0.92
    if pop < 1:
        p = ease(pop); sc = 0.6 + 0.4 * p
        lay2 = lay.resize((max(1, int(w * sc)), max(1, int(h * sc))), Image.BILINEAR)
        lay2.putalpha(lay2.getchannel("A").point(lambda a: int(a * p)))
        im.alpha_composite(lay2, (int(x0 + (w - lay2.width) / 2), int(y0 + (h - lay2.height) / 2)))
    else:
        im.alpha_composite(lay, (int(x0), int(y0)))

class Geo:
    def __init__(self, portrait):
        self.portrait = portrait
        if portrait:
            self.W, self.H = 1080, 1920; cw, ch, gx, gy, gap = 480, 400, 45, 470, 30
            self.cells = [(gx + c * (cw + gap), gy + r * (ch + gap), gx + c * (cw + gap) + cw, gy + r * (ch + gap) + ch) for r in range(2) for c in range(2)]
            self.q_xy = (540, 1365); ow = 310
            self.opts = [(30 + i * (ow + 25), 1420, 30 + i * (ow + 25) + ow, 1550) for i in range(3)]
            self.timer = (180, 1600, 1000, 1635); self.count = (95, 1617, 58); self.expl_y = 1640; self.chip_y = 405
        else:
            self.W, self.H = 1920, 1080; cw, ch, gx, gy, gap = 540, 400, 50, 165, 25
            self.cells = [(gx + c * (cw + gap), gy + r * (ch + gap), gx + c * (cw + gap) + cw, gy + r * (ch + gap) + ch) for r in range(2) for c in range(2)]
            self.q_xy = (1530, 235); self.opts = [(1220, 300 + i * 140, 1860, 300 + i * 140 + 115) for i in range(3)]
            self.timer = (1320, 745, 1860, 778); self.count = (1260, 761, 52); self.expl_y = 760; self.chip_y = 95

def background(g, chip):
    bg = gradient(g.W, g.H); d = ImageDraw.Draw(bg)
    if g.portrait:
        bg.alpha_composite(user_logo(200), ((g.W - 200) // 2, 145))
        d.text((g.W // 2, g.H - 150), "@QuizNado • Subscribe for more!", font=F(32), fill=SOFT, anchor="mm")
    else:
        bg.alpha_composite(user_logo(120), (30, 18))
        d.text((g.W - 30, g.H - 25), "@QuizNado", font=F(24), fill=SOFT, anchor="rm")
    if chip:
        f = F(40 if g.portrait else 34); w = d.textlength(chip, font=f) + 70
        d.rounded_rectangle([g.W / 2 - w / 2, g.chip_y - 36, g.W / 2 + w / 2, g.chip_y + 36], radius=36, fill=YELLOW)
        d.text((g.W / 2, g.chip_y), chip, font=f, fill=DEEP, anchor="mm")
    return bg

def txt(im, xy, s, size, col, stroke=6, anchor="mm"):
    ImageDraw.Draw(im).text(xy, s, font=F(size), fill=col, anchor=anchor, stroke_width=stroke, stroke_fill=DEEP)

def options(im, g, puzzle, reveal):
    for i, box in enumerate(g.opts):
        ok = reveal and i == puzzle["correct"]; wrong = reveal and not ok
        shadowed(im, box, 30, GREEN if ok else (LAV if wrong else WHITE), blur=10, off=6, alpha=60); d = ImageDraw.Draw(im)
        bx0, by0, bx1, by1 = box; bh = by1 - by0; r = bh * 0.32; cx = bx0 + 22 + r; cy = (by0 + by1) / 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE if ok else PURPLE_T)
        d.text((cx, cy), "ABC"[i], font=F(int(r * 1.2)), fill=GREEN if ok else WHITE, anchor="mm")
        t = f"{puzzle['options'][i]} kg"; tx = cx + r + 18
        d.text((tx, cy), t, font=fit_font(d, t, bx1 - tx - 20, int(bh * 0.42)), fill=WHITE if ok else DEEP, anchor="lm")

def explanation(im, g, puzzle):
    """emoji = value row(s)"""
    items = [(ANIMALS[a][0], v) for a, v in zip(puzzle["trio"], puzzle["vals"])]
    d = ImageDraw.Draw(im); es = 70 if g.portrait else 62; f = F(56 if g.portrait else 50)
    parts = []
    for ch, v in items:
        parts.append(("e", ch)); parts.append(("t", f" = {v} kg"))
    if g.portrait:
        rows = [parts]; y = g.expl_y + 60
    else:
        rows = [parts[i:i + 2] for i in range(0, 6, 2)]; y = g.expl_y + 10
    for row in rows:
        widths = [(es if k == "e" else d.textlength(s, font=f)) for k, s in row]; spacing = 40 if g.portrait else 0
        tw = sum(widths) + spacing * (len(row) // 2 - 1); x = (g.W / 2 if g.portrait else 1540) - tw / 2
        for (k, s), wdt in zip(row, widths):
            if k == "e": e = emoji(s, es); im.alpha_composite(e, (int(x), int(y - e.height / 2)))
            else:
                d.text((x, y), s, font=f, fill=WHITE, anchor="lm", stroke_width=4, stroke_fill=DEEP)
                x += spacing if g.portrait else 0
            x += wdt
        y += 85

def bar(im, g, frac, secs):
    x0, y0, x1, y1 = g.timer; overlay_rect(im, g.timer, (y1 - y0) // 2, (255, 255, 255, 50)); d = ImageDraw.Draw(im)
    if frac > 0.003:
        d.rounded_rectangle([x0, y0, x0 + (x1 - x0) * frac, y1], radius=(y1 - y0) // 2, fill=YELLOW if frac > 0.3 else RED)
    cx, cy, r = g.count; d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE)
    d.text((cx, cy), str(secs), font=F(int(r * 1.2)), fill=DEEP, anchor="mm")

# ---------------- segments ----------------
class Seg:
    def __init__(self, dur, draw, key, sounds, chip):
        self.dur, self.draw, self.key, self.sounds, self.chip = dur, draw, key, sounds, chip

def say(snd, at, text):
    a = tts(text, VOICE); snd.append((at, a)); return len(a) / SR

def card(g, lines, voice, min_dur=2.6, pad=0.6, chip=None):
    snd = []; d = say(snd, 0.2, voice) + 0.2 + pad if voice else 0
    def draw(im, t):
        lay = Image.new("RGBA", (g.W, g.H), (0, 0, 0, 0))
        tot = sum(s * 1.45 for _, s, _ in lines); y = g.H / 2 + (60 if g.portrait else 30) - tot / 2
        for s_, size, col in lines: txt(lay, (g.W / 2, y + size * 0.72), s_, size, col, 7); y += size * 1.45
        e = ease(t / 0.35)
        if e < 1:
            sc = 0.85 + 0.15 * e; w, h = int(g.W * sc), int(g.H * sc); l2 = lay.resize((w, h), Image.BILINEAR)
            l2.putalpha(l2.getchannel("A").point(lambda a: int(a * e))); im.alpha_composite(l2, ((g.W - w) // 2, (g.H - h) // 2))
        else: im.alpha_composite(lay)
    return Seg(max(min_dur, d), draw, lambda t: "s" if t >= 0.35 else None, snd, chip)

def puzzle_seg(g, pz, chip, *, think=15, intro=None, short=False):
    snd = []; pops = [0.3, 0.85, 1.4, 1.95]
    for p_ in pops: snd.append((p_, whoosh() * 0.6))
    vd = say(snd, 0.2, intro or "Find the missing weight!")
    t_opts = max(2.6, vd + 0.4); t_think = t_opts + 0.3
    for s in range(think): snd.append((t_think + s, tick() * (1.5 if s >= think - 3 else 1)))
    t_rev = t_think + think; snd.append((t_rev, ding()))
    names = ", ".join(f"{a} {v}" for a, v in zip(pz["trio"], pz["vals"]))
    rv = say(snd, t_rev + 0.3, f"The answer is {'ABC'[pz['correct']]}: {pz['answer']} kilograms! {names}.")
    total = t_rev + max(4.5, rv + 1.2)
    q_text = "Comment your answer!" if short else "What is the missing weight?"
    def draw(im, t):
        rev = t >= t_rev
        for k in range(4):
            box = g.cells[k]; pop = min(1, max(0, (t - pops[k]) / 0.35))
            if pop <= 0: continue
            if k < 3: draw_scale(im, box, pz, pz["scales"][k], f"{pz['sums'][k]} kg", "normal", pop)
            else: draw_scale(im, box, pz, pz["scales"][3], f"{pz['answer']} kg" if rev else "?", "answer" if rev else "question", pop)
        if t >= t_opts:
            txt(im, g.q_xy, "Here is the answer!" if rev else q_text, 58 if g.portrait else 50, WHITE if rev else YELLOW)
            options(im, g, pz, rev)
            if not rev and t >= t_think:
                left = t_rev - t; bar(im, g, left / think, max(1, math.ceil(left)))
            if rev: explanation(im, g, pz)
        if rev and t - t_rev < 0.25:
            im.alpha_composite(Image.new("RGBA", (g.W, g.H), (255, 255, 255, int(80 * (1 - (t - t_rev) / 0.25)))))
    def key(t):
        if t < 2.35 or (t_rev <= t < t_rev + 0.25): return None
        if t < t_opts: return "a"
        if t < t_think: return "b"
        if t < t_rev: return ("c", int((t - t_think) * 10))
        return "r"
    return Seg(total, draw, key, snd, chip)

def render(segs, g, out):
    total = sum(s.dur for s in segs); mix = music(total) * 0.8; t0 = 0
    for s in segs:
        for at, a in s.sounds:
            i = int((t0 + at) * SR); j = min(len(mix), i + len(a)); mix[i:j] += a[:j - i]
        t0 += s.dur
    wav = out + ".wav"; sf.write(wav, np.clip(mix, -1, 1), SR); tmp = out + ".part.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{g.W}x{g.H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE); bgs = {}
    for si, s in enumerate(segs):
        if s.chip not in bgs: bgs[s.chip] = background(g, s.chip)
        last_k = None; last_b = None
        for fi in range(int(round(s.dur * FPS))):
            t = fi / FPS; k = s.key(t)
            if k is not None and k == last_k: p.stdin.write(last_b); continue
            im = bgs[s.chip].copy(); s.draw(im, t); last_b = im.convert("RGB").tobytes(); last_k = k; p.stdin.write(last_b)
    p.stdin.close(); p.wait(); os.remove(wav)
    if p.returncode: raise SystemExit("ffmpeg failed")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", out + ".n.mp4"], check=True)
    os.remove(tmp); os.replace(out + ".n.mp4", out); return total

def make_long(outdir, prefix, seed):
    rnd = random.Random(seed); g = Geo(False); N = len(LONG_PLAN); segs = []; ans = []
    plan = list(LONG_PLAN)
    if seed != 41:  # new episodes: shuffle the animal trios inside each difficulty tier
        for tier in range(len(TIERS)):
            idx = [i for i, p in enumerate(plan) if p[2] == tier]; trios = [plan[i][0] for i in idx]; rnd.shuffle(trios)
            for i, tr in zip(idx, trios): plan[i] = (tr, plan[i][1], plan[i][2])
    segs.append(card(g, [("FIND THE MISSING WEIGHT", 100, YELLOW), (f"{N} levels • easy to impossible", 62, WHITE),
                         (f"Count your points: ___ / {N}", 54, SOFT)],
                     f"Welcome to QuizNado! {N} weight puzzles, from easy to impossible. Look at the scales, "
                     "find the missing weight, and count your points. Let's go!"))
    for i, (trio, typ, tier) in enumerate(plan):
        pz = make_puzzle(trio, typ, rnd); name, col = TIERS[tier]; chip = f"LEVEL {i + 1} / {N} • {name}"
        segs.append(card(g, [(f"LEVEL {i + 1}", 120, YELLOW), (name, 84, col)], f"Level {i + 1}. {name.lower()}.", 2.0, 0.3, chip))
        segs.append(puzzle_seg(g, pz, chip)); ans.append({"level": i + 1, "tier": name, **pz})
        if i + 1 in (5, 12, 19):
            segs.append(card(g, [("Enjoying it?", 86, WHITE), ("SUBSCRIBE & LIKE", 104, YELLOW), ("It really helps QuizNado", 50, SOFT)],
                             "If you liked it so far, subscribe and like! It really helps QuizNado.", 3, 0.5, chip))
    segs.append(card(g, [("What's your score?", 96, YELLOW), (f"___ / {N}", 124, WHITE), ("Comment it below!", 60, SOFT)],
                     f"What is your score out of {N}? Write it in the comments, and subscribe to QuizNado for more challenges!", 3, 1.2))
    total = render(segs, g, f"{outdir}/{prefix}.mp4"); thumbnail(f"{outdir}/{prefix}_thumbnail.jpg", rnd, N)
    json.dump(ans, open(f"{outdir}/{prefix}_answers.json", "w"))
    print("long", round(total, 1), "s", [a["answer"] for a in ans], flush=True)

def make_short(out, typ, seed, trio):
    rnd = random.Random(seed); g = Geo(True); pz = make_puzzle(trio, typ, rnd)
    lvl = "EXPERT" if typ == 4 else "IMPOSSIBLE"; chip = f"WEIGHT PUZZLE • LEVEL {lvl}"
    segs = [card(g, [("Only 1% can", 92, WHITE), ("solve this!", 92, WHITE), ("Find the missing weight", 60, YELLOW)],
                 "Only one percent of people can solve this! Find the missing weight.", 2.8, 0.3, chip),
            puzzle_seg(g, pz, chip, think=12, short=True,
                       intro="Look at the scales. Comment your answer before the reveal!"),
            card(g, [("Did you get it?", 86, YELLOW), ("Subscribe to QuizNado", 70, WHITE), ("for more challenges!", 70, WHITE)],
                 "Did you get it right? Subscribe to QuizNado for more challenges!", 2.8, 0.8, chip)]
    total = render(segs, g, out); json.dump(pz, open(out + ".answer.json", "w"))
    print("short", lvl, round(total, 1), "s answer", pz["answer"], flush=True)

def thumbnail(out, rnd, n):
    g = Geo(False); im = gradient(1920, 1080)
    im.alpha_composite(user_logo(200), (60, 40))
    txt(im, (90, 330), "FIND THE", 110, WHITE, 8, "lm"); txt(im, (90, 470), "MISSING", 130, YELLOW, 9, "lm")
    txt(im, (90, 620), "WEIGHT!", 130, YELLOW, 9, "lm")
    d = ImageDraw.Draw(im); d.rounded_rectangle([90, 760, 700, 870], radius=55, fill=RED)
    d.text((395, 815), f"{n} LEVELS", font=F(64), fill=WHITE, anchor="mm")
    pz = {"trio": ["frog", "sheep", "horse"]}
    draw_scale(im, (1000, 150, 1860, 900), pz, [0, 1, 2], "?", "question")
    im.convert("RGB").resize((1280, 720), Image.LANCZOS).save(out, quality=92)

if __name__ == "__main__":
    if sys.argv[1] == "long": make_long(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    elif sys.argv[1] == "short": make_short(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5].split(","))
    elif sys.argv[1] == "frames":
        # preview: python3 weights.py frames OUT_DIR
        o = sys.argv[2]; rnd = random.Random(5)
        for portrait in (False, True):
            g = Geo(portrait); pz = make_puzzle(("frog", "sheep", "horse"), 5, rnd)
            s = puzzle_seg(g, pz, "LEVEL 20 / 24 • EXPERT", think=12)
            for tt, nm in ((8.0, "ask"), (s.dur - 1.0, "rev")):
                im = background(g, s.chip); s.draw(im, tt); im.convert("RGB").save(f"{o}/prev_{'p' if portrait else 'l'}_{nm}.png")
        thumbnail(f"{o}/prev_thumb.jpg", rnd, 24)

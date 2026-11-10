"""QuizNado07 'Memory test' — memorize where the colors are, cards flip to numbers, "Where is YELLOW?".
python3 memory.py short OUT.mp4 SEED      -> hook-first Short (memorize 5 s, 3 answered, last one NO answer)
"""
import sys, os, math, random
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import F, tick, ding, whoosh, ease, shadowed, YELLOW, WHITE, DEEP
from weights import Seg, say, render, txt, bar, RED, SOFT

COLORS = {"BLUE": (37, 99, 235), "RED": (220, 38, 38), "GREEN": (34, 197, 94), "YELLOW": (250, 204, 21),
          "ORANGE": (249, 115, 22), "PINK": (236, 72, 153), "PURPLE": (147, 51, 234), "BROWN": (146, 64, 14),
          "WHITE": (245, 245, 245), "BLACK": (30, 30, 36), "GRAY": (148, 163, 184), "LIGHT BLUE": (56, 189, 248)}
NUMC = (109, 40, 217)

class G:
    def __init__(self, cols=2, rows=3):
        self.portrait = True; self.W, self.H = 1080, 1920; self.chip_y = 405
        self.title_y = 525; self.cols, self.rows = cols, rows
        x0, y0, x1, y1 = 110, 610, 970, 1600; gap = 34
        cw = (x1 - x0 - gap * (cols - 1)) / cols; ch = (y1 - y0 - gap * (rows - 1)) / rows
        self.cells = [(x0 + c * (cw + gap), y0 + r * (ch + gap), x0 + c * (cw + gap) + cw, y0 + r * (ch + gap) + ch)
                      for r in range(rows) for c in range(cols)]
        self.timer = (180, 1660, 1000, 1695); self.count = (95, 1677, 50)

def face(lv, slot, kind, box):
    """one card face as an RGBA image"""
    w, h = int(box[2] - box[0]), int(box[3] - box[1]); im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if kind == "color":
        c = COLORS[lv["colors"][slot]]
        for y in range(h):   # soft vertical shading
            k = 1.08 - 0.22 * y / h; d.line([(0, y), (w, y)], fill=tuple(min(255, int(v * k)) for v in c) + (255,))
        m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=26, fill=255); im.putalpha(m)
        ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, h - 1], radius=26, outline=WHITE, width=7)
    else:
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=26, fill=WHITE)
        r = min(w, h) * 0.40; cx, cy = w / 2, h / 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=NUMC)
        d.text((cx, cy + 4), str(lv["nums"][slot]), font=F(int(r * 1.25)), fill=WHITE, anchor="mm")
    return im

def draw_cards(im, g, lv, revealed, flips, t, hide_all=False, glow=None):
    """revealed: slots showing color; flips: {slot: (t0, from, to)}"""
    for s, box in enumerate(g.cells):
        kind = "color" if (s in revealed and not hide_all) else "num"; sx = 1.0
        if s in flips:
            t0, a, b = flips[s]; p = min(1, max(0, (t - t0) / 0.36))
            kind = a if p < 0.5 else b; sx = max(0.04, abs(math.cos(math.pi * p)))
        f = face(lv, s, kind, box)
        if sx < 0.999: f = f.resize((max(2, int(f.width * sx)), f.height))
        x = int((box[0] + box[2]) / 2 - f.width / 2); y = int(box[1])
        if glow == s:
            gl = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).rounded_rectangle(
                [box[0] - 14, box[1] - 14, box[2] + 14, box[3] + 14], radius=34, outline=YELLOW, width=12); im.alpha_composite(gl)
        sh = Image.new("RGBA", f.size, (0, 0, 0, 0)); sh.putalpha(f.getchannel("A").point(lambda v: int(v * .35)))
        im.alpha_composite(sh, (x + 8, y + 12)); im.alpha_composite(f, (x, y))

def ask_text(im, g, color, prefix="WHERE IS", y=None):
    y = y or g.title_y; d = ImageDraw.Draw(im); f = F(74); a = prefix + " "; b = color + "?"
    wa, wb = d.textlength(a, font=f), d.textlength(b, font=f); x = g.W / 2 - (wa + wb) / 2
    d.text((x, y), a, font=f, fill=WHITE, anchor="lm", stroke_width=7, stroke_fill=DEEP)
    c = COLORS[color]; c = c if sum(c) > 160 else (200, 200, 210)
    d.text((x + wa, y), b, font=f, fill=c, anchor="lm", stroke_width=7, stroke_fill=WHITE if color in ("BLACK", "PURPLE", "BLUE") else DEEP)

def make_level(rnd, n=6, pool=("BLUE", "RED", "GREEN", "YELLOW", "ORANGE", "PINK")):
    colors = list(pool[:n]); rnd.shuffle(colors); nums = list(range(1, n + 1)); rnd.shuffle(nums)
    asks = colors[:]; rnd.shuffle(asks)
    return {"colors": colors, "nums": nums, "asks": asks}

def make_short(out, seed):
    rnd = random.Random(seed); g = G(2, 3); lv = make_level(rnd); n = len(lv["colors"])
    answered, final = lv["asks"][:3], lv["asks"][3]
    chip = "MEMORY TEST 🧠".replace(" 🧠", "") + " • 5 SECONDS"
    segs = []; revealed = set()
    # 1) memorize (colors on screen from frame 0)
    snd = []; vd = say(snd, 0.1, "Memory test! Remember where each color is. Five seconds!")
    mem = max(5.0, vd + 0.6)
    for s in range(int(mem)): snd.append((mem - int(mem) + s, tick() * (1.4 if s >= int(mem) - 3 else 1)))
    def d_mem(im, t):
        draw_cards(im, g, lv, set(range(n)), {}, t)
        txt(im, (g.W / 2, g.title_y), "MEMORIZE THE COLORS!", 70, YELLOW, 7)
        left = max(0.0, mem - t); bar(im, g, left / mem, max(1, math.ceil(left)))
    segs.append(Seg(mem, d_mem, lambda t: ("m", int(t * 10)), snd, chip))
    # 2) flip to numbers
    snd = [(0.0, whoosh() * 0.8)]; vd = say(snd, 0.5, "Time's up!")
    fl = {s: (0.05 * s, "color", "num") for s in range(n)}
    def d_flip(im, t):
        draw_cards(im, g, lv, set(range(n)), fl, t)
        txt(im, (g.W / 2, g.title_y), "TIME'S UP!", 84, YELLOW, 8)
    segs.append(Seg(max(1.4, vd + 0.7), d_flip, lambda t: ("f", min(12, int(t * 20))), snd, "MEMORY TEST"))
    # 3) questions
    def q_seg(color, think, reveal, label):
        rv = set(revealed); slot = lv["colors"].index(color); num = lv["nums"][slot]
        snd = []; vd = say(snd, 0.1, f"Where is {color.lower()}?"); t_th = vd + 0.3
        for s in range(think): snd.append((t_th + s, tick() * (1.4 if s >= think - 3 else 1)))
        t_rev = t_th + think
        if reveal:
            snd.append((t_rev, ding())); rvd = say(snd, t_rev + 0.35, f"Number {num}!"); dur = t_rev + max(1.7, rvd + 0.7)
        else: dur = t_rev
        def draw(im, t):
            fl = {slot: (t_rev, "num", "color")} if (reveal and t >= t_rev) else {}
            draw_cards(im, g, lv, rv, fl, t, glow=slot if (reveal and t >= t_rev + 0.3) else None)
            ask_text(im, g, color)
            if t < t_rev or not reveal:
                left = min(think, max(0.0, t_rev - t)); bar(im, g, left / think, max(1, math.ceil(left)))
            else:
                txt(im, (g.W / 2, 1678), f"NUMBER {num}!", 64, YELLOW, 6)
        def key(t):
            if t < t_th: return "a"
            if t < t_rev: return ("c", int((t - t_th) * 10))
            return ("r", min(15, int((t - t_rev) * 20)))
        if reveal: revealed.add(slot)
        return Seg(dur, draw, key, snd, label)
    for k, c in enumerate(answered):
        segs.append(q_seg(c, 4, True, f"QUESTION {k + 1}/4"))
    segs.append(q_seg(final, 5, False, "LAST ONE • NO ANSWER"))
    # 4) end card: cards stay hidden -> comment + loop back to the colors
    fslot = lv["colors"].index(final); rv = set(revealed)
    left_n = sorted(lv["nums"][i] for i in range(n) if i not in rv)
    left_txt = ", ".join(map(str, left_n[:-1])) + " or " + str(left_n[-1]) + "?"
    snd = []; vd = say(snd, 0.1, f"Where is {final.lower()}? Comment the number! And subscribe for more memory tests!")
    def d_end(im, t):
        draw_cards(im, g, lv, rv, {}, t)
        ov = Image.new("RGBA", im.size, (20, 8, 50, 195)); im.alpha_composite(ov)
        ask_text(im, g, final)
        txt(im, (g.W / 2, 980), "Comment the number!", 86, YELLOW, 9)
        txt(im, (g.W / 2, 1090), left_txt, 66, WHITE, 6)
        dd = ImageDraw.Draw(im); pulse = 1 + 0.04 * math.sin(t * 6); w, h = 700 * pulse, 130 * pulse; y = 1270
        dd.rounded_rectangle([g.W / 2 - w / 2, y - h / 2, g.W / 2 + w / 2, y + h / 2], radius=65, fill=RED, outline=WHITE, width=5)
        dd.text((g.W / 2, y), "SUBSCRIBE & LIKE", font=F(60), fill=WHITE, anchor="mm")
    segs.append(Seg(max(3.6, vd + 0.4), d_end, lambda t: ("e", int(t * 10) % 11), snd, "QuizNado07"))
    total = render(segs, g, out)
    print("memory short", round(total, 1), "s; layout", list(zip(lv["nums"], lv["colors"])), "; final", final,
          "= number", lv["nums"][fslot], flush=True)

if __name__ == "__main__":
    if sys.argv[1] == "short": make_short(sys.argv[2], int(sys.argv[3]))

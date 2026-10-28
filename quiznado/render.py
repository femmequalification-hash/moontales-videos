"""QuizNado video renderer: purple background, question card, A/B/C options,
countdown timer, voiceover (Kokoro TTS), tick/ding sounds, soft music, logo watermark."""
import os, sys, math, subprocess, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
TTS_DIR = os.environ.get("MT_TTS_DIR", os.path.join(HERE, "..", "pipeline", "tts"))
CACHE = os.environ.get("QN_CACHE", "/tmp/qn_tts_cache")
FONT_DIR = "/usr/share/fonts/truetype/google-fonts"
def F(size, w="Bold"):
    p = f"{FONT_DIR}/Poppins-{w}.ttf"
    if not os.path.exists(p): p = f"{FONT_DIR}/Poppins-Bold.ttf"
    if not os.path.exists(p): p = os.path.join(HERE, "..", "pipeline", "fonts", "Fredoka.ttf")
    return ImageFont.truetype(p, size)

FPS = 30
SR = 24000
PURPLE_T = (124, 58, 237); PURPLE_B = (46, 16, 101); DEEP = (46, 16, 101)
YELLOW = (250, 204, 21); GREEN = (22, 163, 74); WHITE = (255, 255, 255); LAV = (237, 233, 254)

# ---------------- TTS ----------------
_k = None
def tts(text, voice="af_heart", speed=1.05):
    global _k
    from kokoro_onnx import Kokoro
    if _k is None:
        _k = Kokoro(os.path.join(TTS_DIR, "kokoro.onnx"), os.path.join(TTS_DIR, "voices.bin"))
    cache = CACHE; os.makedirs(cache, exist_ok=True)
    key = re.sub(r"[^a-z0-9]+", "_", text.lower())[:80] + f"_{abs(hash((text, voice, speed))) % 10**8}"
    p = f"{cache}/{key}.npy"
    if os.path.exists(p): return np.load(p)
    s, sr = _k.create(text, voice=voice, speed=speed, lang="en-us")
    s = s.astype(np.float32); np.save(p, s); return s

def spoken(t):
    t = t.replace("×", " times ").replace("÷", " divided by ").replace("= ?", "").replace("___", "blank")
    t = t.replace("°C", " degrees").replace("...", ",").replace('"', "")
    return re.sub(r"\s+", " ", t).strip()

# ---------------- sounds ----------------
def tone(f, d, vol=0.3, decay=8):
    t = np.arange(int(SR * d)) / SR
    return (vol * np.sin(2 * np.pi * f * t) * np.exp(-decay * t)).astype(np.float32)
def tick(): return tone(1800, 0.06, 0.25, 60) + tone(900, 0.06, 0.12, 60)
def ding():
    return tone(1046.5, 0.9, 0.25, 4) + tone(1318.5, 0.9, 0.18, 4) + tone(1568, 0.9, 0.12, 4)
def whoosh():
    n = int(SR * 0.35); w = np.random.RandomState(1).randn(n).astype(np.float32)
    w = np.convolve(w, np.ones(30) / 30, "same"); env = np.sin(np.linspace(0, np.pi, n)) ** 2
    return 0.12 * w * env
def music(total):
    # soft looping arpeggio pad (C - Am - F - G), quiet
    bpm = 100; beat = 60 / bpm; out = np.zeros(int(SR * total) + SR, np.float32)
    chords = [[261.6, 329.6, 392.0], [220.0, 261.6, 329.6], [174.6, 220.0, 261.6], [196.0, 246.9, 293.7]]
    i = 0; t = 0.0
    while t < total:
        ch = chords[(i // 8) % 4]; f = ch[i % 3] * (2 if (i % 8) >= 4 else 1)
        s = tone(f, beat * 0.9, 0.05, 5) + tone(f / 2, beat * 0.9, 0.03, 3)
        a = int(t * SR); out[a:a + len(s)] += s; t += beat / 2; i += 1
    return out[:int(SR * total)]

# ---------------- drawing helpers ----------------
def gradient(W, H):
    y = np.linspace(0, 1, H)[:, None]
    top = np.array(PURPLE_T); bot = np.array(PURPLE_B)
    arr = (top * (1 - y)[..., None] + bot * y[..., None]).repeat(W, axis=1).astype(np.uint8)
    img = Image.fromarray(arr, "RGB")
    # subtle glowing circles for depth
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for cx, cy, r, a in [(0.15, 0.2, 0.35, 28), (0.9, 0.75, 0.4, 22), (0.6, 0.05, 0.2, 18)]:
        d.ellipse([cx * W - r * W, cy * H - r * W, cx * W + r * W, cy * H + r * W], fill=(167, 139, 250, a))
    ov = ov.filter(ImageFilter.GaussianBlur(60))
    img = img.convert("RGBA"); img.alpha_composite(ov); return img

def tornado_icon(size):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    n = 6
    for i in range(n):
        w = size * (0.95 - i * 0.14); h = size * 0.13
        cx = size / 2 + math.sin(i * 0.9) * size * 0.07; cy = size * 0.12 + i * size * 0.15
        col = YELLOW if i % 2 == 0 else WHITE
        d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=h / 2, fill=col + (255,))
    return im

def user_logo(size, alpha=1.0):
    src = Image.open(os.path.join(HERE, "brand", "logo.png")).convert("RGBA")
    w, h0 = src.size; m = min(w, h0); src = src.crop(((w - m) // 2, (h0 - m) // 2, (w + m) // 2, (h0 + m) // 2))
    big = size * 4
    src = src.resize((big, big), Image.LANCZOS)
    mask = Image.new("L", (big, big), 0); ImageDraw.Draw(mask).ellipse([0, 0, big - 1, big - 1], fill=int(255 * alpha))
    src.putalpha(mask)
    ring = Image.new("RGBA", (big, big), (0, 0, 0, 0)); ImageDraw.Draw(ring).ellipse([6, 6, big - 7, big - 7], outline=YELLOW + (int(255 * alpha),), width=24)
    src.alpha_composite(ring)
    return src.resize((size, size), Image.LANCZOS)

def logo(h):
    """QuizNado wordmark: tornado icon + 'Quiz' white + 'Nado' yellow."""
    f = F(int(h * 0.78), "ExtraBold")
    icon = tornado_icon(h)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    w1 = tmp.textlength("Quiz", font=f); w2 = tmp.textlength("Nado", font=f)
    W = int(h + h * 0.2 + w1 + w2 + 10)
    im = Image.new("RGBA", (W, int(h * 1.1)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    im.alpha_composite(icon, (0, 0))
    x = int(h * 1.2); y = int(h * 0.5)
    d.text((x, y), "Quiz", font=f, fill=WHITE, anchor="lm")
    d.text((x + w1, y), "Nado", font=f, fill=YELLOW, anchor="lm")
    return im

def shadowed(base, box, radius, fill, blur=18, off=10, alpha=90):
    x0, y0, x1, y1 = box
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle(
        [x0, y0 + off, x1, y1 + off], radius=radius, fill=(20, 0, 50, alpha))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(base).rounded_rectangle(box, radius=radius, fill=fill)

def fit_text(d, text, box_w, box_h, max_size, min_size=30, w="Bold"):
    size = max_size
    while size >= min_size:
        f = F(size, w); words = text.split(); lines = []; cur = ""
        for wd in words:
            t = (cur + " " + wd).strip()
            if d.textlength(t, font=f) <= box_w: cur = t
            else: lines.append(cur); cur = wd
        lines.append(cur)
        lh = size * 1.22
        if len(lines) * lh <= box_h and all(d.textlength(l, font=f) <= box_w for l in lines):
            return f, lines, lh
        size -= 4
    return F(min_size, w), lines, min_size * 1.22

def draw_lines(d, cx, cy, f, lines, lh, fill):
    y = cy - (len(lines) - 1) * lh / 2
    for l in lines:
        d.text((cx, y), l, font=f, fill=fill, anchor="mm"); y += lh

def ease(x): x = max(0, min(1, x)); return 1 - (1 - x) ** 3

# ---------------- layouts ----------------
class Layout:
    def __init__(self, portrait):
        self.portrait = portrait
        if portrait:
            self.W, self.H = 1080, 1920
            self.card = (90, 470, 990, 880)
            self.opts = [(110, 940 + i * 175, 970, 940 + i * 175 + 145) for i in range(3)]
            self.timer = (140, 1500, 940, 1530)
            self.chip_y = 400; self.logo_h = 110; self.logo_xy = None
        else:
            self.W, self.H = 1920, 1080
            self.card = (210, 190, 1710, 500)
            ow = 470; gap = 45; x0 = (1920 - 3 * ow - 2 * gap) // 2
            self.opts = [(x0 + i * (ow + gap), 570, x0 + i * (ow + gap) + ow, 750) for i in range(3)]
            self.timer = (460, 850, 1460, 878)
            self.chip_y = 135; self.logo_h = 80
        self.bg = gradient(self.W, self.H)
        lg = user_logo(200 if portrait else 135)
        if portrait: pos = ((self.W - lg.width) // 2, 145)
        else: pos = (35, 22)
        self.bg.alpha_composite(lg, pos)
        # watermark (anti re-upload)
        wm = user_logo(110 if portrait else 70, alpha=0.5)
        self.bg.alpha_composite(wm, ((self.W - wm.width) // 2, self.H - (310 if portrait else 125)))
        d = ImageDraw.Draw(self.bg)
        d.text((self.W // 2, self.H - (180 if portrait else 40)), "@QuizNado • New quiz every day",
               font=F(30 if portrait else 24, "SemiBold"), fill=(221, 214, 254), anchor="mm")

    def question_layer(self, num, total, q, opts, state, topic):
        """state: 'ask' | ('reveal', ans)"""
        im = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        chip = f"{topic.upper()}  •  QUESTION {num}/{total}"
        cf = F(34 if self.portrait else 30, "Bold"); cw = d.textlength(chip, font=cf) + 60
        d.rounded_rectangle([self.W / 2 - cw / 2, self.chip_y - 32, self.W / 2 + cw / 2, self.chip_y + 32],
                            radius=32, fill=YELLOW)
        d.text((self.W / 2, self.chip_y), chip, font=cf, fill=DEEP, anchor="mm")
        x0, y0, x1, y1 = self.card
        shadowed(im, self.card, 44, WHITE); d = ImageDraw.Draw(im)
        f, lines, lh = fit_text(d, q, x1 - x0 - 100, y1 - y0 - 80, 76 if self.portrait else 72)
        draw_lines(d, (x0 + x1) / 2, (y0 + y1) / 2, f, lines, lh, DEEP)
        for i, (box, o) in enumerate(zip(self.opts, opts)):
            correct = state != "ask" and state[1] == i
            wrong = state != "ask" and not correct
            fill = GREEN if correct else (WHITE if not wrong else (196, 181, 253))
            shadowed(im, box, 36, fill, blur=12, off=7, alpha=70); d = ImageDraw.Draw(im)
            bx0, by0, bx1, by1 = box; bh = by1 - by0; r = bh * 0.34
            ccx = bx0 + 30 + r; ccy = (by0 + by1) / 2
            d.ellipse([ccx - r, ccy - r, ccx + r, ccy + r], fill=WHITE if correct else PURPLE_T)
            d.text((ccx, ccy), "ABC"[i], font=F(int(r * 1.15), "ExtraBold"),
                   fill=GREEN if correct else WHITE, anchor="mm")
            tx0 = ccx + r + 25
            f2, l2, lh2 = fit_text(d, o, bx1 - tx0 - 30, bh - 20, 58 if self.portrait else 50, 28)
            col = WHITE if correct else (DEEP if not wrong else (91, 33, 182))
            y = ccy - (len(l2) - 1) * lh2 / 2
            for l in l2:
                d.text((tx0, y), l, font=f2, fill=col, anchor="lm"); y += lh2
            if correct:
                d.text((bx1 - 45, ccy), "✓", font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(bh * 0.5)),
                       fill=WHITE, anchor="mm")
        return im

    def timer_layer(self, frac, secs_left):
        im = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        x0, y0, x1, y1 = self.timer
        r = 58 if self.portrait else 46; cx = x0 + r; cy = (y0 + y1) / 2
        x0 = x0 + 2 * r + 30
        d.rounded_rectangle([x0, y0, x1, y1], radius=15, fill=(255, 255, 255, 60))
        if frac > 0.002:
            d.rounded_rectangle([x0, y0, x0 + (x1 - x0) * frac, y1], radius=15,
                                fill=YELLOW if frac > 0.3 else (248, 113, 113))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE)
        d.text((cx, cy), str(secs_left), font=F(int(r * 1.2), "ExtraBold"), fill=DEEP, anchor="mm")
        return im

    def big_text(self, lines_spec):
        """lines_spec: list of (text, size, color). Centered stack inside a card."""
        im = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        tot = sum(s * 1.3 for _, s, _ in lines_spec)
        y = self.H / 2 - tot / 2 + (40 if self.portrait else 30)
        for t, s, c in lines_spec:
            f, ls, lh = fit_text(d, t, self.W - 180, s * 3, s)
            for l in ls:
                # outline for readability
                d.text((self.W / 2, y + lh / 2), l, font=f, fill=c, anchor="mm", stroke_width=6, stroke_fill=DEEP)
                y += lh
            y += s * 0.15
        return im

# ---------------- timeline building ----------------
class Timeline:
    def __init__(self): self.scenes = []; self.audio = []  # (start, samples)
    @property
    def t(self): return sum(s["dur"] for s in self.scenes)
    def add(self, kind, dur, **kw):
        self.scenes.append(dict(kind=kind, dur=dur, start=self.t, **kw))
    def sound(self, at, samples): self.audio.append((at, samples))

def build(quiz_list, portrait, rounds=False):
    tl = Timeline()
    voice = "af_heart"
    def say(text, kind, pad=0.5, min_d=0, **kw):
        a = tts(spoken(text), voice); st = tl.t
        tl.sound(st + 0.15, a); tl.add(kind, max(min_d, len(a) / SR + 0.15 + pad), **kw); return st
    # intro
    if rounds:
        hook = "Ultimate QuizNado Challenge: 35 questions. Can you beat them all?"
        say("Welcome to QuizNado! 35 questions, 7 rounds. Grab a pen, count your points, and let's go!",
            "intro", 0.6, lines=[("ULTIMATE QUIZ", 120, YELLOW), ("35 Questions • 7 Rounds", 64, WHITE),
                                 ("Count your score!", 54, LAV)])
    else:
        q = quiz_list[0]
        say(q["hook"] + " Let's test you!", "intro", 0.4,
            lines=[(q["hook"], 96, YELLOW), (q["topic"] + " • 5 Questions", 56, WHITE)])
    for ri, quiz in enumerate(quiz_list):
        if rounds:
            say(f"Round {ri + 1}. {quiz['topic']}!", "title", 0.5,
                lines=[(f"ROUND {ri + 1}", 120, YELLOW), (quiz["topic"], 80, WHITE)])
        n = len(quiz["qs"])
        for qi, (qq, opts, ans) in enumerate(quiz["qs"]):
            common = dict(num=qi + 1, total=n, q=qq, opts=opts, ans=ans, topic=quiz["topic"])
            tl.sound(tl.t, whoosh())
            text = f"Question {qi + 1}. {qq}"
            if rounds: text += " " + ". ".join(f"{'ABC'[i]}, {o}" for i, o in enumerate(opts)) + "."
            say(text, "ask", 0.25, **common)
            tstart = tl.t; T = 5 if rounds else 4
            for s in range(T): tl.sound(tstart + s, tick())
            tl.add("timer", T, T=T, **common)
            tl.sound(tl.t, ding())
            say(f"The answer is {'ABC'[ans]}! {opts[ans]}.", "reveal", 0.6, **common)
            if (not rounds and qi == 2):
                say("If you liked it so far, subscribe and like!", "cta", 0.4,
                    lines=[("Enjoying it?", 90, WHITE), ("SUBSCRIBE & LIKE", 100, YELLOW),
                           ("New quiz every day", 52, LAV)])
        if rounds and ri in (1, 4):
            say("If you liked it so far, subscribe and like! It really helps QuizNado.", "cta", 0.5,
                lines=[("Enjoying it?", 90, WHITE), ("SUBSCRIBE & LIKE", 110, YELLOW),
                       ("It really helps QuizNado", 52, LAV)])
    end = ("Out of 35, what was your score? Write it in the comments! Subscribe to QuizNado for a new quiz every day."
           if rounds else "How many did you get right? Comment your score! And subscribe to QuizNado for a new quiz every day.")
    say(end, "outro", 1.2, lines=[("Comment your score!", 96, YELLOW), ("___ / 35" if rounds else "___ / 5", 120, WHITE),
                                  ("Subscribe for a new quiz every day", 54, LAV)])
    return tl

# ---------------- render ----------------
def render(tl, L, out):
    total = tl.t; nfr = int(math.ceil(total * FPS))
    # audio mix
    mix = music(total) * 1.0
    for at, s in tl.audio:
        a = int(at * SR); b = min(len(mix), a + len(s)); mix[a:b] += s[:b - a]
    mix = np.clip(mix, -1, 1)
    wav = out.replace(".mp4", ".wav"); sf.write(wav, mix, SR)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{L.W}x{L.H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cache = {}
    def layer(key, fn):
        if key not in cache:
            if len(cache) > 12: cache.clear()
            cache[key] = fn()
        return cache[key]
    si = 0; last_key = None; last_bytes = None
    for fi in range(nfr):
        t = fi / FPS
        while si < len(tl.scenes) - 1 and t >= tl.scenes[si]["start"] + tl.scenes[si]["dur"]: si += 1
        sc = tl.scenes[si]; lt = t - sc["start"]; k = sc["kind"]
        # reuse identical frames (static scenes; timer updated 10x per second)
        if k in ("intro", "title", "cta", "outro"): fkey = (si, "s") if lt >= 0.35 else None
        elif k == "ask": fkey = (si, "s") if lt >= 0.4 else None
        elif k == "reveal": fkey = (si, "s") if lt >= 0.25 else None
        elif k == "timer": fkey = (si, int(lt * 10))
        else: fkey = None
        if fkey is not None and fkey == last_key:
            p.stdin.write(last_bytes); continue
        frame = L.bg.copy()
        if k in ("intro", "title", "cta", "outro"):
            lay = layer((si, "big"), lambda: L.big_text(sc["lines"]))
            e = ease(lt / 0.35); sc_ = 0.85 + 0.15 * e
            if e < 1:
                w, h = int(L.W * sc_), int(L.H * sc_)
                l2 = lay.resize((w, h), Image.BILINEAR)
                l2.putalpha(l2.getchannel("A").point(lambda a: int(a * e)))
                frame.alpha_composite(l2, ((L.W - w) // 2, (L.H - h) // 2))
            else:
                # gentle pulse
                frame.alpha_composite(lay)
        else:
            state = "ask" if k != "reveal" else ("reveal", sc["ans"])
            key = (sc["q"], state)
            lay = layer(key, lambda: L.question_layer(sc["num"], sc["total"], sc["q"], sc["opts"], state, sc["topic"]))
            if k == "ask" and lt < 0.4:
                e = ease(lt / 0.4); dx = int((1 - e) * L.W * 0.6)
                l2 = lay.copy(); l2.putalpha(l2.getchannel("A").point(lambda a: int(a * e)))
                frame.alpha_composite(l2, (dx, 0)) if dx >= 0 else None
            elif k == "reveal" and lt < 0.25:
                # quick flash pop
                frame.alpha_composite(lay)
                fl = Image.new("RGBA", (L.W, L.H), (255, 255, 255, int(90 * (1 - lt / 0.25)))); frame.alpha_composite(fl)
            else:
                frame.alpha_composite(lay)
            if k == "timer":
                T = sc["T"]; frac = 1 - lt / T
                frame.alpha_composite(L.timer_layer(frac, max(1, math.ceil(T - lt))))
        last_bytes = frame.convert("RGB").tobytes(); last_key = fkey
        p.stdin.write(last_bytes)
    p.stdin.close(); p.wait(); os.remove(wav)
    return total

def thumbnail(L, title_lines, out, q=None):
    im = L.bg.copy(); d = ImageDraw.Draw(im)
    if q:
        im.alpha_composite(L.question_layer(1, 35, q[0], q[1], "ask", "Ultimate Quiz"))
        ov = Image.new("RGBA", im.size, (30, 5, 70, 150)); im.alpha_composite(ov)
    im.alpha_composite(L.big_text(title_lines))
    im = im.convert("RGB")
    if not L.portrait: im = im.resize((1280, 720), Image.LANCZOS)
    im.save(out, quality=92)

def long_thumbnail(out, number):
    im = gradient(1920, 1080); d = ImageDraw.Draw(im)
    im.alpha_composite(user_logo(250), (80, 50))
    d.text((90, 340), "35 QUESTIONS", font=F(140), fill=YELLOW, stroke_width=8, stroke_fill=DEEP)
    d.text((95, 560), "Only 1% get", font=F(110), fill=WHITE, stroke_width=6, stroke_fill=DEEP)
    d.text((95, 700), "them all!", font=F(110), fill=WHITE, stroke_width=6, stroke_fill=DEEP)
    d.rounded_rectangle([90, 880, 720, 980], radius=50, fill=WHITE)
    d.text((405, 930), "IQ • English • Riddles", font=F(52), fill=DEEP, anchor="mm")
    shadowed(im, (1290, 250, 1840, 840), 60, WHITE); d = ImageDraw.Draw(im)
    d.text((1565, 470), "?", font=F(380), fill=PURPLE_T, anchor="mm")
    for i, (c, col) in enumerate([("A", PURPLE_T), ("B", GREEN), ("C", PURPLE_T)]):
        cx = 1385 + i * 180
        d.ellipse([cx - 62, 693, cx + 62, 817], fill=col); d.text((cx, 755), c, font=F(78), fill=WHITE, anchor="mm")
    d.rounded_rectangle([1420, 900, 1710, 1000], radius=50, fill=YELLOW)
    d.text((1565, 950), f"#{number}", font=F(64), fill=DEEP, anchor="mm")
    im.convert("RGB").resize((1280, 720), Image.LANCZOS).save(out, quality=92)

def loudnorm(path):
    tmp = path + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", path, "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, path)

def to_quiz(r):
    return {"id": r.get("id", r["topic"]), "topic": r["topic"], "hook": r.get("hook", ""),
            "qs": [(q["q"], q["options"], q["answer"]) for q in r["questions"]]}

if __name__ == "__main__":
    # usage: python3 render.py day.json OUTDIR [long|short1|short2|all]
    import json
    day = json.load(open(sys.argv[1])); outdir = sys.argv[2]; which = sys.argv[3] if len(sys.argv) > 3 else "all"
    os.makedirs(outdir, exist_ok=True); n = day["number"]; date = day["date"]
    if which in ("long", "all"):
        out = f"{outdir}/{date}_QuizNado_Ultimate_Quiz_{n}.mp4"
        d = render(build([to_quiz(r) for r in day["long"]["rounds"]], False, rounds=True), Layout(False), out)
        loudnorm(out); long_thumbnail(f"{outdir}/{date}_QuizNado_Ultimate_Quiz_{n}_thumbnail.jpg", n)
        print("long", round(d, 1), flush=True)
    for i, sh in enumerate(day["shorts"], 1):
        if which not in ("all", f"short{i}"): continue
        out = f"{outdir}/{date}_Short_{i}_{sh['id']}.mp4"
        d = render(build([to_quiz(sh)], True), Layout(True), out); loudnorm(out)
        print(f"short{i}", round(d, 1), flush=True)

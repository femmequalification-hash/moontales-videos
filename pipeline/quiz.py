"""English quiz videos for kids: a long "Big English Quiz" and 4 vertical Shorts.

Usage:  python3 quiz.py OUT_DIR long      -> OUT_DIR/big-quiz.mp4 (+ _thumb.jpg, _meta.json)
        python3 quiz.py OUT_DIR shorts    -> OUT_DIR/quiz-short1..4.mp4 (+ _meta.json)

Each question: the question is read, a 5-second countdown ticks while the child
thinks, then the right answer lights up green and is said out loud.
Question types: missing letter, what is this, what colour, how many, odd one
out, starts with. Pictures are the channel's own drawings (art.py / alphabet.py).
"""
import json
import math
import os
import sys

import numpy as np
import soundfile as sf
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alphabet  # noqa: E402
import art  # noqa: E402
import build  # noqa: E402

H = art.hexc
SR = build.SR
THINK = 5  # seconds of countdown
LETTERS = "ABCD"

# ---------------------------------------------------------------- question bank
Q = {
    # missing letter: (picture, shown word with _, options, answer, full word)
    "ml_apple": ("missing", "apple", "_pple", ["a", "e", "o"], "a"),
    "ml_cat": ("missing", "cat", "c_t", ["o", "a", "i"], "a"),
    "ml_kite": ("missing", "kite", "k_te", ["a", "i", "o"], "i"),
    "ml_dog": ("missing", "dog", "d_g", ["o", "u", "a"], "o"),
    "ml_fish": ("missing", "fish", "f_sh", ["e", "i", "a"], "i"),
    "ml_sun": ("missing", "sun", "s_n", ["u", "a", "o"], "u"),
    "ml_ball": ("missing", "ball", "b_ll", ["a", "e", "u"], "a"),
    "ml_zebra": ("missing", "zebra", "_ebra", ["s", "z", "x"], "z"),
    "ml_cake": ("missing", "cake", "ca_e", ["k", "t", "p"], "k"),
    # what is this: (picture, options, answer)
    "wi_robot": ("what", "robot", ["rabbit", "robot", "rocket"], "robot"),
    "wi_butterfly": ("what", "butterfly", ["bird", "bee", "butterfly"], "butterfly"),
    "wi_umbrella": ("what", "umbrella", ["umbrella", "hat", "kite"], "umbrella"),
    "wi_banana": ("what", "banana", ["apple", "banana", "orange"], "banana"),
    "wi_carrot": ("what", "carrot", ["cake", "pencil", "carrot"], "carrot"),
    "wi_moon": ("what", "moon", ["sun", "moon", "star"], "moon"),
    # colour: (picture, question, options, answer)
    "co_banana": ("color", "banana", "What color is the banana?", ["red", "yellow", "blue"], "yellow"),
    "co_apple": ("color", "apple", "What color is the apple?", ["green", "purple", "red"], "red"),
    "co_carrot": ("color", "carrot", "What color is the carrot?", ["orange", "pink", "black"], "orange"),
    "co_tree": ("color", "tree", "What color are the leaves?", ["blue", "green", "white"], "green"),
    # how many: (picture, count, options)
    "hm_ball": ("count", "ball", 3, ["2", "3", "4"]),
    "hm_star": ("count", "star", 5, ["4", "6", "5"]),
    "hm_apple": ("count", "apple", 4, ["4", "3", "5"]),
    "hm_heart": ("count", "heart", 2, ["1", "2", "3"]),
    # odd one out: (pictures, answer, reason)
    "od_car": ("odd", ["apple", "banana", "car", "orange"], "car", "The car is not a fruit!"),
    "od_pencil": ("odd", ["dog", "cat", "pencil", "fish"], "pencil", "The pencil is not an animal!"),
    "od_sun": ("odd", ["hat", "shoes", "sun", "watch"], "sun", "You cannot wear the sun!"),
    # starts with: (letter, pictures, answer)
    "sw_b": ("starts", "B", ["cat", "ball", "sun"], "ball"),
    "sw_m": ("starts", "M", ["moon", "egg", "kite"], "moon"),
    "sw_t": ("starts", "T", ["fish", "dog", "tree"], "tree"),
}
ROUNDS = [
    ("Missing letter!", ["ml_apple", "ml_dog", "ml_fish", "ml_sun", "ml_ball", "ml_zebra"]),
    ("What is this?", ["wi_banana", "wi_carrot", "wi_moon", "wi_robot"]),
    ("What color?", ["co_banana", "co_apple", "co_carrot", "co_tree"]),
    ("How many?", ["hm_ball", "hm_star", "hm_apple", "hm_heart"]),
    ("Odd one out!", ["od_car", "od_pencil", "od_sun"]),
    ("Which one starts with...?", ["sw_b", "sw_m", "sw_t"]),
]
SHORTS = [
    ("Missing letter challenge", ["ml_apple", "ml_cat", "ml_kite"]),
    ("What is this?", ["wi_robot", "wi_butterfly", "wi_umbrella"]),
    ("How many can you count?", ["hm_ball", "hm_star", "hm_apple"]),
    ("Odd one out!", ["od_car", "od_pencil", "sw_b"]),
]
COLOR_SWATCH = {"red": "#E84A4A", "yellow": "#FFD23F", "blue": "#3E86E0", "green": "#4FAF4A",
                "purple": "#9B6BD3", "orange": "#FF8A2E", "pink": "#FF8FB1", "black": "#2B2B33",
                "white": "#FFFFFF"}


def ask(key):
    """(spoken question, spoken answer, option labels, answer index, pictures, extra)."""
    q = Q[key]
    t = q[0]
    if t == "missing":
        _, pic, shown, opts, ans = q
        return (f"Which letter is missing? {pic.capitalize()}.", f"It's {ans.upper()}! {pic.capitalize()}!",
                [o for o in opts], opts.index(ans), [pic], {"shown": shown, "word": pic})
    if t == "what":
        _, pic, opts, ans = q
        return ("What is this?", f"It's a {ans}!" if ans[0] not in "aeiou" else f"It's an {ans}!",
                opts, opts.index(ans), [pic], {})
    if t == "color":
        _, pic, text, opts, ans = q
        return (text, f"{ans.capitalize()}! The {pic if pic != 'tree' else 'leaves are'} "
                      f"{'is ' if pic != 'tree' else ''}{ans}!", opts, opts.index(ans), [pic], {"swatch": True})
    if t == "count":
        _, pic, n, opts = q
        word = {"ball": "balls", "star": "stars", "apple": "apples", "heart": "hearts"}[pic]
        nums = ["zero", "one", "two", "three", "four", "five", "six"]
        return (f"How many {word} can you see?", f"{nums[n].capitalize()}! There are {nums[n]} {word}!",
                opts, opts.index(str(n)), [pic] * n, {"count": n})
    if t == "odd":
        _, pics, ans, reason = q
        return ("Which one is different? Find the odd one out!", f"The {ans}! {reason}",
                pics, pics.index(ans), pics, {"pictures_are_options": True})
    if t == "starts":
        _, letter, pics, ans = q
        return (f"Which one starts with the letter {letter}?", f"{ans.capitalize()}! {letter} is for {ans}!",
                pics, pics.index(ans), pics, {"pictures_are_options": True, "letter": letter})
    raise ValueError(key)


# ---------------------------------------------------------------- pictures
_pic_cache = {}


PROP_SIZE = {"banana": 260, "carrot": 260, "star": 190, "heart": 200, "shoes": 300, "car": 420,
             "bike": 360, "bird": 260, "butterfly": 220, "cake": 300, "book": 240, "cup": 220,
             "balloon": 300, "boat": 300, "toothbrush": 300}


def picture(name, size):
    k = (name, size)
    if k not in _pic_cache:
        if name in [w for _, w in alphabet.LETTERS]:
            im = alphabet.object_image(name, 840)
        else:
            old = art.SS
            art.SS = 4
            n = PROP_SIZE.get(name, 300)
            c = art.Canvas(n, n)
            art.prop(c, name, n / 2, n / 2 + (10 if name == "carrot" else 0))
            im = c.img.resize((840, 840), Image.LANCZOS)
            art.SS = old
        im = im.convert("RGBA")
        bbox = im.getbbox()
        if bbox:
            im = im.crop(bbox)
        im.thumbnail((size, size), Image.LANCZOS)
        _pic_cache[k] = im
    return _pic_cache[k]


def check(c, x, y, s, col):
    c.line([(x - s * 0.5, y), (x - s * 0.15, y + s * 0.38), (x + s * 0.55, y - s * 0.42)], col, int(s * 0.18))


# ---------------------------------------------------------------- frames
def frame(key, state, timer, vertical, header, number=None, total=None):
    """state: 'ask' (no answer yet) or 'reveal'. timer: seconds left or None."""
    spoken, _, opts, ans, pics, extra = ask(key)
    W, Hh = (1080, 1920) if vertical else (1920, 1080)
    c = art.Canvas(W, Hh)
    c.rect(0, 0, W, Hh, H("#F1E8FF"))
    for k in range(22):
        r = (k * 71 + (number or 0) * 13) % 997
        c.circle((r * 7) % W, (r * 11) % Hh, 12 + r % 24, H("#8E5BD6", 22))
    # header
    hb = (40, 40, W - 40, 190) if vertical else (40, 30, W - 40, 150)
    c.rect(*hb, H("#2B2350"), r=50)
    hdr = header + (f"  {number}/{total}" if number else "")
    c.text(W / 2, (hb[1] + hb[3]) / 2, hdr, art.font(64 if vertical else 66, "Bold"), H("#FFE680"), anchor="mm")
    # question text
    qy = 270 if vertical else 215
    qtext = spoken if Q[key][0] != "missing" else "Which letter is missing?"
    fsize = 58 if len(qtext) < 34 else 46
    c.text(W / 2, qy, qtext, art.font(fsize, "Bold"), H("#2D2A3E"), anchor="mm")
    # picture area
    show_pics = not extra.get("pictures_are_options")
    if vertical:
        pa = (90, 340, W - 90, 1000)
    else:
        pa = (80, 290, 900, 1010)
    if show_pics:
        c.rect(*pa, H("#FFFFFF"), r=60)
        px, py = (pa[0] + pa[2]) / 2, (pa[1] + pa[3]) / 2
        if extra.get("count"):
            n = extra["count"]
            cols = 3 if n > 4 else (2 if n > 1 else 1)
            rows = math.ceil(n / cols)
            cw, ch = (pa[2] - pa[0]) / cols, (pa[3] - pa[1] - 40) / rows
            sz = int(min(cw, ch) * 0.8)
            for i in range(n):
                r_, col = divmod(i, cols)
                rn = min(cols, n - r_ * cols)
                x0 = px - rn * cw / 2 + col * cw + cw / 2
                y0 = pa[1] + 20 + r_ * ch + ch / 2
                im = picture(pics[0], sz)
                c.paste(im, x0 - im.width / 2, y0 - im.height / 2)
        else:
            im = picture(pics[0], 470 if vertical else 520)
            c.paste(im, px - im.width / 2, py - im.height / 2 - (60 if extra.get("shown") else 0))
            if extra.get("shown"):
                shown = extra["shown"]
                if state == "reveal":
                    shown = extra["word"]
                f = art.font(120, "Bold")
                txt = " ".join(shown)
                tw = f.getlength(txt)
                x = px - tw / 2
                for ch_i, ch in enumerate(txt):
                    col = H("#2D2A3E")
                    if ch == "_":
                        col = H("#FF6A1F")
                    if state == "reveal" and ch_i // 2 == extra["shown"].index("_") and ch != " ":
                        col = H("#2FA84F")
                    c.text(x, pa[3] - 175, ch, f, col)
                    x += f.getlength(ch)
    # options
    n = len(opts)
    if extra.get("pictures_are_options"):
        if vertical:
            cols = 2
            box_w, box_h = 440, 560
            ox0, oy0 = (W - 2 * box_w - 40) / 2, 380
        else:
            cols = n
            box_w, box_h = (1760 - (n - 1) * 30) / n, 560
            ox0, oy0 = 80, 300
        boxes = []
        for i in range(n):
            r_, col = divmod(i, cols)
            in_row = min(cols, n - r_ * cols)
            shift = (cols - in_row) * (box_w + 40) / 2 if vertical else 0
            x = ox0 + shift + col * (box_w + 40 if vertical else box_w + 30)
            y = oy0 + r_ * (box_h + 40)
            boxes.append((x, y, x + box_w, y + box_h))
    else:
        if vertical:
            box_w, box_h = W - 180, 150
            boxes = [(90, 1060 + i * 185, 90 + box_w, 1060 + i * 185 + box_h) for i in range(n)]
        else:
            box_w, box_h = 860, 170
            boxes = [(980, 300 + i * 240, 980 + box_w, 300 + i * 240 + box_h) for i in range(n)]
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        right = i == ans
        if state == "reveal":
            fill = H("#2FA84F") if right else H("#FFFFFF", 150)
            outline = H("#1E7A37") if right else H("#D8D0E8")
        else:
            fill, outline = H("#FFFFFF"), H("#8E5BD6")
        c.rect(x0 + 6, y0 + 10, x1 + 6, y1 + 10, H("#000000", 35), r=40)
        c.rect(x0, y0, x1, y1, fill, r=40, outline=outline, width=8)
        badge = H("#FFB020") if not (state == "reveal" and right) else H("#FFFFFF")
        c.circle(x0 + 60, y0 + 60 if extra.get("pictures_are_options") else (y0 + y1) / 2, 40, badge)
        c.text(x0 + 60, y0 + 60 if extra.get("pictures_are_options") else (y0 + y1) / 2, LETTERS[i],
               art.font(52, "Bold"), H("#2B2350"), anchor="mm")
        tcol = H("#FFFFFF") if state == "reveal" and right else H("#2D2A3E", 255 if state == "ask" or right else 130)
        if extra.get("pictures_are_options"):
            im = picture(opts[i], int(min(box_w, box_h) * 0.72))
            if state == "reveal" and not right:
                im = im.copy()
                im.putalpha(im.getchannel("A").point(lambda v: v * 0.35))
            c.paste(im, (x0 + x1) / 2 - im.width / 2, (y0 + y1) / 2 - im.height / 2 + 10)
            if state == "reveal" and right:
                c.text((x0 + x1) / 2, y1 - 50, opts[i], art.font(60, "Bold"), H("#FFFFFF"), anchor="mm")
        else:
            label = opts[i] if Q[key][0] != "missing" else opts[i].upper() + "  " + opts[i]
            tx = x0 + 130
            if extra.get("swatch"):
                c.circle(x0 + 160, (y0 + y1) / 2, 38, H(COLOR_SWATCH[opts[i]]), outline=H("#2B2350", 80), width=3)
                tx = x0 + 220
            c.text(tx, (y0 + y1) / 2, label, art.font(76, "Bold"), tcol, anchor="lm")
            if state == "reveal" and right:
                check(c, x1 - 75, (y0 + y1) / 2, 60, H("#FFFFFF"))
    # timer
    if timer is not None:
        tx, ty, tr = (W - 130, 300 if not vertical else 1810, 85) if not vertical else (W / 2, 1810, 80)
        if not vertical:
            tx, ty = W - 130, 215
            tr = 70
        c.circle(tx, ty, tr + 8, H("#2B2350"))
        c.circle(tx, ty, tr, H("#FFFFFF"))
        c.pie(tx, ty, tr, tr, -90, -90 + 360 * timer / THINK, H("#FF7A30"))
        c.circle(tx, ty, tr - 18, H("#FFFFFF"))
        c.text(tx, ty, str(timer), art.font(int(tr * 1.1), "Bold"), H("#2B2350"), anchor="mm")
    elif vertical:
        c.text(W / 2, 1810, "Think... then say it out loud!" if state == "ask" else "Great job!",
               art.font(56, "SemiBold"), H("#7A6A9A"), anchor="mm")
    return c.final().convert("RGB")


def title_frame(lines, vertical, big=None):
    W, Hh = (1080, 1920) if vertical else (1920, 1080)
    c = art.Canvas(W, Hh)
    art.sky(c, "night", "sunny")
    art.stars(c, 70, 8)
    art.moon(c, W - 150, 160, 70)
    y = Hh / 2 - (len(lines) - 1) * (80 if not vertical else 95) - (80 if big else 0)
    if big:
        c.text(W / 2, y - 40, big, art.font(150 if not vertical else 130, "Bold"), H("#FFE680"), anchor="mm",
               stroke=8, stroke_fill=H("#2B2350"))
        y += 170
    for ln in lines:
        c.text(W / 2, y, ln, art.font(70, "Bold"), H("#FFFFFF"), anchor="mm", stroke=5, stroke_fill=H("#2B2350"))
        y += 160 if vertical else 130
    for name, x in (("lina", 0.18), ("adams", 0.82)):
        im = art.CHARACTERS[name]()
        sc = 0.75 if vertical else 0.7
        im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
        c.paste(im, W * x - im.width / 2, Hh - im.height + 20)
    return c.final().convert("RGB")


# ---------------------------------------------------------------- audio helpers
def tone(freq, dur, amp=0.3, decay=6.0):
    t = np.arange(int(dur * SR)) / SR
    return (amp * np.exp(-t * decay) * np.sin(2 * np.pi * freq * t)).astype(np.float32)


TICK = tone(1400, 0.08, 0.18, 40)
DING = tone(880, 0.6, 0.22, 4) + tone(1320, 0.6, 0.14, 4) + tone(1760, 0.6, 0.08, 4)


class Timeline:
    def __init__(self, work, voice):
        self.work, self.voice = work, voice
        self.audio = np.zeros(SR * 600, dtype=np.float32)
        self.t = 0.0
        self.frames = []  # (png path, duration)
        self.n = 0

    def add_sound(self, a, at):
        s = int(at * SR)
        self.audio[s:s + len(a)] += a

    def say(self, text, who="narrator"):
        p = os.path.join(self.work, f"v{self.n}.wav")
        self.n += 1
        d = self.voice.say(text, who, p)
        a, _ = sf.read(p, dtype="float32")
        self.add_sound(a, self.t)
        return d

    def show(self, img, dur):
        p = os.path.join(self.work, f"f{len(self.frames):04d}.png")
        img.save(p)
        self.frames.append((p, dur))
        self.t += dur

    def question(self, key, vertical, header, number=None, total=None):
        spoken, answer, *_ = ask(key)
        img_ask = frame(key, "ask", None, vertical, header, number, total)
        d = self.say(spoken)
        self.show(img_ask, d + 0.4)
        for s in range(THINK, 0, -1):
            self.add_sound(TICK, self.t)
            self.show(frame(key, "ask", s, vertical, header, number, total), 1.0)
        self.add_sound(DING, self.t)
        who = "lina" if (number or 0) % 2 else "adams"
        d = self.say(answer, who)
        self.show(frame(key, "reveal", None, vertical, header, number, total), d + 0.9)

    def render(self, out, music_vol=0.10, vertical=False):
        total = self.t
        lst = os.path.join(self.work, "frames.txt")
        with open(lst, "w") as f:
            for p, d in self.frames:
                f.write(f"file '{p}'\nduration {d:.3f}\n")
            f.write(f"file '{self.frames[-1][0]}'\n")
        vpath = os.path.join(self.work, "voice.wav")
        sf.write(vpath, np.clip(self.audio[: int(total * SR) + SR], -1, 1), SR)
        mpath = os.path.join(self.work, "music.wav")
        build.music(total + 1, mpath, seed=21)
        build.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                   "-i", vpath, "-i", mpath, "-filter_complex",
                   f"[0:v]fps=30,format=yuv420p[v];[2:a]volume={music_vol}[m];"
                   "[1:a][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]",
                   "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "veryfast",
                   "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", out])


# ---------------------------------------------------------------- builds
def build_long(out_dir, voice):
    work = os.path.join(out_dir, "work_big-quiz")
    os.makedirs(work, exist_ok=True)
    tl = Timeline(work, voice)
    total_q = sum(len(r[1]) for r in ROUNDS)
    img = title_frame(["Can you answer them all?", "Let's play and learn English!"], False, "Big English Quiz!")
    d = tl.say("Hello, friends! Welcome to the Big English Quiz, on Moon Tales Kids!")
    d += 0.3
    tl.show(img, d)
    d = tl.say("Listen to the question. Think for five seconds. Then say your answer out loud!", "lina")
    tl.show(img, d + 0.5)
    num = 0
    for r_i, (name, keys) in enumerate(ROUNDS, 1):
        card = title_frame([f"Round {r_i}"], False, name)
        d = tl.say(f"Round {r_i}. {name.replace('...?', '?')}", "adams")
        tl.show(card, d + 0.8)
        for k in keys:
            num += 1
            tl.question(k, False, name.replace("...?", "..."), num, total_q)
    img = title_frame(["How many did you get right?", "Ask a grown-up to subscribe for more!"], False, "Well done!")
    d = tl.say(f"Well done, friends! There were {total_q} questions. How many did you get right?")
    tl.show(img, d + 0.3)
    d = tl.say("Ask a grown-up to subscribe to Moon Tales Kids for a new quiz soon. Bye, bye!", "lina")
    tl.show(img, d + 1.0)
    out = os.path.join(out_dir, "big-quiz.mp4")
    tl.render(out)
    # thumbnail
    c = art.Canvas(1280, 720)
    c.rect(0, 0, 1280, 720, H("#F1E8FF"))
    c.rect(30, 30, 760, 690, H("#8E5BD6"), r=60)
    c.text(395, 150, "QUIZ", art.font(170, "Bold"), H("#FFE680"), anchor="mm", stroke=8, stroke_fill=H("#2B2350"))
    c.text(395, 300, "_ p p l e", art.font(120, "Bold"), H("#FFFFFF"), anchor="mm")
    c.text(395, 410, "?", art.font(150, "Bold"), H("#FF7A30"), anchor="mm")
    c.rect(70, 540, 720, 650, H("#2B2350"), r=34)
    c.text(395, 595, "Can you answer?", art.font(64, "Bold"), H("#FFE680"), anchor="mm")
    ap = picture("apple", 330)
    c.paste(ap, 1010 - ap.width / 2, 200 - ap.height / 2 + 30)
    im = art.CHARACTERS["lina"]()
    im = im.resize((int(im.width * 0.6), int(im.height * 0.6)), Image.LANCZOS)
    c.paste(im, 1010 - im.width / 2, 720 - im.height + 15)
    c.final().convert("RGB").save(os.path.join(out_dir, "big-quiz_thumb.jpg"), quality=92)
    meta = {
        "title": "Big English Quiz for Kids 🧠 Missing Letter, Colors, Counting & More | Moon Tales Kids",
        "description": (
            "Can you answer them all? 🧠✨ Play the Big English Quiz with Lina and Adams!\n"
            f"{total_q} fun questions in 6 rounds. Listen, think for 5 seconds, and say your answer out loud!\n\n"
            "🎯 Rounds in this quiz:\n1️⃣ Missing letter (_pple, d_g, f_sh…)\n2️⃣ What is this?\n"
            "3️⃣ What color?\n4️⃣ How many?\n5️⃣ Odd one out\n6️⃣ Which one starts with…?\n\n"
            "👨‍👩‍👧 For parents: pause the video if your child needs more time, and cheer every right answer! "
            "Perfect for kids aged 3 to 8 learning English.\n\n"
            "🇲🇦 مسابقة باللغة الإنجليزية للأطفال: الحرف الناقص، الألوان، العد وأكثر!\n"
            "🇫🇷 Quiz en anglais pour enfants : la lettre manquante, les couleurs, compter et plus !\n\n"
            "🌙 Subscribe to Moon Tales Kids for more quizzes and English stories!\n\n"
            "#EnglishQuiz #QuizForKids #EnglishForKids #MoonTalesKids"),
        "tags": ["english quiz for kids", "quiz for kids", "missing letter quiz", "guess the word kids",
                 "kids quiz english", "brain games for kids", "learn english for kids", "Moon Tales Kids",
                 "Lina and Adams", "مسابقة للاطفال بالانجليزي", "اختبار انجليزي للاطفال", "الغاز للاطفال",
                 "quiz anglais enfant", "jeu anglais pour enfants", "devinette enfant anglais"],
    }
    json.dump(meta, open(os.path.join(out_dir, "big-quiz_meta.json"), "w"), ensure_ascii=False, indent=2)
    print(f"done: {out} ({tl.t / 60:.1f} min)")


def build_shorts(out_dir, voice):
    for n, (name, keys) in enumerate(SHORTS, 1):
        work = os.path.join(out_dir, f"work_quiz-short{n}")
        os.makedirs(work, exist_ok=True)
        tl = Timeline(work, voice)
        hook = title_frame(["Only smart kids", "can answer all 3!"], True, "QUIZ TIME!")
        d = tl.say("Quiz time! Only smart kids can answer all three. Are you ready?", "lina")
        tl.show(hook, d + 0.3)
        for i, k in enumerate(keys, 1):
            tl.question(k, True, name if len(name) < 20 else "Quiz time!", i, len(keys))
        end = title_frame(["How many did you get?", "More quizzes on", "Moon Tales Kids!"], True, "Wow!")
        d = tl.say("How many did you get? Watch the big quiz on Moon Tales Kids!", "adams")
        tl.show(end, d + 0.8)
        out = os.path.join(out_dir, f"quiz-short{n}.mp4")
        tl.render(out, music_vol=0.08, vertical=True)
        hooks = {1: "Which letter is missing? 🤔", 2: "Can you guess what this is? 🤔",
                 3: "Can you count them all? 🔢", 4: "Find the odd one out! 🧐"}
        meta = {
            "title": f"{hooks[n]} English Quiz for Kids #shorts",
            "description": (f"{name}! 3 questions, 5 seconds each. Only smart kids can answer all 3! 🧠\n"
                            "Think, then say your answer out loud!\n\n"
                            "🇲🇦 مسابقة إنجليزية للأطفال — هل تعرف الجواب؟\n"
                            "🇫🇷 Quiz en anglais pour enfants — tu connais la réponse ?\n\n"
                            "Play the Big English Quiz on Moon Tales Kids! 🌙\n\n"
                            "#shorts #EnglishQuiz #QuizForKids #EnglishForKids"),
            "tags": ["english quiz for kids", "quiz shorts", "guess the word", "missing letter", "kids quiz",
                     "Moon Tales Kids", "مسابقة للاطفال", "اختبار انجليزي", "quiz anglais enfant", "devinette"],
        }
        json.dump(meta, open(os.path.join(out_dir, f"quiz-short{n}_meta.json"), "w"), ensure_ascii=False, indent=2)
        print(f"short {n}: {out} ({tl.t:.0f} s)")


if __name__ == "__main__":
    out_dir, what = sys.argv[1], sys.argv[2]
    tts = os.environ.get("MT_TTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts"))
    if what == "preview":
        os.makedirs(out_dir, exist_ok=True)
        for k, key in enumerate(["ml_apple", "hm_star", "od_car", "co_banana"]):
            frame(key, "ask", 3, False, "Quiz", 1, 26).save(os.path.join(out_dir, f"p{k}a.png"))
            frame(key, "reveal", None, False, "Quiz", 1, 26).save(os.path.join(out_dir, f"p{k}b.png"))
        frame("sw_b", "ask", 4, True, "Odd one out!", 3, 3).save(os.path.join(out_dir, "pv1.png"))
        frame("ml_kite", "reveal", None, True, "Missing letter", 3, 3).save(os.path.join(out_dir, "pv2.png"))
        sys.exit()
    v = build.Voice(tts)
    if what == "long":
        build_long(out_dir, v)
    else:
        build_shorts(out_dir, v)

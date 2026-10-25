"""'Worksheet' style quiz Shorts: a paper sheet with 3 numbered questions, a red marker
underline on the current question, a countdown circle, and a green tick on the answer.

Usage:  python3 worksheet.py OUT_DIR [N ...]   -> worksheet-short1..3.mp4 (+ _meta.json)
Our own drawings and branding only.
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art  # noqa: E402
import build  # noqa: E402
import quiz  # noqa: E402

H = art.hexc
W, HH = 1080, 1920
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


def serif(size):
    from PIL import ImageFont
    f = ImageFont.truetype(SERIF, size)
    return f


def stext(c, x, y, s, size, fill, anchor="la"):
    """Serif text on a Canvas (supersampled)."""
    f = serif(size * art.SS)
    c._do(lambda d: d.text((x * art.SS, y * art.SS), s, font=f, fill=fill, anchor=anchor), fill)


def slen(s, size):
    return serif(size).getlength(s)


# ---------------------------------------------------------------- extra drawings
STEEL, STEEL_D = H("#C3CCD6"), H("#7E8B99")


def draw_kettle(c, x, y):
    c.arc(x + 5, y - 70, 120, 110, 200, 340, H("#2B2B33"), 22)          # handle
    c.poly([(x - 95, y + 10), (x - 190, y - 70), (x - 172, y - 92), (x - 80, y - 30)], STEEL,
           outline=STEEL_D, width=5)                                     # spout
    c.ellipse(x, y + 40, 125, 115, STEEL, outline=STEEL_D, width=6)       # body
    c.rect(x - 120, y + 125, x + 120, y + 160, H("#2B2B33"), r=14)       # base
    c.ellipse(x, y - 70, 70, 18, H("#AEB8C4"), outline=STEEL_D, width=5)  # lid
    c.circle(x, y - 90, 18, H("#2B2B33"))                                # knob
    c.ellipse(x - 55, y + 10, 18, 45, H("#FFFFFF", 150))                 # shine


def draw_whisk(c, x, y):
    for w in (95, 65, 35, 8):
        c.ellipse(x, y - 60, w, 130, None, outline=H("#9AA4B0"), width=7)
    c.rect(x - 28, y + 55, x + 28, y + 190, H("#E84A4A"), r=22)
    c.rect(x - 34, y + 50, x + 34, y + 72, H("#9AA4B0"), r=8)


def draw_ladle(c, x, y):
    c.line([(x + 10, y + 60), (x + 70, y - 60), (x + 95, y - 160)], STEEL_D, 16)
    c.arc(x + 70, y - 165, 25, 25, 180, 360, STEEL_D, 14)
    c.pie(x - 60, y + 60, 105, 95, 0, 180, STEEL)
    c.arc(x - 60, y + 60, 105, 95, 0, 180, STEEL_D, 6)
    c.line([(x - 165, y + 60), (x + 45, y + 60)], STEEL_D, 8)
    c.ellipse(x - 95, y + 95, 20, 12, H("#FFFFFF", 150))


SKIN, SKIN2 = H("#E2B086"), H("#C98E63")


def avatar(c, x, y, s, kind):
    """Small person (head + shoulders). kind: man, woman, oldman, oldwoman, boy, girl."""
    skin = SKIN if kind in ("man", "oldman", "boy") else SKIN2
    shirt = {"man": "#3E86E0", "woman": "#E85D8A", "oldman": "#7CB342", "oldwoman": "#9B6BD3",
             "boy": "#FFB020", "girl": "#9B6BD3"}[kind]
    hair = H("#B9B9C2") if kind.startswith("old") else H("#3A2415")
    c.chord(x, y + 95 * s, 70 * s, 60 * s, 180, 360, H(shirt))
    if kind in ("woman", "girl"):
        c.ellipse(x, y + 5 * s, 52 * s, 62 * s, hair)
    if kind == "oldwoman":
        c.circle(x, y - 52 * s, 22 * s, hair)
    c.circle(x, y, 45 * s, skin)
    if kind in ("man", "boy"):
        c.chord(x, y - 8 * s, 47 * s, 42 * s, 180, 360, hair)
    elif kind in ("woman", "girl", "oldwoman"):
        c.chord(x, y - 10 * s, 48 * s, 40 * s, 180, 360, hair)
    elif kind == "oldman":
        c.circle(x - 42 * s, y - 8 * s, 14 * s, hair)
        c.circle(x + 42 * s, y - 8 * s, 14 * s, hair)
    if kind == "girl":
        c.circle(x - 46 * s, y - 30 * s, 16 * s, hair)
        c.circle(x + 46 * s, y - 30 * s, 16 * s, hair)
    for ex in (-15, 15):
        c.circle(x + ex * s, y + 2 * s, 5 * s, H("#2B1B12"))
    if kind == "oldman":
        c.chord(x, y + 22 * s, 30 * s, 32 * s, 0, 180, H("#E9E9EE"))
        c.ellipse(x, y + 18 * s, 22 * s, 7 * s, H("#E9E9EE"))
        c.circle(x - 15 * s, y + 2 * s, 11 * s, None, outline=H("#555566"), width=max(1, int(3 * s)))
        c.circle(x + 15 * s, y + 2 * s, 11 * s, None, outline=H("#555566"), width=max(1, int(3 * s)))
    else:
        c.arc(x, y + 16 * s, 14 * s, 9 * s, 20, 160, H("#8C2F3A"), max(1, int(4 * s)))


def family(c, x0, y0, spec):
    """spec: nodes [(kind, label, x, y, is_question)], edges [(i, j)]. Coords relative to (x0,y0)."""
    nodes, edges = spec
    for i, j in edges:
        (_, _, xa, ya, _), (_, _, xb, yb, _) = nodes[i], nodes[j]
        c.line([(x0 + xa, y0 + ya), (x0 + xb, y0 + yb)], H("#9A8F7A"), 5)
    for kind, label, x, y, q in nodes:
        c.circle(x0 + x, y0 + y, 66, H("#FFF3B0") if q else H("#FFFFFF"),
                 outline=H("#E84A4A") if q else H("#9A8F7A"), width=5)
        avatar(c, x0 + x, y0 + y - 8, 0.62, kind)
        if q:
            c.circle(x0 + x + 52, y0 + y - 52, 24, H("#E84A4A"))
            c.text(x0 + x + 52, y0 + y - 52, "?", art.font(36, "Bold"), H("#FFFFFF"), anchor="mm")
        c.text(x0 + x, y0 + y + 88, label, art.font(32, "Bold"), H("#2B2350"), anchor="mm")


def picture_tile(item, size=380):
    """Render a question picture as an RGBA image of about size x size."""
    old = art.SS
    art.SS = 2
    try:
        if isinstance(item, tuple):          # family tree
            c = art.Canvas(440, 420)
            family(c, 0, 0, item)
            return c.final()
        if item in ("kettle", "whisk", "ladle"):
            c = art.Canvas(420, 420)
            {"kettle": draw_kettle, "whisk": draw_whisk, "ladle": draw_ladle}[item](c, 225, 210)
            im = c.final()
            bb = im.getbbox()
            im = im.crop(bb)
            im.thumbnail((size, size), Image.LANCZOS)
            return im
    finally:
        art.SS = old
    return quiz.picture(item, size)


# ---------------------------------------------------------------- content
F_DAD = ([("man", "Dad", 110, 90, False), ("man", "Dad's brother", 330, 90, True), ("boy", "You", 110, 300, False)],
         [(0, 1), (0, 2)])
F_NIECE = ([("woman", "You", 110, 90, False), ("man", "Your brother", 330, 90, False),
            ("girl", "His daughter", 330, 300, True)], [(0, 1), (1, 2)])
F_GRANNY = ([("oldwoman", "Mom's mom", 220, 70, True), ("woman", "Mom", 220, 230, False),
             ("girl", "You", 220, 380, False)], [(0, 1), (1, 2)])
F_GRANNY = ([("oldwoman", "Mom's mom", 110, 90, True), ("woman", "Mom", 330, 90, False),
             ("girl", "You", 330, 300, False)], [(0, 1), (1, 2)])

SETS = [
    ("VOCABULARY", "What is this called in English?", [
        ("What is this called in English?", "toothbrush", ["Hairbrush", "Toothbrush", "Paintbrush"], "Toothbrush",
         "It's a toothbrush! We brush our teeth with it."),
        ("What is this called in English?", "queen", ["Crown", "Tiara", "Helmet"], "Crown",
         "It's a crown! A king or a queen wears it."),
        ("What is this called in English?", "nest", ["Hive", "Cage", "Nest"], "Nest",
         "It's a nest! Birds live in a nest. Bees live in a hive."),
     ], "What Is This Called in English? 🤔 Vocabulary Quiz #shorts"),
    ("FAMILY", "Family words", [
        ("What is your father's brother called?", F_DAD, ["Nephew", "Uncle", "Cousin"], "Uncle",
         "Uncle! Your father's brother is your uncle."),
        ("What is your brother's daughter called?", F_NIECE, ["Niece", "Daughter", "Aunt"], "Niece",
         "Niece! Your brother's daughter is your niece."),
        ("What is your mother's mother called?", F_GRANNY, ["Aunt", "Mother-in-law", "Grandmother"],
         "Grandmother", "Grandmother! Your mother's mother is your grandmother."),
     ], "Family Words in English 👨‍👩‍👧 Can You Get 3/3? #shorts"),
    ("KITCHEN", "Kitchen words", [
        ("What is this called in English?", "kettle", ["Teapot", "Kettle", "Jug"], "Kettle",
         "It's a kettle! We boil water in a kettle. A teapot is for making tea."),
        ("What is this called in English?", "whisk", ["Whisk", "Fork", "Spatula"], "Whisk",
         "It's a whisk! We use it to mix eggs and cream."),
        ("What is this called in English?", "ladle", ["Spoon", "Scoop", "Ladle"], "Ladle",
         "It's a ladle! We use it to serve soup."),
     ], "Do You Know These Kitchen Words? 🍳 English Quiz #shorts"),
]
NUM_WORD = ["one", "two", "three"]


# ---------------------------------------------------------------- drawing the sheet
_paper = None


def paper():
    global _paper
    if _paper is None:
        rng = np.random.default_rng(3)
        base = np.ones((HH, W, 3), dtype=np.float32) * np.array([247, 244, 236], dtype=np.float32)
        noise = rng.normal(0, 5, (HH // 2, W // 2, 1)).astype(np.float32)
        noise = np.kron(noise, np.ones((2, 2, 1), dtype=np.float32))
        im = Image.fromarray(np.clip(base + noise, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
        _paper = im.convert("RGBA")
    return _paper.copy()


def wrap(text, size, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if slen(t, size) > maxw and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    lines.append(cur)
    return lines


def marker(c, x0, x1, y, seed, progress=1.0):
    r = random.Random(seed)
    xe = x0 + (x1 - x0) * progress
    pts, x = [], x0
    while x < xe:
        pts.append((x, y + r.uniform(-3, 3)))
        x += 40
    pts.append((xe, y + r.uniform(-2, 2)))
    if len(pts) > 1:
        c.line(pts, H("#E8312F", 235), 12)


def tick(c, x, y, s=1.0):
    c.line([(x - 30 * s, y + 2 * s), (x - 6 * s, y + 32 * s), (x + 48 * s, y - 42 * s)], H("#1FA34A"), int(16 * s))


def sheet(si, active=None, answered=(), timer=None, underline=1.0, overlay=None):
    cat, _, qs, _ = SETS[si]
    c = art.Canvas(W, HH)
    c.paste(paper(), 0, 0)
    # header (our own branding: moons + colours)
    c.rect(150, 60, 930, 205, H("#FFFFFF"), r=70, outline=H("#1C1C24"), width=7)
    f = art.font(104, "Bold")
    wE, wQ = f.getlength("English "), f.getlength("Quiz")
    x = 540 - (wE + wQ) / 2
    c.text(x, 133, "English ", f, H("#E8312F"), anchor="lm")
    c.text(x + wE, 133, "Quiz", f, H("#1F5FD6"), anchor="lm")
    art.moon(c, 95, 133, 40)
    art.moon(c, 985, 133, 40)
    c.text(540, 262, cat, art.font(60, "Bold"), H("#1F5FD6"), anchor="mm")
    by = 310
    bh = 505
    for qi, (qtext, pic, opts, ans, _) in enumerate(qs):
        y0 = by + qi * bh
        lines = wrap(f"{qi + 1}) {qtext}", 54, 960)
        for li, ln in enumerate(lines):
            stext(c, 50, y0 + li * 70, ln, 54, H("#141420"))
        if qi == active or qi in answered:
            for li, ln in enumerate(lines):
                prog = underline if qi == active and qi not in answered else 1.0
                marker(c, 48, 52 + slen(ln, 54), y0 + li * 70 + 66, seed=qi * 7 + li, progress=prog)
        oy = y0 + 70 * len(lines) + 40
        # picture
        tile = picture_tile(pic, 340)
        if isinstance(pic, tuple):
            tile = tile.resize((int(tile.width * 0.75), int(tile.height * 0.75)), Image.LANCZOS)
            px, py = 840 - tile.width / 2, oy - 5
        else:
            px = 820 - tile.width / 2
            py = oy + 175 - tile.height / 2
        c.paste(tile, px, py)
        for oi, opt in enumerate(opts):
            yy = oy + oi * 112
            right = qi in answered and opt == ans
            c.rect(70, yy, 140, yy + 70, H("#FFFFFF"), r=10, outline=H("#1C1C24"), width=6)
            size = 56
            while slen(opt, size) > 470 and size > 36:
                size -= 2
            stext(c, 175, yy + 35, opt, size, H("#1FA34A") if right else H("#141420"), anchor="lm")
            if right:
                tick(c, 108, yy + 30, 1.1)
        if timer is not None and qi == active:
            tx, ty, tr = 975, y0 + 34, 62
            c.circle(tx, ty, tr + 10, H("#FFFFFF", 235))
            c.pie(tx, ty, tr + 6, tr + 6, -90, -90 + 360 * timer / quiz.THINK, H("#E8312F"))
            c.circle(tx, ty, tr - 8, H("#FFFFFF"))
            c.text(tx, ty, str(timer), art.font(76, "Bold"), H("#1C1C24"), anchor="mm")
    if overlay:
        c.rect(0, 0, W, HH, H("#000000", 120))
        c.rect(70, 560, 1010, 1360, H("#FFFFFF"), r=60, outline=H("#1C1C24"), width=7)
        y = 680
        for k, (txt, col, sz) in enumerate(overlay):
            c.text(540, y, txt, art.font(sz, "Bold"), H(col), anchor="mm")
            y += sz + 70
    return c.final().convert("RGB")


def build_short(out_dir, voice, si):
    cat, theme, qs, title = SETS[si]
    n = si + 1
    work = os.path.join(out_dir, f"work_worksheet{n}")
    os.makedirs(work, exist_ok=True)
    tl = quiz.Timeline(work, voice)
    d = tl.say(f"English quiz! {theme}. Can you answer all three? Let's go!")
    tl.show(sheet(si), d + 0.3)
    answered = []
    for qi, (qtext, _, opts, ans, explain) in enumerate(qs):
        # underline animation (3 quick frames) while the question is read
        d = tl.say(f"Number {NUM_WORD[qi]}. {qtext}")
        steps = 4
        for k in range(1, steps + 1):
            tl.show(sheet(si, qi, answered, underline=k / steps), min(0.18, d / steps))
        tl.show(sheet(si, qi, answered), max(0.2, d - 4 * 0.18) + 0.3)
        for s in range(quiz.THINK, 0, -1):
            tl.add_sound(quiz.TICK, tl.t)
            tl.show(sheet(si, qi, answered, timer=s), 1.0)
        answered.append(qi)
        tl.add_sound(quiz.DING, tl.t)
        d = tl.say(explain)
        tl.show(sheet(si, qi, answered), d + 0.7)
    ov = [("How many did you get?", "#1C1C24", 66), ("Comment your score!", "#E8312F", 72),
          ("More quizzes on our channel", "#1F5FD6", 54), ("Like & Subscribe!", "#1FA34A", 72)]
    d = tl.say("How many did you get? Comment your score! Want more? You'll find more quizzes on our channel. "
               "If you liked it, like and subscribe!")
    tl.show(sheet(si, None, answered, overlay=ov), d + 1.0)
    out = os.path.join(out_dir, f"worksheet-short{n}.mp4")
    tl.render(out, music_vol=0.07, vertical=True)
    words = ", ".join(q[3] for q in qs)
    meta = {
        "title": title,
        "description": (f"English quiz — {theme}: can you get 3/3? 🧠\n"
                        "💬 Comment your score: 1/3, 2/3 or 3/3?\n"
                        "🎬 More English quizzes on our channel!\n"
                        "👍 Liked it? Like & subscribe for a new quiz every week! 🔔\n\n"
                        f"Answers: {words}\n\n"
                        "🇲🇦 اختبر مفرداتك في اللغة الإنجليزية — شارك نتيجتك في التعليقات!\n"
                        "🇫🇷 Teste ton vocabulaire en anglais — partage ton score en commentaire !\n\n"
                        "#shorts #EnglishQuiz #LearnEnglish #EnglishVocabulary"),
        "tags": ["english quiz", "english vocabulary", "vocabulary quiz", "what is this called in english",
                 f"{cat.lower()} words in english", "learn english", "english test", "quiz shorts",
                 "مفردات انجليزية", "اختبار انجليزي", "تعلم الانجليزية", "vocabulaire anglais", "quiz anglais"],
    }
    json.dump(meta, open(os.path.join(out_dir, f"worksheet-short{n}_meta.json"), "w"), ensure_ascii=False, indent=2)
    print(f"short {n}: {out} ({tl.t:.0f} s)")


if __name__ == "__main__":
    out_dir = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] == "preview":
        os.makedirs(out_dir, exist_ok=True)
        ims = [sheet(0, 1, [0], timer=3), sheet(1, 2, [0, 1]), sheet(2, 0, [], underline=0.5)]
        g = Image.new("RGB", (3 * 405 + 20, 720), (0, 0, 0))
        for k, im in enumerate(ims):
            g.paste(im.resize((405, 720)), (k * 415, 0))
        g.save(os.path.join(out_dir, "ws_prev.png"))
        sys.exit()
    tts = os.environ.get("MT_TTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts"))
    v = build.Voice(tts)
    which = [int(a) for a in sys.argv[2:]] or [1, 2, 3]
    for n in which:
        build_short(out_dir, v, n - 1)

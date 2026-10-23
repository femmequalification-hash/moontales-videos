"""Build the "ABC Phonics with Lina and Adams" video (A for Apple ... Z for Zebra).

Usage:  python3 alphabet.py OUT_DIR            (the long video)
        python3 alphabet.py OUT_DIR --shorts   (4 Shorts, after the long video)
Output: OUT_DIR/abc-phonics.mp4, OUT_DIR/abc-phonics_thumb.jpg,
        OUT_DIR/work_abc-phonics/segNN.mp4 (one per letter, used for Shorts),
        OUT_DIR/abc-phonics_meta.json
Original drawings only (no copied characters or logos). No rainbow anywhere:
letter cards use a 4-colour cycle that never forms a rainbow band.
"""
import json
import math
import os
import sys

import numpy as np
import soundfile as sf
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art  # noqa: E402
import build  # noqa: E402

H = art.hexc
LETTERS = [
    ("A", "apple"), ("B", "ball"), ("C", "cat"), ("D", "dog"), ("E", "egg"), ("F", "fish"),
    ("G", "gift"), ("H", "hat"), ("I", "ice cream"), ("J", "juice"), ("K", "kite"), ("L", "lamp"),
    ("M", "moon"), ("N", "nest"), ("O", "orange"), ("P", "pencil"), ("Q", "queen"), ("R", "robot"),
    ("S", "sun"), ("T", "tree"), ("U", "umbrella"), ("V", "van"), ("W", "watch"), ("X", "xylophone"),
    ("Y", "yo-yo"), ("Z", "zebra"),
]
# card colour, background colour (4-step cycle: purple, teal, coral, blue)
PALETTE = [("#8E5BD6", "#F1E8FF"), ("#1FA79A", "#E2F7F3"), ("#F06A5D", "#FFEDE8"), ("#3E86E0", "#E5F0FF")]


# ---------------------------------------------------------------- extra drawings
def draw_object(c, name, x, y):
    """Draw a big object centred at (x, y) on a 420x420-ish Canvas."""
    if name == "ball":
        c.circle(x, y, 80, H("#FFFFFF"))
        for k, col in enumerate(("#E84A4A", "#3E86E0", "#FFD23F")):
            c.pie(x, y, 80, 80, k * 120 - 90, k * 120 - 30, H(col))
        c.circle(x, y, 80, None, outline=H("#D9D9E3"), width=3)
        c.circle(x, y, 12, H("#FFFFFF"))
        c.ellipse(x - 35, y - 40, 14, 22, H("#FFFFFF", 150))
    elif name == "dog":
        art.prop(c, "dog", x - 25, y - 20)
    elif name in ("apple", "fish", "gift", "hat", "kite", "lamp", "orange", "umbrella"):
        art.prop(c, name, x, y + (60 if name == "lamp" else (40 if name == "umbrella" else 0)))
        if name == "apple":
            c.ellipse(x - 42, y - 12, 10, 18, H("#FFFFFF", 150))
    elif name == "moon":
        art.moon(c, x, y, 120)
    elif name == "sun":
        art.sun(c, x, y, 105)
    elif name == "tree":
        art.tree(c, x, y + 200, 0.62)
    elif name == "egg":
        c.ellipse(x, y + 10, 78, 100, H("#FFF7E8"), outline=H("#E9D6B5"), width=6)
        c.ellipse(x - 25, y - 30, 16, 26, H("#FFFFFF"))
    elif name == "ice cream":
        c.poly([(x - 70, y), (x + 70, y), (x, y + 170)], H("#E6A960"))
        for k in range(-2, 3):
            c.line([(x + k * 26 - 30, y + 10), (x + k * 26 + 30, y + 110)], H("#C98B44"), 4)
        c.circle(x, y - 40, 72, H("#FFB3C7"))
        c.circle(x - 45, y - 5, 40, H("#FFB3C7"))
        c.circle(x + 45, y - 5, 40, H("#FFB3C7"))
        c.circle(x + 5, y - 115, 18, H("#E84A4A"))
    elif name == "juice":
        c.rect(x - 70, y - 110, x + 70, y + 130, H("#FFFFFF", 230), r=22, outline=H("#BFD7EA"), width=6)
        c.rect(x - 60, y - 40, x + 60, y + 120, H("#FFA62B"), r=16)
        c.line([(x + 25, y - 170), (x + 10, y - 40)], H("#4FA3E3"), 12)
        c.circle(x - 50, y - 100, 34, H("#FF9A2E"))
        c.circle(x - 50, y - 100, 24, H("#FFC27A"))
    elif name == "nest":
        c.ellipse(x, y + 40, 150, 70, H("#8A5A34"))
        for k in range(7):
            c.arc(x, y + 40, 150 - k * 8, 60 - k * 4, 0, 180, H("#B07A4A"), 6)
        for dx in (-50, 0, 50):
            c.ellipse(x + dx, y + 5, 34, 44, H("#9FD3F2"))
        c.ellipse(x, y + 60, 150, 40, H("#8A5A34"))
    elif name == "pencil":
        c.poly([(x - 150, y + 70), (x + 90, y - 90), (x + 125, y - 40), (x - 115, y + 120)], H("#FFD23F"))
        c.poly([(x - 150, y + 70), (x - 115, y + 120), (x - 185, y + 135)], H("#F2C27B"))
        c.poly([(x - 175, y + 122), (x - 165, y + 112), (x - 185, y + 135)], H("#333344"))
        c.poly([(x + 90, y - 90), (x + 125, y - 40), (x + 150, y - 57), (x + 115, y - 107)], H("#FF8FB1"))
    elif name == "queen":
        c.poly([(x - 140, y + 60), (x - 150, y - 80), (x - 70, y - 10), (x, y - 120),
                (x + 70, y - 10), (x + 150, y - 80), (x + 140, y + 60)], H("#FFD23F"))
        c.rect(x - 145, y + 50, x + 145, y + 100, H("#F2B705"), r=14)
        for dx, col in ((-75, "#E84A4A"), (0, "#4FA3E3"), (75, "#7CCB5A")):
            c.circle(x + dx, y + 75, 16, H(col))
        for dx, dy in ((-150, -80), (0, -120), (150, -80)):
            c.circle(x + dx, y + dy, 16, H("#FFF3B0"))
    elif name == "robot":
        c.rect(x - 8, y - 175, x + 8, y - 130, H("#8C96A8"))
        c.circle(x, y - 180, 16, H("#F06A5D"))
        c.rect(x - 95, y - 135, x + 95, y - 15, H("#AEB8C8"), r=26)
        c.circle(x - 40, y - 80, 22, H("#FFFFFF"))
        c.circle(x + 40, y - 80, 22, H("#FFFFFF"))
        c.circle(x - 40, y - 80, 10, H("#3E86E0"))
        c.circle(x + 40, y - 80, 10, H("#3E86E0"))
        c.rect(x - 40, y - 45, x + 40, y - 32, H("#5A6374"), r=6)
        c.rect(x - 110, y - 5, x + 110, y + 150, H("#8C96A8"), r=26)
        c.rect(x - 50, y + 30, x + 50, y + 90, H("#BFE6FF"), r=12)
        c.circle(x - 25, y + 120, 10, H("#FFD23F"))
        c.circle(x + 25, y + 120, 10, H("#7CCB5A"))
        c.rect(x - 160, y + 10, x - 115, y + 110, H("#AEB8C8"), r=20)
        c.rect(x + 115, y + 10, x + 160, y + 110, H("#AEB8C8"), r=20)
    elif name == "van":
        c.rect(x - 190, y - 100, x + 150, y + 70, H("#3E86E0"), r=30)
        c.rect(x + 100, y - 40, x + 195, y + 70, H("#3E86E0"), r=26)
        c.rect(x + 105, y - 25, x + 175, y + 15, H("#BFE6FF"), r=10)
        for wx in (-150, -55, 40):
            c.rect(wx + x, y - 75, wx + x + 75, y - 20, H("#BFE6FF"), r=10)
        for wx in (-110, 120):
            c.circle(x + wx, y + 75, 45, H("#333344"))
            c.circle(x + wx, y + 75, 20, H("#C8CCD6"))
    elif name == "watch":
        c.rect(x - 45, y - 190, x + 45, y + 190, H("#9B6BD3"), r=24)
        c.circle(x, y, 110, H("#F2B705"))
        c.circle(x, y, 92, H("#FFFFFF"))
        for k in range(12):
            a = k * math.pi / 6
            c.circle(x + math.cos(a) * 76, y + math.sin(a) * 76, 5, H("#555566"))
        c.line([(x, y), (x, y - 60)], H("#333344"), 10)
        c.line([(x, y), (x + 45, y + 15)], H("#333344"), 8)
        c.circle(x, y, 10, H("#E84A4A"))
    elif name == "xylophone":
        cols = ["#E84A4A", "#FFB020", "#7CCB5A", "#3E86E0", "#9B6BD3", "#FF8FB1"]
        c.poly([(x - 190, y - 60), (x + 190, y - 20), (x + 190, y + 20), (x - 190, y + 80)], H("#8A5A34"))
        for k, col in enumerate(cols):
            bx = x - 165 + k * 62
            hgt = 150 - k * 14
            c.rect(bx, y - hgt / 2 + 10 + k * 4, bx + 48, y + hgt / 2 + 10 + k * 4, H(col), r=10)
            c.circle(bx + 24, y - hgt / 2 + 25 + k * 4, 6, H("#FFFFFF"))
        c.line([(x + 60, y - 150), (x + 150, y - 60)], H("#B07A4A"), 10)
        c.circle(x + 50, y - 160, 22, H("#E84A4A"))
    elif name == "yo-yo":
        c.line([(x, y - 200), (x, y - 40)], H("#555566"), 4)
        c.circle(x, y + 30, 105, H("#E84A4A"))
        c.circle(x, y + 30, 70, H("#FF8A7A"))
        c.circle(x, y + 30, 22, H("#FFFFFF"))
        c.circle(x, y - 205, 18, None, outline=H("#555566"), width=5)
    elif name == "zebra":
        body, black = H("#FFFFFF"), H("#2B2B33")
        for lx in (-110, -60, 30, 80):
            c.rect(x + lx - 16, y + 40, x + lx + 16, y + 190, body, outline=black, width=4)
            for k in range(3):
                c.rect(x + lx - 16, y + 95 + k * 28, x + lx + 16, y + 105 + k * 28, black)
            c.rect(x + lx - 16, y + 175, x + lx + 16, y + 195, black, r=4)
        c.ellipse(x - 20, y + 20, 140, 80, body, outline=black, width=5)
        for k in range(6):
            c.line([(x - 120 + k * 45, y - 40), (x - 105 + k * 45, y + 80)], black, 14)
        c.poly([(x + 90, y - 20), (x + 130, y - 170), (x + 175, y - 160), (x + 150, y)], body,
               outline=black, width=5)
        c.ellipse(x + 175, y - 165, 55, 40, body, outline=black, width=5)
        c.ellipse(x + 210, y - 155, 22, 22, H("#3A3A44"))
        c.circle(x + 165, y - 180, 7, black)
        c.poly([(x + 140, y - 205), (x + 150, y - 250), (x + 165, y - 200)], body, outline=black, width=4)
        for k in range(5):
            c.line([(x + 105 + k * 10, y - 140 + k * 25), (x + 140 + k * 8, y - 150 + k * 25)], black, 8)
        c.line([(x - 160, y + 10), (x - 205, y + 80)], black, 8)


def object_image(name, size=840):
    old = art.SS
    art.SS = 4
    try:
        if name == "cat":
            im = art.milo()
            return im.resize((int(im.width * 2.2), int(im.height * 2.2)), Image.LANCZOS)
        n = {"apple": 210, "ball": 190, "orange": 180, "fish": 230, "gift": 240, "hat": 270,
             "kite": 300, "lamp": 400, "umbrella": 400, "dog": 380}.get(name, 460)
        c = art.Canvas(n, n)
        draw_object(c, name, n / 2, n / 2)
        return c.img.resize((size, size), Image.LANCZOS)
    finally:
        art.SS = old


def letter_frame(letter, word, idx):
    """Static parts of a letter scene: background + letter card (no object, no word)."""
    card, bg = PALETTE[idx % 4]
    c = art.Canvas(art.FW, art.FH)
    c.rect(0, 0, art.FW, art.FH, H(bg))
    for k in range(18):
        r = (idx * 37 + k * 53) % 997
        c.circle((r * 7) % art.FW, (r * 13) % art.FH, 10 + r % 20, H(card, 28))
    c.rect(90, 150, 860, 930, H("#000000", 40), r=70)
    c.rect(80, 130, 850, 910, H(card), r=70)
    big = art.font(470, "Bold")
    c.text(465, 520, letter + letter.lower(), big, H("#FFFFFF"), anchor="mm",
           stroke=10, stroke_fill=H("#2B2350", 90))
    art.moon(c, 1810, 110, 36)
    return c.final()


def word_label(letter, word):
    f = art.font(120, "Bold")
    w = int(f.getlength(word) + 120)
    c = art.Canvas(w, 170)
    c.rect(0, 0, w, 170, H("#FFFFFF", 245), r=50)
    first, rest = word[0], word[1:]
    x = 60
    c.text(x, 18, first, f, H("#FF6A1F"))
    x += f.getlength(first)
    c.text(x, 18, rest, f, H("#2D2A3E"))
    return c.final()


# ---------------------------------------------------------------- render
def render_letter(i, letter, word, work, voice):
    d = os.path.join(work, f"s{i:02d}")
    os.makedirs(d, exist_ok=True)
    lines = [(letter + ".", "narrator"), (f"{letter} is for {word}.", "narrator"),
             (f"{letter}, {letter}, {word}!", "lina" if i % 2 else "adams")]
    t, pieces, times = 0.4, [], []
    for j, (text, who) in enumerate(lines):
        p = os.path.join(d, f"l{j}.wav")
        dur = voice.say(text, who, p)
        pieces.append((t, p))
        times.append((t, t + dur))
        t += dur + 0.35
    total = t + 0.5
    buf = np.zeros(int(total * build.SR) + 1, dtype=np.float32)
    for start, p in pieces:
        a, _ = sf.read(p, dtype="float32")
        s = int(start * build.SR)
        buf[s:s + len(a)] += a[: len(buf) - s]
    apath = os.path.join(d, "audio.wav")
    sf.write(apath, buf, build.SR)

    frame = letter_frame(letter, word, i)
    frame.save(os.path.join(d, "bg.png"))
    obj = object_image(word)
    obj = obj.resize((int(obj.width * 0.78), int(obj.height * 0.78)), Image.LANCZOS)
    obj.save(os.path.join(d, "obj.png"))
    lab = word_label(letter, word)
    lab.save(os.path.join(d, "label.png"))
    show_obj = times[1][0] - 0.1
    ox = 1390 - obj.width // 2
    oy = 470 - obj.height // 2
    fc = (
        f"[0:v]format=rgba[b];"
        f"[b][1:v]overlay=x={ox}:y='{oy}+12*sin(2*PI*t*0.9)':eval=frame:"
        f"enable='gte(t,{show_obj:.2f})'[v1];"
        f"[v1][2:v]overlay=x={1390 - lab.width // 2}:y=860:enable='gte(t,{show_obj:.2f})'[v2];"
        f"[v2]fade=t=in:st=0:d=0.25,fade=t=out:st={total - 0.25:.2f}:d=0.25,format=yuv420p[v]"
    )
    out = os.path.join(work, f"seg{i:02d}.mp4")
    build.run(["ffmpeg", "-y", "-loglevel", "error",
               "-loop", "1", "-framerate", "30", "-t", f"{total:.2f}", "-i", os.path.join(d, "bg.png"),
               "-loop", "1", "-framerate", "30", "-t", f"{total:.2f}", "-i", os.path.join(d, "obj.png"),
               "-loop", "1", "-framerate", "30", "-t", f"{total:.2f}", "-i", os.path.join(d, "label.png"),
               "-i", apath, "-filter_complex", fc, "-map", "[v]", "-map", "3:a",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "30",
               "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", "-t", f"{total:.2f}", out])
    return out, total


def alphabet_board():
    c = art.Canvas(art.BW, art.BH)
    art.sky(c, "night", "sunny")
    art.stars(c, 80, 4)
    art.moon(c, 1950, 150, 70)
    c.text(art.BW / 2, 140, "A B C ... we did it!", art.font(96, "Bold"), H("#FFE680"), anchor="mm",
           stroke=6, stroke_fill=H("#2B2350"))
    f = art.font(96, "Bold")
    for k, (L, _) in enumerate(LETTERS):
        row, col = divmod(k, 9)
        x = 210 + col * 210
        y = 330 + row * 250
        card, _bg = PALETTE[k % 4]
        c.rect(x - 85, y - 95, x + 85, y + 95, H(card), r=34)
        c.text(x, y, L, f, H("#FFFFFF"), anchor="mm")
    return c.final()


def thumbnail():
    W, Hh = 1280, 720
    c = art.Canvas(W, Hh)
    c.rect(0, 0, W, Hh, H("#F1E8FF"))
    c.rect(30, 40, 560, 680, H("#8E5BD6"), r=60)
    c.text(295, 330, "Aa", art.font(330, "Bold"), H("#FFFFFF"), anchor="mm", stroke=8, stroke_fill=H("#2B2350", 90))
    c.rect(60, 560, 530, 655, H("#2B2350"), r=30)
    c.text(295, 607, "A to Z Phonics", art.font(56, "Bold"), H("#FFE680"), anchor="mm")
    old = art.SS
    art.SS = 2
    apple = object_image("apple", 500)
    art.SS = old
    c.paste(apple, 640, 175)
    c.rect(620, 30, 1250, 150, H("#FFFFFF", 240), r=40)
    c.text(935, 90, "A for Apple", art.font(84, "Bold"), H("#FF6A1F"), anchor="mm")
    im = art.CHARACTERS["lina"]()
    im = im.resize((int(im.width * 0.62), int(im.height * 0.62)), Image.LANCZOS)
    c.paste(im, 1150 - im.width / 2, Hh - im.height + 20)
    return c.final().convert("RGB")


def main():
    out_dir = sys.argv[1]
    slug = "abc-phonics"
    work = os.path.join(out_dir, "work_" + slug)
    os.makedirs(work, exist_ok=True)
    tts = os.environ.get("MT_TTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts"))
    voice = build.Voice(tts)
    clips, total = [], 0.0

    intro = {"lines": [
        {"text": "Hello, friends! Welcome to Moon Tales Kids!"},
        {"who": "lina", "text": "Today we learn the A B C!"},
        {"who": "adams", "text": "From A to Z. Let's say every letter together!"},
        {"text": "Listen, look, and say it with us. Are you ready? Let's go!"}]}
    title_img = art.title_card("A B C Phonics", "A for Apple to Z for Zebra!")
    print("intro", flush=True)
    os.makedirs(work + "/intro", exist_ok=True)
    clip, d = build.render_segment(0, intro, work + "/intro", voice, title_img=title_img)
    clips.append(clip)
    total += d
    for k, (L, w) in enumerate(LETTERS):
        print(f"letter {L}", flush=True)
        clip, d = render_letter(k, L, w, work, voice)
        clips.append(clip)
        total += d
    # recap + goodbye
    board = alphabet_board()
    outro = {"setting": "park", "time": "night", "weather": "sunny", "chars": ["lina", "adams"], "lines": [
        {"text": "Great job, friends! You said all the letters from A to Z!"},
        {"who": "lina", "text": "A, B, C, D, E, F, G."},
        {"who": "adams", "text": "H, I, J, K, L, M, N, O, P."},
        {"who": "lina", "text": "Q, R, S, T, U, V."},
        {"who": "adams", "text": "W, X, Y, and Z!"},
        {"text": "Now you know your A B C. Ask a grown-up to subscribe to Moon Tales Kids for more!"},
        {"who": "lina", "text": "Bye, bye, friends!"}]}
    os.makedirs(work + "/outro", exist_ok=True)
    print("outro", flush=True)
    clip, d = build.render_segment(1, outro, work + "/outro", voice, title_img=board)
    clips.append(clip)
    total += d

    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as f:
        f.write("".join(f"file '{c}'\n" for c in clips))
    joined = os.path.join(work, "joined.mp4")
    build.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
    mpath = os.path.join(work, "music.wav")
    build.music(total, mpath, seed=9)
    final = os.path.join(out_dir, slug + ".mp4")
    build.run(["ffmpeg", "-y", "-loglevel", "error", "-i", joined, "-i", mpath, "-filter_complex",
               "[1:a]volume=0.18[m];[0:a][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]",
               "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
               "-movflags", "+faststart", final])
    thumbnail().save(os.path.join(out_dir, slug + "_thumb.jpg"), quality=92)
    words = "\n".join(f"{L} — {w}" for L, w in LETTERS)
    meta = {
        "title": "ABC Phonics for Kids 🍎 A for Apple to Z for Zebra | Learn the Alphabet in English | Moon Tales Kids",
        "description": (
            "Learn the English alphabet with Lina and Adams! 🔤🍎🦓\n"
            "Say every letter from A to Z, hear its word, and repeat: A for apple, B for ball, C for cat… "
            "all the way to Z for zebra!\n\n📚 Letters and words in this video:\n" + words +
            "\n\n👨‍👩‍👧 For parents: say each letter with your child and point to the picture. "
            "Perfect for toddlers, preschool and kids aged 2 to 6 learning English.\n\n"
            "🇲🇦 تعلم الحروف الإنجليزية للأطفال من A إلى Z مع لينا وآدم.\n"
            "🇫🇷 Apprendre l'alphabet anglais pour enfants de A à Z avec Lina et Adams.\n\n"
            "🌙 Subscribe to Moon Tales Kids for new English videos every day!\n\n"
            "#ABC #Phonics #Alphabet #EnglishForKids #MoonTalesKids"),
        "tags": ["abc phonics", "abc song for kids", "alphabet for kids", "a for apple", "phonics for toddlers",
                 "learn abc", "abcd for kids", "Moon Tales Kids", "Lina and Adams",
                 "الحروف الانجليزية للاطفال", "تعلم الحروف الانجليزية", "حروف ABC للاطفال",
                 "alphabet anglais enfant", "apprendre l'alphabet anglais", "abc en anglais"],
        "duration_seconds": round(total, 1),
    }
    json.dump(meta, open(os.path.join(out_dir, slug + "_meta.json"), "w"), ensure_ascii=False, indent=2)
    print(f"done: {final} ({total / 60:.1f} min)")




# ---------------------------------------------------------------- Shorts
SHORT_GROUPS = [(0, 6), (6, 12), (12, 18), (18, 26)]   # A–F, G–L, M–R, S–Z


def shorts(out_dir):
    """Four vertical Shorts (A–F, G–L, M–R, S–Z) from the built letter clips."""
    import short as sh
    slug = "abc-phonics"
    work = os.path.join(out_dir, "work_" + slug)
    music = os.path.join(work, "music.wav")
    for n, (a, b) in enumerate(SHORT_GROUPS, 1):
        segs = [os.path.join(work, f"seg{k:02d}.mp4") for k in range(a, b)]
        durs = [sh.dur(s) for s in segs]
        while sum(durs) > 58.5:
            segs.pop(), durs.pop()
        last = a + len(segs) - 1
        span = f"{LETTERS[a][0]} to {LETTERS[last][0]}"
        total = sum(durs)
        ov = os.path.join(work, f"abc_short_overlay{n}.png")
        W, Hh = 1080, 1920
        c = art.Canvas(W, Hh)
        c.rect(40, 90, W - 40, 560, H("#FFFFFF", 240), r=60)
        c.rect(40, 90, W - 40, 560, None, r=60, outline=H("#FFB020"), width=12)
        c.text(W / 2, 200, "ABC Phonics", art.font(84, "SemiBold"), H("#7A6A9A"), anchor="mm")
        c.text(W / 2, 390, span, art.font(170, "Bold"), H("#FF7A30"), anchor="mm")
        c.rect(70, 1460, W - 70, 1760, H("#2B2350", 235), r=60)
        c.text(W / 2, 1555, "Full A to Z on", art.font(64, "Medium"), H("#FFFFFF"), anchor="mm")
        c.text(W / 2, 1660, "Moon Tales Kids", art.font(86, "Bold"), H("#FFE680"), anchor="mm")
        c.final().save(ov)
        inputs = []
        for s in segs:
            inputs += ["-i", s]
        k = len(segs)
        fc = ["".join(f"[{i}:v][{i}:a]" for i in range(k)) + f"concat=n={k}:v=1:a=1[cv][ca]",
              "[cv]split=2[x][y]",
              "[x]scale=-2:1920,crop=1080:1920,boxblur=30:3,eq=brightness=0.06[bg]",
              "[y]scale=1080:-2[fg]", "[bg][fg]overlay=0:(H-h)/2-40[m]",
              f"[m][{k}:v]overlay=0:0,format=yuv420p[v]",
              f"[{k + 1}:a]volume=0.12,atrim=0:{total:.2f}[mu]",
              "[ca][mu]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[au]"]
        out = os.path.join(out_dir, f"{slug}_short{n}.mp4")
        build.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-loop", "1", "-framerate", "30",
                   "-t", f"{total:.2f}", "-i", ov, "-i", music, "-filter_complex", ";".join(fc),
                   "-map", "[v]", "-map", "[au]", "-t", f"{total:.2f}", "-c:v", "libx264",
                   "-preset", "veryfast", "-crf", "21", "-r", "30", "-c:a", "aac", "-b:a", "128k",
                   "-movflags", "+faststart", out])
        words = ", ".join(f"{L} for {w}" for L, w in LETTERS[a:last + 1])
        meta = {"title": f"ABC Phonics {span} 🔤 {LETTERS[a][0]} for {LETTERS[a][1].capitalize()} | Alphabet for kids #shorts",
                "description": f"Learn the English letters {span}: {words}!\n\n"
                               "🇲🇦 تعلم الحروف الإنجليزية للأطفال\n🇫🇷 Apprendre l'alphabet anglais\n\n"
                               "Watch the full A to Z video on Moon Tales Kids! 🌙\n\n#shorts #ABC #Phonics #EnglishForKids",
                "tags": ["abc phonics", "alphabet for kids", "abc song", "phonics for toddlers", "kids shorts",
                         "Moon Tales Kids", "الحروف الانجليزية للاطفال", "تعلم الحروف", "alphabet anglais enfant",
                         "apprendre l'alphabet"]}
        json.dump(meta, open(os.path.join(out_dir, f"{slug}_short{n}_meta.json"), "w"), ensure_ascii=False, indent=2)
        print(f"short {n}: {span} ({total:.0f} s)")


if __name__ == "__main__":
    if "--shorts" in sys.argv:
        shorts(sys.argv[1])
    else:
        main()

"""Spot the Difference videos (QuizNado design).

One picture per puzzle (e.g. made with ChatGPT). This script makes the second picture itself with
EXACTLY 5 changes, so the reveal circles are always right.

Usage:  python3 spotdiff.py spotpacks/<slug>.json OUT_DIR [long|shorts|all|preview]

Pack JSON:
  slug, title, name, tags[], ar, fr, hashtags,
  puzzles[]: {image, level (0-3), edits[5]}, coordinates in the picture's own pixels
  shorts[]:  {puzzle: index, title}
Edits:
  {"type": "recolor", "box": [x0,y0,x1,y1], "hue": 120}            colour of the main object in the box
  {"type": "recolor", "box": [...], "to": "#3E86E0"}                 paint it a given colour
  {"type": "remove",  "box": [...], "src": [dx, dy]}                 cover it with the area dx,dy away
  {"type": "copy",    "box": [...], "to": [x, y]}                    duplicate the box at x,y (top-left)
  {"type": "flip",    "box": [...]}                                  mirror the object left-right
  {"type": "scale",   "box": [...], "factor": 1.35}                  make it bigger / smaller
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art  # noqa: E402
import build  # noqa: E402
import quiz  # noqa: E402
import quizpack  # noqa: E402  (loads the QuizNado brand)
from quiz import Timeline  # noqa: E402
from quizpack import LEVELS, WORDS, CHANNEL, card, pill, write_kit  # noqa: E402

H = art.hexc
SEARCH = [15, 20, 25, 30]  # seconds to search, per level
RED = (232, 49, 47)


# ---------------------------------------------------------------- picture edits
import cv2  # noqa: E402


def border_mask(patch, tol=38, keep_all=False):
    """Object pixels inside a box: everything that differs from the box's border (background) colour."""
    a = np.asarray(patch.convert("RGB")).astype(np.float32)
    ring = np.concatenate([a[:2].reshape(-1, 3), a[-2:].reshape(-1, 3), a[:, :2].reshape(-1, 3), a[:, -2:].reshape(-1, 3)])
    bg = np.median(ring, axis=0)
    m = (np.sqrt(((a - bg) ** 2).sum(axis=2)) > tol).astype(np.uint8) * 255
    k = np.ones((3, 3), np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
    if n > 2 and not keep_all:  # keep the big pieces only
        keep = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > 0.08 * stats[1:, cv2.CC_STAT_AREA].max()]
        m = np.isin(lab, keep).astype(np.uint8) * 255
    return m


def soft(m, grow=2, blur=1.2):
    if grow:
        m = cv2.dilate(m, np.ones((grow * 2 + 1, grow * 2 + 1), np.uint8))
    return Image.fromarray(m).filter(ImageFilter.GaussianBlur(blur))


def center_mask(patch, tol=60, ref_xy=None):
    """Pixels with the same colour as the middle of the box (or as the point ref_xy, box coords)."""
    a = np.asarray(patch.convert("RGB")).astype(np.float32)
    h, w, _ = a.shape
    if ref_xy:
        rx, ry = int(ref_xy[0]), int(ref_xy[1])
        ref = np.median(a[max(ry - 6, 0):ry + 7, max(rx - 6, 0):rx + 7].reshape(-1, 3), axis=0)
    else:
        ref = np.median(a[int(h * .4):int(h * .6), int(w * .4):int(w * .6)].reshape(-1, 3), axis=0)
    return (np.sqrt(((a - ref) ** 2).sum(axis=2)) < tol).astype(np.uint8) * 255


def hue_rotate(patch, deg):
    hsv = np.asarray(patch.convert("RGB").convert("HSV")).copy()
    hsv[..., 0] = (hsv[..., 0].astype(int) + int(deg / 360 * 255)) % 256
    return Image.fromarray(hsv, "HSV").convert("RGB")


def colorize(patch, hexcol):
    rgb = np.asarray(patch.convert("RGB")).astype(np.float32)
    lum = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) / 255
    t = np.array(H(hexcol)[:3], np.float32)
    out = np.clip(t[None, None, :] * (0.35 + 0.9 * lum[..., None]), 0, 255)
    return Image.fromarray(out.astype(np.uint8))


def erase(img, box, m):
    """Remove the masked object from img (inpainting from the surroundings)."""
    x0, y0, x1, y1 = box
    full = np.zeros((img.height, img.width), np.uint8)
    full[y0:y1, x0:x1] = cv2.dilate(m, np.ones((9, 9), np.uint8))
    arr = cv2.inpaint(np.asarray(img)[:, :, ::-1].copy(), full, 9, cv2.INPAINT_TELEA)[:, :, ::-1]
    img.paste(Image.fromarray(np.ascontiguousarray(arr)))


def feather_mask(w, h, k=0.12):
    m = Image.new("L", (w, h), 0)
    pad = max(2, int(min(w, h) * k))
    ImageDraw.Draw(m).rounded_rectangle((pad, pad, w - pad, h - pad), radius=pad * 2, fill=255)
    return m.filter(ImageFilter.GaussianBlur(pad * 0.8))


def rect_mask(w, h, k=0.14):
    """Soft rectangle: fully opaque in the middle, fading at the edges (for textured backgrounds)."""
    return feather_mask(w, h, k)


def apply_edit(img, e):
    """img: RGB picture (edited in place). Returns the circle (cx, cy, r) for the reveal.

    mode "box" (flip / scale / copy): move the whole box with soft edges (object must sit in its middle).
    remove with "src": [dx, dy]: cover the object with the area dx,dy away (good for grass, sand, water).
    """
    x0, y0, x1, y1 = [int(v) for v in e["box"]]
    w, h = x1 - x0, y1 - y0
    patch = img.crop((x0, y0, x1, y1))
    t = e["type"]
    box_mode = e.get("mode") == "box"
    cx, cy, rad = (x0 + x1) / 2, (y0 + y1) / 2, max(w, h) / 2 * 1.0 + 10
    if box_mode:
        rad = max(w, h) / 2 * 0.85 + 10
    tol = e.get("tol", 38)
    if t == "recolor":
        new = colorize(patch, e["to"]) if e.get("to") else hue_rotate(patch, e.get("hue", 140))
        ref = [e["ref"][0] - x0, e["ref"][1] - y0] if "ref" in e else None
        m = center_mask(patch, e.get("tol", 60), ref) if e.get("part") else border_mask(patch, tol, e.get("all"))
        m = np.minimum(m, np.asarray(feather_mask(w, h, 0.03)))
        img.paste(new, (x0, y0), soft(m, 1, 1.0))
    elif t == "remove":
        if "src" in e:
            dx, dy = e["src"]
            src = img.crop((x0 + dx, y0 + dy, x1 + dx, y1 + dy))
            if e.get("rect"):
                mm = rect_mask(w, h, e.get("k", 0.16))
            else:  # cover the object (grown a little) with the neighbouring background
                mm = soft(border_mask(patch, tol, True), e.get("grow", 9), 3)
            img.paste(src, (x0, y0), mm)
        else:
            erase(img, (x0, y0, x1, y1), border_mask(patch, tol, e.get("all")))
    elif t == "copy":
        tx, ty = [int(v) for v in e["to"]]
        mm = rect_mask(w, h, 0.16) if box_mode else soft(border_mask(patch, tol), 1, 1.0)
        img.paste(patch, (tx, ty), mm)
        cx, cy = tx + w / 2, ty + h / 2
    elif t == "flip":
        if box_mode:
            img.paste(patch.transpose(Image.FLIP_LEFT_RIGHT), (x0, y0), rect_mask(w, h, 0.14))
        else:
            m = border_mask(patch, tol)
            erase(img, (x0, y0, x1, y1), m)
            img.paste(patch.transpose(Image.FLIP_LEFT_RIGHT), (x0, y0), soft(m, 1, 1.0).transpose(Image.FLIP_LEFT_RIGHT))
    elif t == "scale":
        f = e.get("factor", 1.35)
        nw, nh = int(w * f), int(h * f)
        big = patch.resize((nw, nh), Image.LANCZOS)
        if e.get("shape") == "circle":
            m0 = Image.new("L", (nw * 4, nh * 4), 0)
            ImageDraw.Draw(m0).ellipse((6, 6, nw * 4 - 6, nh * 4 - 6), fill=255)
            mm = m0.resize((nw, nh), Image.LANCZOS)
        elif box_mode:
            mm = rect_mask(nw, nh, 0.15)
        else:
            m = border_mask(patch, tol)
            if f < 1:
                erase(img, (x0, y0, x1, y1), m)
            mm = soft(m, 1, 1.0).resize((nw, nh), Image.LANCZOS)
        img.paste(big, (int(cx - nw / 2), int(cy - nh / 2)), mm)
        rad = max(nw, nh) / 2 * (0.85 if box_mode else 1.0) + 10
    else:
        raise ValueError(t)
    if "circle" in e:  # manual circle override [cx, cy, r]
        cx, cy, rad = e["circle"]
    return cx, cy, rad


class Puzzle:
    def __init__(self, spec, base_dir):
        path = spec["image"] if os.path.isabs(spec["image"]) else os.path.join(base_dir, spec["image"])
        self.a = Image.open(path).convert("RGB")
        self.b = self.a.copy()
        self.level = spec.get("level", 0)
        self.circles = [apply_edit(self.b, e) for e in spec["edits"]]
        assert len(self.circles) == 5, "every puzzle needs exactly 5 edits"


# ---------------------------------------------------------------- frames
def fit(img, bw, bh):
    s = min(bw / img.width, bh / img.height)
    return s, int(img.width * s), int(img.height * s)


def draw_pictures(c, pz, boxes, found):
    """Paste A and B into boxes; red circles for the first `found` differences (on both)."""
    for img, (bx0, by0, bx1, by1) in zip((pz.a, pz.b), boxes):
        s, w, h = fit(img, bx1 - bx0, by1 - by0)
        x, y = bx0 + (bx1 - bx0 - w) / 2, by0 + (by1 - by0 - h) / 2
        c.rect(x - 8, y - 8, x + w + 8, y + h + 8, H("#FFFFFF"), r=18)
        im = img.resize((int(w * art.SS), int(h * art.SS)), Image.LANCZOS).convert("RGBA")
        c.img.alpha_composite(im, (int(x * art.SS), int(y * art.SS)))
        for (cx, cy, r) in pz.circles[:found]:
            rr = max(r * s, 22)
            c.circle(x + cx * s, y + cy * s, rr, None, outline=H("#E8312F"), width=7)


def sd_frame(pz, vertical, header, number, total, timer, found, note=None, footer=None, tmax=20):
    W, Hh = (1080, 1920) if vertical else (1920, 1080)
    c = art.Canvas(W, Hh)
    c.rect(0, 0, W, Hh, H("#F1E8FF"))
    for k in range(18):
        r = (k * 71 + (number or 0) * 13) % 997
        c.circle((r * 7) % W, (r * 11) % Hh, 12 + r % 24, H("#8E5BD6", 22))
    hb = (40, 40, W - 40, 190) if vertical else (40, 22, W - 40, 132)
    c.rect(*hb, H("#2B2350"), r=50)
    quiz.brand_header(c, W, hb, vertical, header + (f"  {number}/{total}" if number else ""), 64 if vertical else 60)
    lv = pill(pz.level)
    lf = art.font(48, "Bold")
    py = 255 if vertical else 178
    lw = lf.getlength(lv[0]) + 90
    c.rect(W / 2 - lw / 2, py - 36, W / 2 + lw / 2, py + 36, H(lv[1]), r=36)
    c.text(W / 2, py, lv[0], lf, H("#FFFFFF"), anchor="mm")
    boxes = [(40, 310, 1040, 940), (40, 965, 1040, 1595)] if vertical else [(30, 225, 950, 790), (970, 225, 1890, 790)]
    draw_pictures(c, pz, boxes, found)
    # found counter: 5 dots
    dy = 1665 if vertical else 860
    dx0 = W / 2 - 2 * 92 if vertical else 1260
    if not vertical and not note:
        c.text(560, dy, "Find 5 differences!", art.font(54, "Bold"), H("#2B2350"), anchor="mm")
    for i in range(5):
        x = dx0 + i * 92
        c.circle(x, dy, 34, H("#E8312F") if i < found else H("#FFFFFF"), outline=H("#E8312F"), width=6)
        if i < found:
            c.text(x, dy, str(i + 1), art.font(40, "Bold"), H("#FFFFFF"), anchor="mm")
    # timer or note
    if timer is not None:
        tx, ty, tr = (W / 2, 1800, 80) if vertical else (960, 860, 66)
        c.circle(tx, ty, tr + 8, H("#2B2350"))
        c.circle(tx, ty, tr, H("#FFFFFF"))
        c.pie(tx, ty, tr, tr, -90, -90 + 360 * timer / tmax, H("#FF7A30") if timer > 5 else H("#E8312F"))
        c.circle(tx, ty, tr - 18, H("#FFFFFF"))
        c.text(tx, ty, str(timer), art.font(int(tr * 0.95), "Bold"), H("#2B2350"), anchor="mm")
    elif note:
        if vertical:
            nf = 58
            while nf > 36 and art.font(nf, "Bold").getlength(note) > W - 100:
                nf -= 2
            c.text(W / 2, 1800, note, art.font(nf, "Bold"), H("#7A4FC0"), anchor="mm")
        else:
            c.text(640, 860, note, art.font(54, "Bold"), H("#7A4FC0"), anchor="mm")
    if footer and not vertical:
        c.rect(W / 2 - 560, 1000, W / 2 + 560, 1056, H("#2B2350", 220), r=28)
        c.text(W / 2, 1028, footer, art.font(36, "SemiBold"), H("#FFE680"), anchor="mm")
    return c.final().convert("RGB")


# ---------------------------------------------------------------- one puzzle
def play(tl, pz, vertical, header, number, total, intro_say, footer=None, search=None):
    t_search = search or SEARCH[pz.level]
    note = f"{t_search} seconds... GO!"
    d = tl.say(intro_say)
    tl.show(sd_frame(pz, vertical, header, number, total, None, 0, note, footer), d + 0.3)
    for s in range(t_search, 0, -1):
        tl.add_sound(quiz.TICK * (1.0 if s <= 5 else 0.45), tl.t)
        tl.show(sd_frame(pz, vertical, header, number, total, s, 0, None, footer, t_search), 1.0)
    d = tl.say("Time's up! Here are the five differences.")
    tl.show(sd_frame(pz, vertical, header, number, total, None, 0, "Time's up!", footer), d + 0.2)
    for k in range(1, 6):
        tl.add_sound(quiz.DING, tl.t)
        tl.show(sd_frame(pz, vertical, header, number, total, None, k, f"{k}/5", footer), 1.1)


def load(path):
    p = json.load(open(path))
    base = os.path.dirname(os.path.abspath(path))
    return p, [Puzzle(s, base) for s in p["puzzles"]]


def thumbnail(p, pzs, path):
    pz = pzs[-1]
    c = art.Canvas(1280, 720)
    c.rect(0, 0, 1280, 720, H("#F1E8FF"))
    c.rect(30, 18, 1250, 150, H("#2B2350"), r=44)
    quiz.paste_logo(c, 105, 84, 160)
    fs = 92
    while art.font(fs, "Bold").getlength(p["thumb_top"]) > 1010:
        fs -= 4
    c.text(715, 84, p["thumb_top"], art.font(fs, "Bold"), H("#FFE680"), anchor="mm")
    for k, (img, x) in enumerate(((pz.a, 30), (pz.b, 655))):
        s, w, h = fit(img, 595, 420)
        y = 175 + (420 - h) / 2
        xx = x + (595 - w) / 2
        c.rect(xx - 7, y - 7, xx + w + 7, y + h + 7, H("#FFFFFF"), r=16)
        im = img.resize((int(w * art.SS), int(h * art.SS)), Image.LANCZOS).convert("RGBA")
        c.img.alpha_composite(im, (int(xx * art.SS), int(y * art.SS)))
        if k == 1:
            cx, cy, r = pz.circles[0]
            c.circle(xx + cx * s, y + cy * s, max(r * s, 26), None, outline=H("#E8312F"), width=9)
    c.rect(150, 618, 1130, 700, H("#E8312F"), r=41)
    c.text(640, 659, p["thumb_bottom"], art.font(52, "Bold"), H("#FFFFFF"), anchor="mm")
    c.final().convert("RGB").save(path, quality=92)


def build_long(p, pzs, out_dir, voice):
    slug, n = p["slug"], len(pzs)
    work = os.path.join(out_dir, "work_" + slug)
    os.makedirs(work, exist_ok=True)
    tl = Timeline(work, voice)
    hdr = "Spot the difference"
    last = pzs[-1]
    d = tl.say("Can you find all five differences in this picture? It's the hardest one in this video. "
               "Keep watching: the answer is at the end!")
    tl.show(sd_frame(last, False, "Can you find all 5?", None, None, None, 0, "Answer at the end!",
                     "The answer is at the end of the video!"), d + 0.5)
    intro = card("Spot the Difference: Easy to Impossible", [f"{n} puzzles", "5 differences each",
                                                             "Count what you find!"], logo=True)
    for text in (f"Welcome to {CHANNEL}! Spot the difference, from easy to impossible!",
                 f"{n} puzzles, five differences each. The time gets shorter for you... and the puzzles get harder. "
                 "Count how many differences you find!",
                 "At the end, share your score in the comments. Ready? Let's go!"):
        d = tl.say(text)
        tl.show(intro, d + 0.3)
    level_say = ["Level one: easy!", "Level two: medium. Look carefully!", "Level three: hard!",
                 "Level four: impossible! Only sharp eyes find all five."]
    footers = ["Level 1 · Easy: count your differences!", "Level 2 · Medium: how many so far?",
               "Level 3 · Hard: don't stop now!", "Level 4 · Impossible: the puzzle from the start is coming!"]
    num, prev = 0, -1
    for pz in pzs:
        li = pz.level
        if li != prev:
            if prev == 1:
                cta = card(f"Enjoying {CHANNEL}?", ["Like & subscribe!", "It helps us make", "more puzzles",
                                                    "!Then: level 3..."], logo=True)
                d = tl.say(f"If you like it until now, hit like and subscribe to {CHANNEL}! "
                           "It really helps us make more puzzles. Now, level three!")
                tl.show(cta, d + 0.6)
            cnt = sum(1 for z in pzs if z.level == li)
            d = tl.say(level_say[li])
            tl.show(card(f"Level {li + 1}: {WORDS[li]}", [f"{cnt} puzzles", f"{SEARCH[li]} seconds each"],
                         highlight=li), d + 0.7)
            prev = li
        num += 1
        say = f"Puzzle {num}. Find five differences in {SEARCH[li]} seconds. Go!"
        if pz is last:
            say = "And now, the puzzle from the start of the video! " + say
        play(tl, pz, False, hdr, num, n, say, footers[li])
        d = tl.say("How many did you find?")
        tl.show(sd_frame(pz, False, hdr, num, n, None, 5, "How many did you find?", footers[li]), d + 0.6)
    tot = n * 5
    res = card("Your score?", [f"{tot}/{tot}: Eagle eyes!", f"{int(tot * .8)}–{tot - 1}: Excellent",
                               f"{int(tot * .6)}–{int(tot * .8) - 1}: Good", f"0–{int(tot * .6) - 1}: Keep practising",
                               "!Comment your score!"])
    for text in (f"Finished! How many differences did you find, out of {tot}?",
                 "Share your score in the comments! We read every comment."):
        d = tl.say(text)
        tl.show(res, d + 0.8)
    end = card("Thank you!", [f"Subscribe to {CHANNEL}", "& hit like!", "New puzzles every week",
                              "!Easy to Impossible"], logo=True)
    d = tl.say(f"If you enjoyed it, hit like and subscribe to {CHANNEL}. New puzzles every week. See you next time!")
    tl.show(end, d + 1.2)
    out = os.path.join(out_dir, slug + ".mp4")
    tl.render(out, music_vol=0.06)
    thumbnail(p, pzs, os.path.join(out_dir, slug + "_thumb.jpg"))
    desc = (f"{p['about']} 👀\n"
            "4 levels: 🟢 Easy · 🟡 Medium · 🟠 Hard · 🔴 Impossible\n"
            f"{n} puzzles, 5 differences each. Count how many you find!\n"
            "👀 The hardest puzzle is at the start... and the answer is at the end!\n\n"
            f"💬 Share your score in the comments! Example: {int(tot * .8) + 2}/{tot} 🎉\n"
            f"🔔 Subscribe to {CHANNEL} 🌪️ for new puzzles every 3 days!\n\n"
            f"🇲🇦 {p['ar']}\n🇫🇷 {p['fr']}\n\n{p['hashtags']} #{CHANNEL}")
    write_kit(out_dir, slug, {"title": p["title"], "description": desc, "tags": p["tags"]}, False)
    print(f"done: {out} ({tl.t / 60:.1f} min)", flush=True)


def build_short(p, pzs, out_dir, voice, si):
    s = p["shorts"][si]
    pz = pzs[s["puzzle"]]
    name = f"{p['slug']}_short{si + 1}"
    work = os.path.join(out_dir, "work_" + name)
    os.makedirs(work, exist_ok=True)
    tl = Timeline(work, voice)
    secs = min(SEARCH[pz.level], 25)
    d = tl.say(f"Can you find all five differences in {secs} seconds?")
    tl.show(sd_frame(pz, True, "Find 5 differences!", None, None, None, 0, f"Only {secs} seconds!"), d + 0.2)
    play(tl, pz, True, "Spot the difference", None, None, "Go!", None, secs)
    d = tl.say(f"Found all five? Comment your score! More puzzles on our channel. Subscribe to {CHANNEL}!")
    tl.show(card("Score?", ["How many did you find?", "Comment: 3/5? 5/5?", "More puzzles on our channel!",
                            f"!Subscribe to {CHANNEL}!"], vertical=True, logo=True), d + 1.0)
    out = os.path.join(out_dir, name + ".mp4")
    tl.render(out, music_vol=0.07, vertical=True)
    desc = (f"Spot the difference: can you find all 5 in {secs} seconds? 👀\n"
            "💬 Comment your score: 1/5, 3/5 or 5/5?\n"
            f"🎬 Want more? \"{p['title'].split(' |')[0]}\" is on our channel!\n"
            f"👍 Liked it? Like & subscribe to {CHANNEL} 🌪️ for new puzzles every 3 days!\n\n"
            f"🇲🇦 {p['ar']}\n🇫🇷 {p['fr']}\n\n#shorts {p['hashtags']} #{CHANNEL}")
    write_kit(out_dir, name, {"title": s["title"], "description": desc, "tags": p["tags"]}, True)
    print(f"short: {out} ({tl.t:.0f} s)", flush=True)


if __name__ == "__main__":
    p, pzs = load(sys.argv[1])
    out_dir = sys.argv[2]
    what = sys.argv[3] if len(sys.argv) > 3 else "all"
    os.makedirs(out_dir, exist_ok=True)
    if what == "preview":
        for i, pz in enumerate(pzs):
            sd_frame(pz, False, "Spot the difference", i + 1, len(pzs), None, 5, "5/5").save(
                os.path.join(out_dir, f"{p['slug']}_pv{i + 1}.png"))
        if pzs:
            sd_frame(pzs[0], True, "Spot the difference", None, None, 12, 0).save(
                os.path.join(out_dir, f"{p['slug']}_pv_short.png"))
            thumbnail(p, pzs, os.path.join(out_dir, f"{p['slug']}_thumb.jpg"))
        sys.exit()
    tts = os.environ.get("MT_TTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts"))
    v = build.Voice(tts)
    if what in ("shorts", "all"):
        for i in range(len(p.get("shorts", []))):
            build_short(p, pzs, out_dir, v, i)
    if what in ("long", "all"):
        build_long(p, pzs, out_dir, v)

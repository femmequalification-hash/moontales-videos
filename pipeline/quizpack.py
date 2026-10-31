""""Easy to Impossible" quiz packs in the channel's purple quiz design.

One pack (quizpacks/<slug>.json) = 1 long video (32 questions, 4 levels) + 1 vertical teaser Short:
2 hard questions with answers, then the long video's IMPOSSIBLE question WITHOUT answer, ending on
"Want the answer? Watch the full video" with the long video's thumbnail (Zahra's rule, Oct 2026).

Usage:  python3 quizpack.py quizpacks/<slug>.json OUT_DIR [long|short|all|preview]

Pack JSON: name, header, noun, read_options, title, about, thumb{top, card[]}, ar, fr, hashtags,
tags[], levels[4][8] of [shown, options, answer, why, (spoken)], shorts[{picks[[level, index]], title}],
optional spoken_cycle[] (spoken question used in turn when the question is always the same).
The last question of level 4 is shown at the start of the long video as a teaser (open loop).
"""
import hashlib
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art  # noqa: E402
import build  # noqa: E402
import quiz  # noqa: E402
from quiz import Q, Timeline, frame  # noqa: E402
from PIL import Image  # noqa: E402

LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brand", "quiznado_logo.png")
CHANNEL = "QuizNado"
if os.path.exists(LOGO):
    quiz.BRAND = {"logo": Image.open(LOGO).convert("RGBA"), "name": CHANNEL}

H = art.hexc
LEVELS = [("EASY", "#2FA84F"), ("MEDIUM", "#E39A00"), ("HARD", "#FF6A1F"), ("IMPOSSIBLE", "#E23B3B")]
WORDS = ["Easy", "Medium", "Hard", "Impossible"]
FIXED = {"both are correct", "they're the same", "none", "all of them"}
LET = "ABCD"
NUM = ["zero", "one", "two", "three", "four"]


def pill(li, prefix=True):
    return ((f"LEVEL {li + 1} · " if prefix else "") + LEVELS[li][0], LEVELS[li][1])


def shuffled(shown, opts, ans):
    if any(o.lower() in FIXED for o in opts):
        return list(opts)
    o = list(opts)
    random.Random(hashlib.md5((shown + ans + "".join(opts)).encode()).hexdigest()).shuffle(o)
    return o


SAY = (("°C", " degrees Celsius"), ("km/h", " kilometres per hour"), ("$1.10", "one dollar ten"),
       ("$1.05", "one dollar five"), ("$1", "one dollar"), (" × ", " times "), ("×", " times "),
       (" ÷ ", " divided by "), (" + ", " plus "), (" − ", " minus "), (" = ", " equals "), ("%", " percent"),
       ("²", " squared"), ("½", "one half"), ("CO2", "C O 2"), ("H2O", "H 2 O"), ("...", ", "))


def speakable(t):
    for a, b in SAY:
        t = t.replace(a, b)
    return t


def mathspeak(t):
    for a, b in (("× ", "times "), ("÷ ", "divided by "), ("+ ", "plus "), ("− ", "minus "), ("= ?", ""),
                 ("²", " squared"), ("√", "the square root of "), ("%", " percent")):
        t = t.replace(a, b)
    return t.strip()


class Pack:
    def __init__(self, path):
        self.p = json.load(open(path))
        self.slug = self.p["slug"]
        self.nq = sum(len(lv) for lv in self.p["levels"])
        self.q = {}  # (li, qi) -> dict
        cyc = self.p.get("spoken_cycle")
        n = 0
        for li, lv in enumerate(self.p["levels"]):
            for qi, item in enumerate(lv):
                shown, opts, ans, why = item[:4]
                spoken = item[4] if len(item) > 4 else (cyc[n % len(cyc)] if cyc else
                                                        shown.replace("___", ", blank,").replace("\"", ""))
                if self.p.get("math") and len(item) <= 4:
                    spoken = mathspeak(shown) + "?"
                opts = shuffled(shown, opts, ans)
                key = f"{self.slug}|{li}|{qi}"
                Q[key] = ("text", shown, spoken, opts, ans, why)
                self.q[(li, qi)] = {"key": key, "shown": shown, "spoken": spoken, "opts": opts, "ans": ans,
                                    "why": why, "letter": LET[opts.index(ans)]}
                n += 1

    def spoken_with_options(self, d):
        if not self.p.get("read_options"):
            return d["spoken"]
        parts = [f"{LET[i]}, {o.rstrip('.')}" for i, o in enumerate(d["opts"])]
        return f"{d['spoken']} Is it {', '.join(parts[:-1])}, or {parts[-1]}?"


# ---------------------------------------------------------------- cards in the quiz design
def card(title, lines, vertical=False, highlight=None, sub=None, logo=False):
    W, Hh = (1080, 1920) if vertical else (1920, 1080)
    c = art.Canvas(W, Hh)
    c.rect(0, 0, W, Hh, H("#F1E8FF"))
    for k in range(22):
        r = (k * 71 + len(title) * 13) % 997
        c.circle((r * 7) % W, (r * 11) % Hh, 12 + r % 24, H("#8E5BD6", 22))
    hb = (40, 40, W - 40, 190) if vertical else (40, 30, W - 40, 150)
    c.rect(*hb, H("#2B2350"), r=50)
    quiz.brand_header(c, W, hb, vertical, title, 66)
    if logo and quiz.BRAND:
        if vertical:
            quiz.paste_logo(c, W / 2, 520, 600)
        else:
            quiz.paste_logo(c, 520, 610, 700)
    # level staircase
    if logo and quiz.BRAND:
        pass
    elif vertical:
        x0, y0, step, ph, base_w, grow = 140, 260, 125, 100, 520, 90
    else:
        x0, y0, step, ph, base_w, grow = 90, 230, 175, 140, 520, 90
    for li, (name, col) in enumerate(LEVELS if not (logo and quiz.BRAND) else []):
        y = y0 + li * step
        w = base_w + li * grow
        if vertical:
            x0 = (W - w) / 2
        faded = highlight is not None and li != highlight
        c.rect(x0 + 6, y + 8, x0 + w + 6, y + ph + 8, H("#000000", 25 if faded else 40), r=ph // 2)
        c.rect(x0, y, x0 + w, y + ph, H(col, 90 if faded else 255), r=ph // 2,
               outline=H("#FFFFFF") if li == highlight else None, width=8)
        c.text(x0 + w / 2, y + ph / 2, f"{li + 1} · {name}", art.font(54 if vertical else 60, "Bold"),
               H("#FFFFFF", 150 if faded else 255), anchor="mm")
        if li == highlight:
            tx = x0 - 20
            c.poly([(tx - 50, y + ph / 2 - 34), (tx - 50, y + ph / 2 + 34), (tx, y + ph / 2)], H("#2B2350"))
    # text card
    box = (90, 830, W - 90, 1760) if vertical else (1040, 230, 1840, 990)
    c.rect(box[0] + 6, box[1] + 10, box[2] + 6, box[3] + 10, H("#000000", 35), r=60)
    c.rect(*box, H("#FFFFFF"), r=60, outline=H("#8E5BD6"), width=8)
    maxw = box[2] - box[0] - 80
    sizes = [86] + [62] * (len(lines) - 1)
    while True:
        tot = sum(int(s * 1.45) for s in sizes)
        if tot <= box[3] - box[1] - 80 or sizes[0] < 40:
            break
        sizes = [int(s * 0.92) for s in sizes]
    y = (box[1] + box[3]) / 2 - tot / 2
    for i, (ln, s) in enumerate(zip(lines, sizes)):
        while s > 30 and art.font(s, "Bold").getlength(ln) > maxw:
            s -= 2
        col = H("#2B2350") if i == 0 else H("#4A4466")
        if ln.startswith("!"):
            ln, col = ln[1:], H("#E23B3B")
        y += int(s * 1.45) / 2
        c.text(W / 2 if vertical else (box[0] + box[2]) / 2, y, ln, art.font(s, "Bold"), col, anchor="mm")
        y += int(s * 1.45) / 2
    if sub:
        c.text(W / 2, Hh - 80 if vertical else Hh - 45, sub, art.font(48 if vertical else 40, "SemiBold"),
               H("#7A6A9A"), anchor="mm")
    return c.final().convert("RGB")


def thumbnail(pack, path):
    p = pack.p
    c = art.Canvas(1280, 720)
    c.rect(0, 0, 1280, 720, H("#F1E8FF"))
    for k in range(16):
        r = (k * 71 + 7) % 997
        c.circle((r * 7) % 1280, (r * 11) % 720, 10 + r % 20, H("#8E5BD6", 26))
    c.rect(30, 22, 1250, 170, H("#2B2350"), r=44)
    fs, tx, tw = 104, 640, 1150
    if quiz.BRAND:
        quiz.paste_logo(c, 112, 96, 176)
        tx, tw = 715, 1010
    while art.font(fs, "Bold").getlength(p["thumb"]["top"]) > tw:
        fs -= 4
    c.text(tx, 96, p["thumb"]["top"], art.font(fs, "Bold"), H("#FFE680"), anchor="mm")
    for li, (name, col) in enumerate(LEVELS):
        y = 205 + li * 124
        w = 330 + li * 62
        c.rect(36, y + 7, 36 + w + 4, y + 104 + 7, H("#000000", 40), r=52)
        c.rect(32, y, 32 + w, y + 104, H(col), r=52)
        c.text(32 + w / 2, y + 52, name, art.font(52 if li < 3 else 50, "Bold"), H("#FFFFFF"), anchor="mm")
    box = (660, 205, 1250, 700)
    c.rect(box[0] + 6, box[1] + 10, box[2] + 6, box[3] + 10, H("#000000", 40), r=50)
    c.rect(*box, H("#FFFFFF"), r=50, outline=H("#8E5BD6"), width=8)
    lines = p["thumb"]["card"]
    s = 74
    while s > 40 and (max(art.font(s, "Bold").getlength(ln) for ln in lines) > box[2] - box[0] - 70
                      or len(lines) * s * 1.3 > 300):
        s -= 2
    y = 400 - (len(lines) - 1) * s * 0.65
    for ln in lines:
        c.text((box[0] + box[2]) / 2, y, ln, art.font(s, "Bold"), H("#2B2350"), anchor="mm")
        y += s * 1.3
    c.rect(770, 600, 1140, 672, H("#FF7A30"), r=36)
    c.text(955, 636, f"{pack.nq} {p['noun'].upper()}", art.font(46, "Bold"), H("#FFFFFF"), anchor="mm")
    c.circle(1222, 232, 66, H("#E23B3B"), outline=H("#FFFFFF"), width=8)
    c.text(1222, 232, "?", art.font(96, "Bold"), H("#FFFFFF"), anchor="mm")
    c.final().convert("RGB").save(path, quality=92)


# ---------------------------------------------------------------- one question
def ask_question(tl, d, vertical, header, number, total, level, footer=None, spoken=None):
    key = d["key"]
    img = frame(key, "ask", None, vertical, header, number, total, footer, level=level)
    dur = tl.say(speakable(spoken or d["spoken"]))
    tl.show(img, dur + 0.4)
    for s in range(quiz.THINK, 0, -1):
        tl.add_sound(quiz.TICK, tl.t)
        tl.show(frame(key, "ask", s, vertical, header, number, total, footer, level=level), 1.0)
    tl.add_sound(quiz.DING, tl.t)
    dur = tl.say(speakable(f"The answer is {d['letter']}: {d['ans'].rstrip('.')}. {d['why']}"))
    tl.show(frame(key, "reveal", None, vertical, header, number, total, footer, level=level), dur + 0.9)


SETTINGS = ("SETTINGS:\n- Audience: No, it's not made for kids (quiz for teens and adults:"
            " this keeps comments ON for \"comment your score\")\n- Altered or synthetic content: Yes\n"
            "- Category: Education\n- Visibility: Public\n")


def write_kit(out_dir, name, meta, short):
    meta = dict(meta, tags=list(dict.fromkeys(meta["tags"])))
    extra = ("- Cover: in the YouTube app choose the FIRST frame (the question without the answer)\n"
             "- Related video: choose the full video (long video) so viewers can tap to it and find the answer\n" if short else
             f"- Thumbnail: {name}_thumb.jpg\n- Pinned comment: What's your score out of 32? 👇 "
             "I reply to everyone!\n")
    text = (f"=== {'YOUTUBE SHORT' if short else 'YOUTUBE VIDEO'}: {name}.mp4 ===\n\n"
            f"TITLE:\n{meta['title']}\n\nDESCRIPTION:\n{meta['description']}\n\n"
            f"TAGS (paste in the Tags box):\n{', '.join(meta['tags'])}\n\n{SETTINGS}{extra}")
    open(os.path.join(out_dir, name + ".txt"), "w").write(text)
    json.dump(meta, open(os.path.join(out_dir, name + "_meta.json"), "w"), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- long video
def build_long(pack, out_dir, voice):
    p, nq, slug = pack.p, pack.nq, pack.slug
    work = os.path.join(out_dir, "work_" + slug)
    os.makedirs(work, exist_ok=True)
    tl = Timeline(work, voice)
    noun = p["noun"]
    last = (3, len(p["levels"][3]) - 1)
    teaser = pack.q[last]
    # 1. open loop: the hardest question first, no answer
    img = frame(teaser["key"], "ask", None, False, "Can you answer this?", footer="The answer is at the end of the video!",
                level=pill(3))
    d = tl.say(f"{teaser['spoken']} Can you answer this? It's the hardest one in this video. "
               "Keep watching: the answer is at the end!")
    tl.show(img, d + 0.6)
    # 2. intro
    intro = card(f"{p['name']}: Easy to Impossible", [f"{nq} {noun}", "4 levels", "5 seconds each",
                                                       "Keep your score!"], logo=True)
    for text in (f"Welcome to {CHANNEL}! This is the {p['name']}, from easy to impossible!",
                 f"{nq} {noun} in four levels: easy, medium, hard, and impossible. "
                 "You have five seconds for each one. Take a paper and keep your score!",
                 "At the end, share your score in the comments. Ready? Let's go!"):
        d = tl.say(text)
        tl.show(intro, d + 0.3)
    level_say = ["Level one: easy. Let's warm up!", "Level two: medium. Still easy?",
                 "Level three: hard. This is where it gets tricky!",
                 "Level four: impossible! Only real experts get these. Good luck!"]
    level_line = ["Warm up!", "Still easy?", "It gets tricky...", "!Only experts get these!"]
    footers = ["Level 1 · Easy: keep your score!", "Level 2 · Medium: how many do you have so far?",
               "Level 3 · Hard: don't stop now!", "Level 4 · Impossible: the question from the start is coming!"]
    check_say = ["Level one complete! Write down your score.",
                 "Level two complete! You're halfway there. Don't stop now!",
                 "Level three complete! Now the impossible level, with the question from the start of the video!"]
    num = 0
    for li, lv in enumerate(p["levels"]):
        d = tl.say(level_say[li])
        tl.show(card(f"Level {li + 1}: {WORDS[li]}", [f"{len(lv)} {noun}", level_line[li]], highlight=li),
                d + 0.7)
        for qi in range(len(lv)):
            num += 1
            q = pack.q[(li, qi)]
            sp = f"Number {num}. " + pack.spoken_with_options(q)
            if (li, qi) == last:
                sp = "And now, the last one. It's the question from the start of the video! " + sp
            ask_question(tl, q, False, p["header"], num, nq, pill(li), footers[li], sp)
        if li < 3:
            done = sum(len(x) for x in p["levels"][:li + 1])
            d = tl.say(check_say[li])
            tl.show(card(f"Level {li + 1} complete!", ["Your score so far:", f"? / {done}", "Write it down!"],
                         highlight=li), d + 0.8)
            if li == 1:  # halfway: like & subscribe
                cta = card(f"Enjoying {CHANNEL}?", ["Like & subscribe!", "It helps us make", "more quizzes",
                                                    "!Then: level 3..."], logo=True)
                d = tl.say(f"If you like it until now, hit like and subscribe to {CHANNEL}! "
                           "It really helps us make more quizzes. Now, let's go to level three!")
                tl.show(cta, d + 0.6)
    hi, mid = round(nq * 0.8), round(nq * 0.55)
    res = card("Your score?", [f"{nq}/{nq}: Genius!", f"{hi}–{nq - 1}: Excellent", f"{mid}–{hi - 1}: Good",
                               f"0–{mid - 1}: Keep practising", "!Comment your score!"])
    for text in (f"Finished! What's your score? {nq} out of {nq} means you are a genius! "
                 f"{hi} or more is excellent, and {mid} or more is good.",
                 "Share your score with us in the comments! We read every comment."):
        d = tl.say(text)
        tl.show(res, d + 0.8)
    end = card("Thank you!", [f"Subscribe to {CHANNEL}", "& hit like!", "A new quiz every week",
                              "!Easy to Impossible"], logo=True)
    d = tl.say(f"If you enjoyed this quiz, hit like and subscribe to {CHANNEL}. "
               "There's a new easy to impossible quiz every week. See you next time!")
    tl.show(end, d + 1.2)
    out = os.path.join(out_dir, slug + ".mp4")
    tl.render(out, music_vol=0.06)
    thumbnail(pack, os.path.join(out_dir, slug + "_thumb.jpg"))
    desc = (f"{p['about']} 🧠\n"
            f"4 levels: 🟢 Easy · 🟡 Medium · 🟠 Hard · 🔴 Impossible\n"
            f"{nq} {noun}, 5 seconds each. Keep your score!\n"
            "👀 The hardest question is at the start... and the answer is at the end!\n\n"
            f"💬 Share your score in the comments! Example: {hi + 1}/{nq} 🎉\n"
            "🔔 Subscribe to QuizNado 🌪️ for a new Easy to Impossible test every 3 days!\n\n"
            f"🇲🇦 {p['ar']}\n🇫🇷 {p['fr']}\n\n{p['hashtags']} #EasyToImpossible #QuizNado")
    write_kit(out_dir, slug, {"title": p["title"], "description": desc, "tags": ["QuizNado"] + p["tags"]}, False)
    print(f"done: {out} ({tl.t / 60:.1f} min)", flush=True)


# ---------------------------------------------------------------- teaser Short (the only Short)
def teaser_end(thumb_path, video_name, more_lines=None):
    """Vertical end card: the long video's thumbnail + 'Want the answer? Watch the full video' + subscribe & like."""
    img = card("Want the answer?", ["Watch the full video", f"\"{video_name}\"", "on our channel!",
                                     "!Subscribe & like!"] + (more_lines or []), vertical=True)
    c = Image.new("RGBA", img.size); c.paste(img)
    th = Image.open(thumb_path).convert("RGB"); tw = 960
    th = th.resize((tw, int(tw * th.height / th.width)), Image.LANCZOS)
    x, y = 60, 225
    shadow = Image.new("RGBA", (tw + 20, th.height + 20), (0, 0, 0, 70)); c.alpha_composite(shadow, (x - 4, y + 6))
    frame_ = Image.new("RGBA", (tw + 16, th.height + 16), (255, 255, 255, 255)); c.alpha_composite(frame_, (x - 8, y - 8))
    c.paste(th, (x, y))
    from PIL import ImageDraw
    d = ImageDraw.Draw(c); cx, cy, r = x + tw - 80, y + th.height - 70, 52
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(226, 59, 59)); d.polygon([(cx - 16, cy - 27), (cx - 16, cy + 27), (cx + 29, cy)], fill="white")
    return c.convert("RGB")


def build_teaser(pack, out_dir, voice):
    p, nq, slug = pack.p, pack.nq, pack.slug
    t = p.get("teaser") or {"picks": [p["shorts"][0]["picks"][2], p["shorts"][0]["picks"][3]],
                            "title": p["shorts"][0]["title"]}
    last = (3, len(p["levels"][3]) - 1)
    picks = [tuple(x) for x in t["picks"]][:2] + [last]
    name = f"{slug}_short"
    thumb = os.path.join(out_dir, slug + "_thumb.jpg")
    if not os.path.exists(thumb):
        thumbnail(pack, thumb)
    work = os.path.join(out_dir, "work_" + name)
    os.makedirs(work, exist_ok=True)
    tl = Timeline(work, voice)
    qs = [pack.q[k] for k in picks]
    hook = frame(qs[0]["key"], "ask", None, True, "3 HARD questions", level=pill(picks[0][0]),
                 note="Only 1% get the last one!")
    d = tl.say("Three hard questions. Only one percent get the last one!")
    tl.show(hook, d + 0.3)
    for i, (q, (li, _)) in enumerate(zip(qs[:2], picks[:2]), 1):
        ask_question(tl, q, True, p["header"], i, 3, pill(li), None, f"Number {i}. " + q["spoken"])
    # the impossible one: countdown, NO answer
    q = qs[2]; key = q["key"]; foot = "The answer is in the full video!"
    d = tl.say("Number 3, the impossible one! " + q["spoken"])
    tl.show(frame(key, "ask", None, True, p["header"], 3, 3, foot, level=pill(3)), d + 0.4)
    for s_ in range(quiz.THINK, 0, -1):
        tl.add_sound(quiz.TICK, tl.t)
        tl.show(frame(key, "ask", s_, True, p["header"], 3, 3, foot, level=pill(3)), 1.0)
    vname = p["title"].split(" |")[0].split(":")[0]
    d = tl.say(f"Want the answer? It's in the full video, {vname}, on our channel. Subscribe and like!")
    tl.show(teaser_end(thumb, vname), d + 1.2)
    out = os.path.join(out_dir, name + ".mp4")
    tl.render(out, music_vol=0.07, vertical=True)
    desc = (f"{p['header']}: 3 hard questions! 🧠 Only 1% get the last one...\n"
            f"👉 The answer to number 3 is in the full video \"{p['title'].split(' |')[0]}\" on our channel!\n"
            "💬 Comment your answer first, then go check it!\n"
            "👍 Like & subscribe to QuizNado 🌪️ for new challenges every week!\n\n"
            f"🇲🇦 {p['ar']}\n🇫🇷 {p['fr']}\n\n#shorts {p['hashtags']} #QuizNado")
    write_kit(out_dir, name, {"title": t["title"], "description": desc, "tags": ["QuizNado"] + p["tags"]}, True)
    print(f"short: {out} ({tl.t:.0f} s)", flush=True)


# ---------------------------------------------------------------- old 2-Short format (not used any more)
def build_short(pack, out_dir, voice, si):
    p, nq = pack.p, pack.nq
    s = p["shorts"][si]
    name = f"{pack.slug}_short{si + 1}"
    work = os.path.join(out_dir, "work_" + name)
    os.makedirs(work, exist_ok=True)
    tl = Timeline(work, voice)
    picks = [pack.q[tuple(x)] for x in s["picks"]]
    # hook = cover frame: first question, no answer
    hook = frame(picks[0]["key"], "ask", None, True, "Can you get 4/4?", level=pill(s["picks"][0][0]),
                 note="The last one is IMPOSSIBLE!")
    d = tl.say("Four questions, from easy to impossible. Can you get all four?")
    tl.show(hook, d + 0.3)
    for i, (q, (li, _)) in enumerate(zip(picks, s["picks"]), 1):
        sp = f"{WORDS[li]}! {q['spoken']}"
        ask_question(tl, q, True, p["header"], i, len(picks), pill(li), None, sp)
        if i == 2:
            d = tl.say("Got it right? Hit like!")
            tl.show(frame(q["key"], "reveal", None, True, p["header"], i, len(picks), level=pill(li),
                          note="Got it right? Hit LIKE!"), d + 0.2)
    end = card("Score?", ["Comment your score!", f"Full test: {nq} {p['noun']}", "on our channel!",
                          f"!Subscribe to {CHANNEL}!"], vertical=True, logo=True)
    d = tl.say(f"How many did you get? Comment your score! The full test, with {nq} {p['noun']}, is on our channel. "
               f"Subscribe to {CHANNEL} for more!")
    tl.show(end, d + 1.0)
    out = os.path.join(out_dir, name + ".mp4")
    tl.render(out, music_vol=0.07, vertical=True)
    desc = (f"{p['header']}: 4 questions, from easy to impossible! 🧠\n"
            "💬 Comment your score: 1/4, 2/4, 3/4 or 4/4?\n"
            f"🎬 Want the full test? \"{p['title'].split(' |')[0]}\" ({nq} {p['noun']}) is on our channel!\n"
            "👍 Liked it? Like & subscribe to QuizNado 🌪️ for a new test every 3 days!\n\n"
            f"🇲🇦 {p['ar']}\n🇫🇷 {p['fr']}\n\n#shorts {p['hashtags']} #QuizNado")
    write_kit(out_dir, name, {"title": s["title"], "description": desc, "tags": ["QuizNado"] + p["tags"]}, True)
    print(f"short: {out} ({tl.t:.0f} s)", flush=True)


if __name__ == "__main__":
    pack = Pack(sys.argv[1])
    out_dir = sys.argv[2]
    what = sys.argv[3] if len(sys.argv) > 3 else "all"
    os.makedirs(out_dir, exist_ok=True)
    if what == "preview":
        q0, ql = pack.q[(0, 0)], pack.q[(3, 7)]
        frame(q0["key"], "ask", None, True, "Can you get 4/4?", level=pill(0),
              note="The last one is IMPOSSIBLE!").save(os.path.join(out_dir, f"{pack.slug}_pv_hook.png"))
        frame(ql["key"], "reveal", None, True, pack.p["header"], 4, 4, level=pill(3)).save(
            os.path.join(out_dir, f"{pack.slug}_pv_reveal.png"))
        frame(ql["key"], "ask", 3, False, pack.p["header"], 32, 32, "Level 4 · Impossible: the question from the "
              "start is coming!", level=pill(3)).save(os.path.join(out_dir, f"{pack.slug}_pv_long.png"))
        card("Level 3: Hard", ["8 questions", "It gets tricky..."], highlight=2).save(
            os.path.join(out_dir, f"{pack.slug}_pv_card.png"))
        card("Score?", ["Comment your score!", "Want the full test?", "32 words", "on our channel!",
                        "!Like & subscribe!"], vertical=True).save(os.path.join(out_dir, f"{pack.slug}_pv_end.png"))
        thumbnail(pack, os.path.join(out_dir, f"{pack.slug}_thumb.jpg"))
        teaser_end(os.path.join(out_dir, f"{pack.slug}_thumb.jpg"), pack.p["title"].split(" |")[0].split(":")[0]).save(
            os.path.join(out_dir, f"{pack.slug}_pv_teaser_end.png"))
        sys.exit()
    tts = os.environ.get("MT_TTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts"))
    v = build.Voice(tts)
    if what in ("long", "all"):
        build_long(pack, out_dir, v)
    if what in ("short", "shorts", "all"):
        build_teaser(pack, out_dir, v)

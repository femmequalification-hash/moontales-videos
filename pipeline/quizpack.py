""""Easy to Impossible" quiz packs in the channel's purple quiz design.

One pack (quizpacks/<slug>.json) = 1 long video (32 questions, 4 levels) + 2 vertical Shorts
(4 questions each, one per level). Every Short ends by sending viewers to the full test.

Usage:  python3 quizpack.py quizpacks/<slug>.json OUT_DIR [long|shorts|all|preview]

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
def card(title, lines, vertical=False, highlight=None, sub=None):
    W, Hh = (1080, 1920) if vertical else (1920, 1080)
    c = art.Canvas(W, Hh)
    c.rect(0, 0, W, Hh, H("#F1E8FF"))
    for k in range(22):
        r = (k * 71 + len(title) * 13) % 997
        c.circle((r * 7) % W, (r * 11) % Hh, 12 + r % 24, H("#8E5BD6", 22))
    hb = (40, 40, W - 40, 190) if vertical else (40, 30, W - 40, 150)
    c.rect(*hb, H("#2B2350"), r=50)
    fs = 66
    while fs > 40 and art.font(fs, "Bold").getlength(title) > hb[2] - hb[0] - 60:
        fs -= 2
    c.text(W / 2, (hb[1] + hb[3]) / 2, title, art.font(fs, "Bold"), H("#FFE680"), anchor="mm")
    # level staircase
    if vertical:
        x0, y0, step, ph, base_w, grow = 140, 260, 125, 100, 520, 90
    else:
        x0, y0, step, ph, base_w, grow = 90, 230, 175, 140, 520, 90
    for li, (name, col) in enumerate(LEVELS):
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
    fs = 104
    while art.font(fs, "Bold").getlength(p["thumb"]["top"]) > 1150:
        fs -= 4
    c.text(640, 96, p["thumb"]["top"], art.font(fs, "Bold"), H("#FFE680"), anchor="mm")
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
    dur = tl.say(spoken or d["spoken"])
    tl.show(img, dur + 0.4)
    for s in range(quiz.THINK, 0, -1):
        tl.add_sound(quiz.TICK, tl.t)
        tl.show(frame(key, "ask", s, vertical, header, number, total, footer, level=level), 1.0)
    tl.add_sound(quiz.DING, tl.t)
    dur = tl.say(f"The answer is {d['letter']}: {d['ans'].rstrip('.')}. {d['why']}")
    tl.show(frame(key, "reveal", None, vertical, header, number, total, footer, level=level), dur + 0.9)


SETTINGS = ("SETTINGS:\n- Audience: No, it's not made for kids (English test for teens and adults:"
            " this keeps comments ON for \"comment your score\")\n- Altered or synthetic content: Yes\n"
            "- Category: Education\n- Visibility: Public\n")


def write_kit(out_dir, name, meta, short):
    extra = ("- Cover: in the YouTube app choose the FIRST frame (the question without the answer)\n"
             "- Related video: choose the full test (long video) so viewers can tap to it\n" if short else
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
                                                       "Keep your score!"])
    for text in (f"Welcome to the {p['name']}, from easy to impossible!",
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
    hi, mid = round(nq * 0.8), round(nq * 0.55)
    res = card("Your score?", [f"{nq}/{nq}: Genius!", f"{hi}–{nq - 1}: Excellent", f"{mid}–{hi - 1}: Good",
                               f"0–{mid - 1}: Keep practising", "!Comment your score!"])
    for text in (f"Finished! What's your score? {nq} out of {nq} means you are a genius! "
                 f"{hi} or more is excellent, and {mid} or more is good.",
                 "Share your score with us in the comments! We read every comment."):
        d = tl.say(text)
        tl.show(res, d + 0.8)
    end = card("Thank you!", ["Like & subscribe", "A new test every week!", "More Easy to Impossible",
                              "tests on our channel"])
    d = tl.say("If you enjoyed this test, like and subscribe. There's a new easy to impossible test every week. "
               "See you next time!")
    tl.show(end, d + 1.2)
    out = os.path.join(out_dir, slug + ".mp4")
    tl.render(out, music_vol=0.06)
    thumbnail(pack, os.path.join(out_dir, slug + "_thumb.jpg"))
    desc = (f"{p['about']} 🧠\n"
            f"4 levels: 🟢 Easy · 🟡 Medium · 🟠 Hard · 🔴 Impossible\n"
            f"{nq} {noun}, 5 seconds each. Keep your score!\n"
            "👀 The hardest question is at the start... and the answer is at the end!\n\n"
            f"💬 Share your score in the comments! Example: {hi + 1}/{nq} 🎉\n"
            "🔔 Subscribe to QuizNado 🌪️ for a new Easy to Impossible test every week!\n\n"
            f"🇲🇦 {p['ar']}\n🇫🇷 {p['fr']}\n\n{p['hashtags']} #EasyToImpossible #QuizNado")
    write_kit(out_dir, slug, {"title": p["title"], "description": desc, "tags": ["QuizNado"] + p["tags"]}, False)
    print(f"done: {out} ({tl.t / 60:.1f} min)", flush=True)


# ---------------------------------------------------------------- shorts
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
    end = card("Score?", ["Comment your score!", "Want the full test?", f"{nq} {p['noun']}", "on our channel!",
                          "!Like & subscribe!"], vertical=True)
    d = tl.say(f"How many did you get? Comment your score! The full test, with {nq} {p['noun']}, is on our channel. "
               "Like and subscribe!")
    tl.show(end, d + 1.0)
    out = os.path.join(out_dir, name + ".mp4")
    tl.render(out, music_vol=0.07, vertical=True)
    desc = (f"{p['header']}: 4 questions, from easy to impossible! 🧠\n"
            "💬 Comment your score: 1/4, 2/4, 3/4 or 4/4?\n"
            f"🎬 Want the full test? \"{p['title'].split(' |')[0]}\" ({nq} {p['noun']}) is on our channel!\n"
            "👍 Liked it? Like & subscribe to QuizNado 🌪️ for a new test every week!\n\n"
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
        sys.exit()
    tts = os.environ.get("MT_TTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts"))
    v = build.Voice(tts)
    if what in ("shorts", "all"):
        for i in range(len(pack.p["shorts"])):
            build_short(pack, out_dir, v, i)
    if what in ("long", "all"):
        build_long(pack, out_dir, v)

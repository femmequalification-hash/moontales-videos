"""'20 tricky grammar questions' long video, clean white worksheet style (16:9).

Usage: python3 grammar20.py OUT_DIR  -> grammar-20.mp4 (+ _thumb.jpg, _meta.json)
Each question: question + options read aloud, 10-second countdown, green tick on the
answer and a short explanation. Question 19 is announced as the trickiest.
"""
import json
import os
import random
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art  # noqa: E402
import build  # noqa: E402
import quiz  # noqa: E402
from worksheet import serif, slen, stext, tick, wrap  # noqa: E402

H = art.hexc
W, HH = 1920, 1080
THINK = 10
LET = "ABC"

QS = [
    ("The children ___ playing in the garden.", ["is", "are", "was"], "are", "Children is plural, so we say: the children are."),
    ("The news ___ good today.", ["is", "are", "were"], "is", "News is uncountable and singular: the news is."),
    ("She speaks English very ___.", ["good", "well", "best"], "well", "Well is an adverb. Good is an adjective."),
    ("I don't have ___ money.", ["some", "any", "no"], "any", "In negative sentences, use any."),
    ("I ___ here since Monday.", ["am", "was", "have been"], "have been", "With since, use the present perfect: I have been."),
    ("He is the ___ person I know.", ["most kind", "kindest", "kinder"], "kindest", "Short adjectives: kind, kinder, the kindest."),
    ("Everyone ___ their own opinion.", ["have", "has", "having"], "has", "Everyone is singular: everyone has."),
    ("Each of the boys ___ a bike.", ["have", "has", "are having"], "has", "Each is singular: each of the boys has."),
    ("This is the woman ___ car was stolen.", ["who", "whose", "whom"], "whose", "Whose shows possession: the woman whose car..."),
    ("There is very ___ milk left.", ["few", "little", "many"], "little", "Milk is uncountable: little milk, but few apples."),
    ("If I had studied, I ___ the exam.", ["would pass", "would have passed", "will pass"], "would have passed",
     "Third conditional: if + had + past participle, would have + past participle."),
    ("I wish you ___ here with me.", ["are", "were", "will be"], "were", "After wish, use were for things that are not true now."),
    ("My mother made me ___ the dishes.", ["wash", "to wash", "washing"], "wash", "Make someone do something: no to after make."),
    ("Could you tell me where ___?", ["is the station", "the station is", "does the station"], "the station is",
     "Indirect questions use normal word order: where the station is."),
    ("When we arrived, the film ___.", ["has started", "had already started", "starts"], "had already started",
     "Past perfect: the film started before we arrived."),
    ("Keep this a secret between you and ___.", ["I", "me", "myself"], "me", "After a preposition, use me: between you and me."),
    ("To ___ should I send this letter?", ["who", "whom", "whose"], "whom", "After a preposition like to, use whom."),
    ("Neither the teacher nor the students ___ ready.", ["was", "were", "is"], "were",
     "With neither... nor, the verb agrees with the nearer subject: the students were."),
    ("Which sentence is correct?", ["Me and him went home.", "Him and I went home.", "He and I went home."],
     "He and I went home.", "Use subject pronouns before the verb: he and I went home."),
    ("I'm tired. I need to ___ down.", ["lay", "lie", "laid"], "lie", "Lie down means to rest. Lay means to put something down."),
]

_paper = None


def paper():
    global _paper
    if _paper is None:
        rng = np.random.default_rng(5)
        base = np.ones((HH, W, 3), dtype=np.float32) * np.array([250, 248, 242], dtype=np.float32)
        noise = np.kron(rng.normal(0, 4, (HH // 2, W // 2, 1)).astype(np.float32), np.ones((2, 2, 1), np.float32))
        im = Image.fromarray(np.clip(base + noise, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
        _paper = im.convert("RGBA")
    return _paper.copy()


def marker(c, x0, x1, y, seed, progress=1.0):
    r = random.Random(seed)
    xe = x0 + (x1 - x0) * progress
    pts, x = [], x0
    while x < xe:
        pts.append((x, y + r.uniform(-3, 3)))
        x += 50
    pts.append((xe, y))
    if len(pts) > 1:
        c.line(pts, H("#E8312F", 235), 14)


def header(c, right_text=None, footer=None):
    c.rect(60, 40, 700, 160, H("#FFFFFF"), r=60, outline=H("#1C1C24"), width=7)
    f = art.font(84, "Bold")
    wa = f.getlength("Grammar ")
    x = 380 - (wa + f.getlength("Test")) / 2
    c.text(x, 100, "Grammar ", f, H("#E8312F"), anchor="lm")
    c.text(x + wa, 100, "Test", f, H("#1F5FD6"), anchor="lm")
    if right_text:
        c.rect(1440, 55, 1860, 145, H("#1C1C24"), r=45)
        c.text(1650, 100, right_text, art.font(56, "Bold"), H("#FFE680"), anchor="mm")
    if footer:
        c.text(1070, 100, footer, art.font(38, "Bold"), H("#E8312F"), anchor="mm")


def frame(qi, state="ask", timer=None, underline=1.0, footer=None):
    q, opts, ans, why = QS[qi]
    c = art.Canvas(W, HH)
    c.paste(paper(), 0, 0)
    header(c, f"Question {qi + 1}/20", footer)
    lines = wrap(q, 74, 1450)
    for li, ln in enumerate(lines):
        y = 230 + li * 95
        stext(c, 110, y, ln, 74, H("#141420"))
        marker(c, 105, 115 + slen(ln, 74), y + 92, seed=qi * 3 + li, progress=underline)
    oy = 230 + len(lines) * 95 + 70
    for oi, opt in enumerate(opts):
        y = oy + oi * 150
        right = state == "reveal" and opt == ans
        c.rect(150, y, 250, y + 100, H("#FFFFFF"), r=14, outline=H("#1C1C24"), width=7)
        size = 70
        while slen(f"{LET[oi]})  {opt}", size) > 1150 and size > 44:
            size -= 2
        col = H("#1FA34A") if right else (H("#141420") if state == "ask" else H("#141420", 150))
        stext(c, 290, y + 50, f"{LET[oi]})  {opt}", size, col, anchor="lm")
        if right:
            tick(c, 200, y + 44, 1.5)
    if timer is not None:
        tx, ty, tr = 1700, 640, 120
        c.circle(tx, ty, tr + 12, H("#1C1C24"))
        c.circle(tx, ty, tr, H("#FFFFFF"))
        c.pie(tx, ty, tr, tr, -90, -90 + 360 * timer / THINK, H("#E8312F"))
        c.circle(tx, ty, tr - 22, H("#FFFFFF"))
        c.text(tx, ty, str(timer), art.font(120, "Bold"), H("#1C1C24"), anchor="mm")
    if state == "reveal":
        c.rect(110, 945, 1810, 1050, H("#E6F6EA"), r=30, outline=H("#1FA34A"), width=5)
        f = art.font(44, "SemiBold")
        size = 44
        while f.getlength(why) > 1560 and size > 30:
            size -= 2
            f = art.font(size, "SemiBold")
        tick(c, 170, 995, 0.8)
        c.text(230, 997, why, f, H("#14743A"), anchor="lm")
    return c.final().convert("RGB")


def card(lines, big=None):
    c = art.Canvas(W, HH)
    c.paste(paper(), 0, 0)
    header(c)
    y = 330
    if big:
        c.text(W / 2, y, big, art.font(110, "Bold"), H("#1F5FD6"), anchor="mm")
        marker(c, W / 2 - art.font(110, "Bold").getlength(big) / 2, W / 2 + art.font(110, "Bold").getlength(big) / 2,
               y + 70, seed=99)
        y += 190
    for txt, col in lines:
        c.text(W / 2, y, txt, art.font(64, "Bold"), H(col), anchor="mm")
        y += 105
    return c.final().convert("RGB")


def main(out_dir):
    slug = "grammar-20"
    work = os.path.join(out_dir, "work_" + slug)
    os.makedirs(work, exist_ok=True)
    tts = os.environ.get("MT_TTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts"))
    tl = quiz.Timeline(work, build.Voice(tts))
    intro = card([("20 tricky grammar questions", "#141420"), ("10 seconds for each question", "#141420"),
                  ("Keep your score and share it in the comments!", "#E8312F")], "Can you score 100%?")
    for text in ("Think you have perfect English grammar? Let's find out!",
                 "Here are twenty tricky grammar questions. You have ten seconds for each one.",
                 "Keep your score, and share it in the comments at the end. "
                 "And watch out for question nineteen: it's the trickiest one! Let's start."):
        d = tl.say(text)
        tl.show(intro, d + 0.3)
    for qi, (q, opts, ans, why) in enumerate(QS):
        footer = {9: "Halfway! Keep your score", 17: "Question 19 is the trickiest...",
                  18: "The trickiest question!", 19: "Last question!"}.get(qi)
        if qi == 18:
            d = tl.say("Question nineteen. This is the trickiest one. Most people get it wrong!")
            tl.show(frame(qi, underline=0.0, footer=footer), d + 0.2)
        spoken = q.replace("___", ", blank,")
        opts_spoken = ", ".join(f"{LET[i]}, {o}" for i, o in enumerate(opts))
        d = tl.say(f"Number {qi + 1}. {spoken} Is it {opts_spoken}?")
        steps = 4
        for k in range(1, steps + 1):
            tl.show(frame(qi, underline=k / steps, footer=footer), 0.2)
        tl.show(frame(qi, footer=footer), max(0.3, d - 0.8) + 0.3)
        for s in range(THINK, 0, -1):
            tl.add_sound(quiz.TICK * 0.7, tl.t)
            tl.show(frame(qi, timer=s, footer=footer), 1.0)
        tl.add_sound(quiz.DING, tl.t)
        letter = LET[opts.index(ans)]
        d = tl.say(f"The answer is {letter}: {ans}. {why}")
        tl.show(frame(qi, "reveal", footer=footer), d + 1.2)
    res = card([("20/20: Grammar expert!", "#1FA34A"), ("15–19: Very good", "#1F5FD6"),
                ("10–14: Good, keep practising", "#141420"), ("Share your score in the comments!", "#E8312F")],
               "What's your score?")
    for text in ("That's it! What's your score? Twenty out of twenty means you are a grammar expert!",
                 "Share your score in the comments, and tell us: did question nineteen get you?"):
        d = tl.say(text)
        tl.show(res, d + 0.6)
    end = card([("If you enjoyed it, like and subscribe!", "#141420"),
                ("A new English test every week", "#1F5FD6"), ("More tests on our channel", "#E8312F")],
               "Thank you for watching!")
    d = tl.say("If you enjoyed this test, like and subscribe. There's a new English test every week. "
               "You'll find more tests on our channel. Thanks for watching!")
    tl.show(end, d + 1.2)
    out = os.path.join(out_dir, slug + ".mp4")
    tl.render(out, music_vol=0.05)
    # thumbnail
    c = art.Canvas(1280, 720)
    c.paste(paper().resize((1280, 720)), 0, 0)
    c.text(640, 95, "20 TRICKY", art.font(110, "Bold"), H("#E8312F"), anchor="mm")
    c.text(640, 205, "GRAMMAR QUESTIONS", art.font(84, "Bold"), H("#1C1C24"), anchor="mm")
    marker(c, 250, 1030, 255, seed=7)
    for k, (txt, ok) in enumerate((("Me and him went home.", False), ("He and I went home.", True))):
        y = 360 + k * 120
        c.rect(150, y - 45, 240, y + 45, H("#FFFFFF"), r=12, outline=H("#1C1C24"), width=6)
        stext(c, 280, y, txt, 60, H("#1FA34A") if ok else H("#141420"), anchor="lm")
        if ok:
            tick(c, 195, y - 4, 1.3)
        else:
            c.line([(170, y - 25), (220, y + 25)], H("#E8312F"), 12)
            c.line([(170, y + 25), (220, y - 25)], H("#E8312F"), 12)
    c.rect(290, 590, 990, 690, H("#1F5FD6"), r=40)
    c.text(640, 640, "Can you score 100%?", art.font(60, "Bold"), H("#FFFFFF"), anchor="mm")
    c.final().convert("RGB").save(os.path.join(out_dir, slug + "_thumb.jpg"), quality=92)
    meta = {
        "title": "20 Tricky English Grammar Questions 🧠 Can You Score 100%?",
        "description": (
            "Think you have perfect English grammar? Take this test and prove it! 🧠\n"
            "20 tricky grammar questions, 10 seconds each, with a clear explanation after every answer.\n\n"
            "✅ Subject-verb agreement, tenses, conditionals, pronouns, who/whom, lie/lay and more.\n"
            "⚠️ Watch out for question 19: it's the trickiest one!\n\n"
            "💬 Share your score in the comments: how many did you get out of 20?\n"
            "👍 If you enjoyed it, like and subscribe for a new English test every week! 🔔\n\n"
            "🇲🇦 اختبر قواعد اللغة الإنجليزية: 20 سؤالاً صعباً — شارك نتيجتك في التعليقات!\n"
            "🇫🇷 Teste ta grammaire anglaise : 20 questions pièges — partage ton score en commentaire !\n\n"
            "Thanks for watching 🙏\n\n#EnglishGrammar #GrammarTest #EnglishQuiz #LearnEnglish"),
        "tags": ["english grammar test", "grammar quiz", "tricky grammar questions", "english test", "english quiz",
                 "can you score 100", "grammar challenge", "learn english", "ielts grammar", "toefl grammar",
                 "اختبار قواعد اللغة الانجليزية", "قواعد الانجليزية", "تعلم الانجليزية",
                 "test de grammaire anglaise", "quiz anglais", "grammaire anglaise"],
    }
    json.dump(meta, open(os.path.join(out_dir, slug + "_meta.json"), "w"), ensure_ascii=False, indent=2)
    print(f"done: {out} ({tl.t / 60:.1f} min)")


if __name__ == "__main__":
    out_dir = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] == "preview":
        os.makedirs(out_dir, exist_ok=True)
        g = Image.new("RGB", (1920, 1080))
        ims = [frame(13, timer=7), frame(17, "reveal", footer="Question 19 is the trickiest..."),
               card([("20 tricky grammar questions", "#141420"), ("Share your score!", "#E8312F")], "Can you score 100%?")]
        for k, im in enumerate(ims):
            g.paste(im.resize((960, 540)), ((k % 2) * 960, (k // 2) * 540))
        g.save(os.path.join(out_dir, "g20.png"))
        sys.exit()
    main(out_dir)

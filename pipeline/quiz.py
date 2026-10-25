"""English quiz videos for kids: a long "Big English Quiz" and 4 vertical Shorts.

Usage:  python3 quiz.py OUT_DIR long      -> OUT_DIR/big-quiz.mp4 (+ _thumb.jpg, _meta.json)
        python3 quiz.py OUT_DIR shorts    -> OUT_DIR/quiz-short1..4.mp4 (+ _meta.json)
        python3 quiz.py OUT_DIR adult     -> OUT_DIR/english-test1..2.mp4 (spelling / grammar, for adults)
        python3 quiz.py OUT_DIR adult2    -> OUT_DIR/english-test3..4.mp4 (confusing words / idioms)
        python3 quiz.py OUT_DIR adultlong -> OUT_DIR/english-level-test.mp4 (30 questions, 5 levels, adults)

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
# adult text questions: (display question, spoken question, options, answer, explanation)
Q.update({
    "ad_receive": ("text", "Which word is spelled correctly?", "Which word is spelled correctly?",
                   ["Recieve", "Receive", "Receeve"], "Receive", "Remember: i before e, except after c!"),
    "ad_definitely": ("text", "Which word is spelled correctly?", "And this one?",
                      ["Definately", "Definitly", "Definitely"], "Definitely", "There is no A in definitely!"),
    "ad_accommodate": ("text", "Which word is spelled correctly?", "The hardest one!",
                       ["Accomodate", "Accommodate", "Acommodate"], "Accommodate", "Double C and double M!"),
    "ad_were": ("text", "If I ___ you, I would study more.", "If I, blank, you, I would study more.",
                ["was", "were", "am"], "were", "After if I, use were for imaginary situations."),
    "ad_since": ("text", "I have lived here ___ 2019.", "I have lived here, blank, twenty nineteen.",
                 ["for", "since", "from"], "since", "Use since with a starting point in time."),
    "ad_fewer": ("text", "Which one is correct?", "Which one is correct?",
                 ["less people", "little people", "fewer people"], "fewer people",
                 "Use fewer with things you can count."),
})
Q.update({
    "ad_youre": ("text", "___ welcome!", "Blank, welcome!", ["Your", "You're", "Youre"], "You're",
                 "You're = you are. You are welcome!"),
    "ad_theyre": ("text", "___ going to the party tonight.", "Blank, going to the party tonight.",
                  ["Their", "There", "They're"], "They're", "They're = they are."),
    "ad_its": ("text", "The dog is wagging ___ tail.", "The dog is wagging, blank, tail.",
               ["it's", "its", "its'"], "its", "Its shows ownership. It's = it is."),
    "ad_cake": ("text", "\"It's a piece of cake\" means...", "It's a piece of cake means...",
                ["it's very easy", "it's delicious", "it's very small"], "it's very easy",
                "A piece of cake = something very easy."),
    "ad_weather": ("text", "\"I'm under the weather\" means...", "I'm under the weather means...",
                   ["I feel sick", "it's raining", "I'm outside"], "I feel sick",
                   "Under the weather = a little ill."),
    "ad_books": ("text", "\"Hit the books\" means...", "Hit the books means...",
                 ["to study hard", "to throw books", "to buy books"], "to study hard",
                 "Hit the books = start studying seriously."),
})
ADULT_SHORTS_2 = [
    ("Confusing words", ["ad_youre", "ad_theyre", "ad_its"],
     "Most people mix up these words, even native speakers! Can you get all three right?",
     ["Even native speakers", "mix these up!"], "WORD TEST",
     "Even Native Speakers Mix Up These Words 😱 English Test #shorts"),
    ("Idioms test", ["ad_cake", "ad_weather", "ad_books"],
     "Do you know these three English idioms? Let's see!",
     ["Do you know these", "3 English idioms?"], "IDIOM TEST",
     "Do You Know These 3 English Idioms? 🤔 English Test #shorts"),
]
ADULT_SHORTS = [
    ("Spelling test", ["ad_receive", "ad_definitely", "ad_accommodate"],
     "Only one in ten people can spell all three words. Let's test your English!",
     ["Only 1 in 10 people", "spell all 3 right!"], "SPELLING TEST",
     "Only 1 in 10 Can Spell These 3 Words 🤯 English Spelling Test #shorts"),
    ("Grammar test", ["ad_were", "ad_since", "ad_fewer"],
     "Most people get at least one of these wrong. Are you better? Let's see!",
     ["Most people get", "this wrong!"], "GRAMMAR TEST",
     "Most People Get This English Grammar Wrong 😳 Can You? #shorts"),
]

# adult level test: (question shown, options, answer, explanation)
LEVELS = [
    ("Level 1", "Beginner", [
        ("She ___ a teacher.", ["is", "are", "am"], "is", "Use is with he, she and it."),
        ("What is the opposite of hot?", ["warm", "cold", "wet"], "cold", "Hot and cold are opposites."),
        ("I ___ coffee every morning.", ["drink", "drinks", "drinking"], "drink", "With I, the verb has no -s."),
        ("What is the plural of child?", ["childs", "children", "childes"], "children", "Child is irregular: children."),
        ("There ___ two cats in the garden.", ["is", "are", "be"], "are", "Use there are with plural nouns."),
        ("What ___ your name?", ["is", "are", "do"], "is", "Name is singular, so we use is."),
    ]),
    ("Level 2", "Elementary", [
        ("Yesterday I ___ to the market.", ["go", "went", "gone"], "went", "Past simple of go is went."),
        ("He is ___ than me.", ["tall", "taller", "tallest"], "taller", "Use -er with than to compare two things."),
        ("I am good ___ math.", ["in", "on", "at"], "at", "We say good at something."),
        ("What is the past of buy?", ["buyed", "bought", "brought"], "bought", "Buy, bought. Brought is the past of bring!"),
        ("How ___ money do you have?", ["many", "much", "more"], "much", "Money is uncountable, so we use much."),
        ("She can ___ three languages.", ["speak", "speaks", "speaking"], "speak", "After can, use the base verb."),
    ]),
    ("Level 3", "Intermediate", [
        ("I have lived here ___ 2019.", ["for", "since", "from"], "since", "Since is used with a starting point in time."),
        ("If it rains, we ___ at home.", ["stay", "will stay", "would stay"], "will stay", "First conditional: if + present, will + verb."),
        ("I'm looking forward to ___ you.", ["see", "seeing", "saw"], "seeing", "Look forward to is followed by -ing."),
        ("She ___ TV when I called her.", ["watched", "was watching", "has watched"], "was watching", "Past continuous for an action in progress."),
        ("Which word means very tired?", ["exhausted", "excited", "exciting"], "exhausted", "Exhausted means extremely tired."),
        ("I ___ never been to London.", ["have", "has", "am"], "have", "Present perfect with I: I have been."),
    ]),
    ("Level 4", "Advanced", [
        ("If I ___ you, I would study more.", ["was", "were", "am"], "were", "In formal English: if I were you."),
        ("There are ___ people here than yesterday.", ["less", "fewer", "little"], "fewer", "Use fewer with things you can count."),
        ("By next June, I ___ my degree.", ["finish", "will have finished", "finished"], "will have finished", "Future perfect: finished before a future time."),
        ("Which word is spelled correctly?", ["Recieve", "Receive", "Receeve"], "Receive", "I before E, except after C!"),
        ("She is used to ___ up early.", ["wake", "waking", "woke"], "waking", "Be used to is followed by -ing."),
        ("To give up means to...", ["start", "stop trying", "give a gift"], "stop trying", "Give up means to stop trying or quit."),
    ]),
    ("Level 5", "Expert", [
        ("Which word is spelled correctly?", ["Accomodate", "Accommodate", "Acommodate"], "Accommodate", "Double C and double M!"),
        ("Hardly ___ arrived when it started to rain.", ["I had", "had I", "I have"], "had I", "After hardly at the start, the order is inverted."),
        ("It's high time we ___ home.", ["go", "went", "will go"], "went", "It's high time + past simple."),
        ("The weather can ___ your mood.", ["affect", "effect", "effects"], "affect", "Affect is the verb, effect is the noun."),
        ("Which word is spelled correctly?", ["Definately", "Definitely", "Definitly"], "Definitely", "There is no A in definitely!"),
        ("To break the ice means to...", ["start a conversation", "break something", "feel cold"], "start a conversation", "It means to make people feel relaxed and start talking."),
    ]),
]
for _li, (_ln, _lname, _qs) in enumerate(LEVELS, 1):
    for _qi, (_shown, _opts, _ans, _why) in enumerate(_qs, 1):
        Q[f"lv{_li}_{_qi}"] = ("text", _shown, _shown.replace("___", ", blank,"), _opts, _ans, _why)

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
    if t == "text":
        _, shown, spoken, opts, ans, why = q
        return (spoken, f"The answer is: {ans}! {why}", opts, opts.index(ans), [], {"text": shown, "why": why})
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
def frame(key, state, timer, vertical, header, number=None, total=None, footer=None, level=None, note=None):
    """state: 'ask' (no answer yet) or 'reveal'. timer: seconds left or None.
    level: optional (label, colour) pill shown instead of "Think fast!"; note: bottom text override."""
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
    qtext = {"missing": "Which letter is missing?", "text": "Think fast!"}.get(Q[key][0], spoken)
    fsize = 58 if len(qtext) < 34 else 46
    if level:
        lf = art.font(50 if vertical else 48, "Bold")
        lw = lf.getlength(level[0]) + 90
        c.rect(W / 2 - lw / 2, qy - 40, W / 2 + lw / 2, qy + 40, H(level[1]), r=40)
        c.text(W / 2, qy, level[0], lf, H("#FFFFFF"), anchor="mm")
    else:
        c.text(W / 2, qy, qtext, art.font(fsize, "Bold"), H("#2D2A3E"), anchor="mm")
    # picture area
    show_pics = not extra.get("pictures_are_options")
    if vertical:
        pa = (90, 340, W - 90, 1000)
    else:
        pa = (80, 290, 900, 1010)
    if extra.get("text"):
        c.rect(*pa, H("#FFFFFF"), r=60)
        px = (pa[0] + pa[2]) / 2
        for qsize in (84, 74, 66, 58, 52):
            words, lines, cur_l = extra["text"].split(), [], ""
            f = art.font(qsize, "Bold")
            for w_ in words:
                trial = (cur_l + " " + w_).strip()
                if f.getlength(trial) > (pa[2] - pa[0]) - 100 and cur_l:
                    lines.append(cur_l)
                    cur_l = w_
                else:
                    cur_l = trial
            lines.append(cur_l)
            if len(lines) <= 3 or (len(lines) <= 4 and qsize <= 66):
                break
        lh = int(qsize * 1.3)
        y0 = (pa[1] + pa[3]) / 2 - (len(lines) - 1) * lh / 2 - (60 if state == "reveal" else 0)
        for ln in lines:
            c.text(px, y0, ln, f, H("#2D2A3E"), anchor="mm")
            y0 += lh
        if state == "reveal":
            maxw = (pa[2] - pa[0]) - 70
            why = extra["why"]
            size = 46
            while size > 30 and art.font(size, "SemiBold").getlength(why) > maxw:
                size -= 2
            fw = art.font(size, "SemiBold")
            if fw.getlength(why) > maxw:
                ws = why.split()
                half = len(ws) // 2
                c.text(px, pa[3] - 115, " ".join(ws[:half]), fw, H("#2FA84F"), anchor="mm")
                c.text(px, pa[3] - 70, " ".join(ws[half:]), fw, H("#2FA84F"), anchor="mm")
            else:
                c.text(px, pa[3] - 90, why, fw, H("#2FA84F"), anchor="mm")
    elif show_pics:
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
            box_w, box_h, step = (W - 180, 150, 185) if n <= 3 else (W - 180, 130, 160)
            boxes = [(90, 1060 + i * step, 90 + box_w, 1060 + i * step + box_h) for i in range(n)]
        else:
            box_w, box_h, step = (860, 170, 240) if n <= 3 else (860, 150, 180)
            boxes = [(980, 300 + i * step, 980 + box_w, 300 + i * step + box_h) for i in range(n)]
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
            if Q[key][0] == "text" and len(label) > 10:
                tcol = tcol
            tx = x0 + 130
            if extra.get("swatch"):
                c.circle(x0 + 160, (y0 + y1) / 2, 38, H(COLOR_SWATCH[opts[i]]), outline=H("#2B2350", 80), width=3)
                tx = x0 + 220
            fs = 76
            avail = x1 - tx - 110
            while fs > 48 and art.font(fs, "Bold").getlength(label) > avail:
                fs -= 4
            if art.font(fs, "Bold").getlength(label) <= avail:
                c.text(tx, (y0 + y1) / 2, label, art.font(fs, "Bold"), tcol, anchor="lm")
            else:  # two lines
                ws = label.split()
                cut = min(range(1, len(ws)), key=lambda k: abs(len(" ".join(ws[:k])) - len(" ".join(ws[k:]))))
                l1, l2 = " ".join(ws[:cut]), " ".join(ws[cut:])
                fs = 54
                while fs > 30 and max(art.font(fs, "Bold").getlength(l1), art.font(fs, "Bold").getlength(l2)) > avail:
                    fs -= 2
                ff = art.font(fs, "Bold")
                c.text(tx, (y0 + y1) / 2 - fs * 0.58, l1, ff, tcol, anchor="lm")
                c.text(tx, (y0 + y1) / 2 + fs * 0.58, l2, ff, tcol, anchor="lm")
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
    if footer and not vertical:
        c.rect(W / 2 - 560, 1022, W / 2 + 560, 1072, H("#2B2350", 220), r=25)
        c.text(W / 2, 1047, footer, art.font(36, "SemiBold"), H("#FFE680"), anchor="mm")
    if timer is None and vertical:
        kid = Q[key][0] != "text"
        note = note or (("Think... then say it out loud!" if kid else "Comment your answer below!") if state == "ask"
                        else ("Great job!" if kid else "Did you get it right?"))
        nf = 56
        while nf > 36 and art.font(nf, "SemiBold").getlength(note) > W - 100:
            nf -= 2
        c.text(W / 2, 1810, note,
               art.font(nf, "SemiBold"), H("#7A6A9A"), anchor="mm")
    return c.final().convert("RGB")


def title_frame(lines, vertical, big=None, chars=True):
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
    for name, x in ((("lina", 0.18), ("adams", 0.82)) if chars else ()):
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
        self.audio = np.zeros(SR * 1500, dtype=np.float32)
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

    def question(self, key, vertical, header, number=None, total=None, answer_voice=None, footer=None):
        spoken, answer, *_ = ask(key)
        img_ask = frame(key, "ask", None, vertical, header, number, total, footer)
        d = self.say(spoken)
        self.show(img_ask, d + 0.4)
        for s in range(THINK, 0, -1):
            self.add_sound(TICK, self.t)
            self.show(frame(key, "ask", s, vertical, header, number, total, footer), 1.0)
        self.add_sound(DING, self.t)
        who = answer_voice or ("lina" if (number or 0) % 2 else "adams")
        d = self.say(answer, who)
        self.show(frame(key, "reveal", None, vertical, header, number, total, footer), d + 0.9)

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


def build_adult_shorts(out_dir, voice, sets=None, first=1):
    for n, (name, keys, hook_say, hook_lines, big, title) in enumerate(sets or ADULT_SHORTS, first):
        work = os.path.join(out_dir, f"work_english-test{n}")
        os.makedirs(work, exist_ok=True)
        tl = Timeline(work, voice)
        hook = title_frame(hook_lines, True, big, chars=False)
        d = tl.say(hook_say)
        tl.show(hook, d + 0.3)
        for i, k in enumerate(keys, 1):
            tl.question(k, True, name, i, len(keys), answer_voice="narrator")
        end = title_frame(["How many did you get?", "Comment your score!", "3/3 = English expert!"], True,
                          "Score?", chars=False)
        d = tl.say("How many did you get? Share your score in the comments! Three out of three means you are "
                   "an English expert. Subscribe for more English tests.")
        tl.show(end, d + 0.8)
        out = os.path.join(out_dir, f"english-test{n}.mp4")
        tl.render(out, music_vol=0.07, vertical=True)
        meta = {
            "title": title,
            "description": (f"{name}: 3 questions, 5 seconds each. Can you get 3/3? 🧠\n"
                            "Pause and check your answer before the timer ends!\n"
                            "💬 Comment your score: 1/3, 2/3 or 3/3?\n\n"
                            "🇲🇦 اختبر مستواك في اللغة الإنجليزية — هل تعرف الجواب؟\n"
                            "🇫🇷 Teste ton niveau d'anglais — tu connais la réponse ?\n\n"
                            "#shorts #EnglishTest #LearnEnglish #EnglishGrammar #Spelling"),
            "tags": ["english test", "english quiz", "spelling test", "english grammar quiz", "learn english",
                     "english vocabulary", "ielts", "toefl", "اختبار اللغة الانجليزية", "تعلم الانجليزية",
                     "قواعد اللغة الانجليزية", "test d'anglais", "quiz anglais", "grammaire anglaise"],
        }
        json.dump(meta, open(os.path.join(out_dir, f"english-test{n}_meta.json"), "w"), ensure_ascii=False, indent=2)
        print(f"adult short {n}: {out} ({tl.t:.0f} s)")


def build_adult_long(out_dir, voice):
    work = os.path.join(out_dir, "work_english-level-test")
    os.makedirs(work, exist_ok=True)
    tl = Timeline(work, voice)
    nq = sum(len(l[2]) for l in LEVELS)
    tf = lambda lines, big: title_frame(lines, False, big, chars=False)  # noqa: E731
    img = tf(["30 questions  ·  5 levels  ·  5 seconds each", "Only 3% get a perfect score!"],
             "What's your English level?")
    for text in ("What is your real English level? Let's find out with thirty questions, in five levels.",
                 "Each level is harder than the one before. Only three percent of people get a perfect score.",
                 "Take a paper and keep your score. And stay until the end: the last question is the hardest, "
                 "and we will tell you your real English level!",
                 "Then share your score and your level with us in the comments!"):
        d = tl.say(text)
        tl.show(img, d + 0.3)
    footers = {1: "Keep your score! Your English level is at the end",
               2: "Most people get 10/12 so far... and you?",
               3: "Halfway! Stay until the end to get your real level",
               4: "Only 20% of people reach Level 5...",
               5: "Final level: the last question is the hardest!"}
    level_intro = {1: "Let's start easy. Level one: beginner.",
                   2: "Level two: elementary. Still easy?",
                   3: "Level three: intermediate. This is where most people start making mistakes!",
                   4: "Level four: advanced. Only a few people get all six right.",
                   5: "Level five: expert. This is the hardest level. Good luck!"}
    num = 0
    for li, (lnum, lname, qs) in enumerate(LEVELS, 1):
        card = tf([lname, f"{len(qs)} questions"], lnum)
        d = tl.say(level_intro[li])
        tl.show(card, d + 0.6)
        for qi in range(1, len(qs) + 1):
            num += 1
            tl.question(f"lv{li}_{qi}", False, f"{lnum} · {lname}", num, nq, answer_voice="narrator",
                        footer=footers[li])
        if li < len(LEVELS):
            done = li * 6
            sc = tf([f"Your score so far: ? / {done}", "Write it down, and share it in the comments at the end!"],
                    f"{lnum} complete!")
            msg = {1: "Level one complete! That was the easy part. Write down your score.",
                   2: "Level two complete! If you have ten or more, you are doing great.",
                   3: "Level three complete! You are halfway. The next levels are much harder. Don't stop now!",
                   4: "Level four complete! Only one level left: the expert level. Ready?"}[li]
            d = tl.say(msg)
            tl.show(sc, d + 0.8)
    table = tf(["0–10: A1 Beginner      11–17: A2 Elementary", "18–23: B1 Intermediate      24–27: B2 Upper",
                "28–30: C1 Expert", "Share your score and level in the comments!"], "Your English level")
    for text in ("Finished! Count your points. Here is your English level.",
                 "Zero to ten: A one, beginner. Eleven to seventeen: A two, elementary. "
                 "Eighteen to twenty three: B one, intermediate. Twenty four to twenty seven: B two, upper intermediate. "
                 "Twenty eight to thirty: C one, expert. Congratulations!",
                 "What is your score? Share your score and your English level with us in the comments! "
                 "We read every comment.",
                 "This is a fun test, not an official exam. Subscribe for more English tests, and see you next time!"):
        d = tl.say(text)
        tl.show(table, d + 0.8)
    out = os.path.join(out_dir, "english-level-test.mp4")
    tl.render(out, music_vol=0.06)
    c = art.Canvas(1280, 720)
    c.rect(0, 0, 1280, 720, H("#2B2350"))
    c.text(640, 110, "WHAT'S YOUR", art.font(96, "Bold"), H("#FFFFFF"), anchor="mm")
    c.text(640, 225, "ENGLISH LEVEL?", art.font(120, "Bold"), H("#FFE680"), anchor="mm", stroke=6,
           stroke_fill=H("#000000"))
    cols = ["#7CCB5A", "#B8D94A", "#FFD23F", "#FF9A2E", "#E84A4A"]
    for k, (lab, col) in enumerate(zip(["A1", "A2", "B1", "B2", "C1"], cols)):
        x = 150 + k * 205
        hgt = 90 + k * 55
        c.rect(x, 640 - hgt, x + 170, 640, H(col), r=18)
        c.text(x + 85, 640 - hgt / 2, lab, art.font(64, "Bold"), H("#2B2350"), anchor="mm")
    c.rect(870, 300, 1240, 400, H("#FFFFFF"), r=30)
    c.text(1055, 350, "Only 3% get 30/30", art.font(40, "Bold"), H("#E84A4A"), anchor="mm")
    c.final().convert("RGB").save(os.path.join(out_dir, "english-level-test_thumb.jpg"), quality=92)
    meta = {
        "title": "What's Your English Level? 🧠 30-Question English Test (A1 to C1) | Only 3% Get 30/30",
        "description": (
            "Test your English in 5 levels, from Beginner to Expert! 🧠\n"
            "30 questions on grammar, vocabulary and spelling. 5 seconds per question. Keep your score "
            "and find your English level at the end!\n\n"
            "📊 Levels:\n1️⃣ Beginner\n2️⃣ Elementary\n3️⃣ Intermediate\n4️⃣ Advanced\n5️⃣ Expert\n\n"
            "🏆 Your level: 0–10 A1 · 11–17 A2 · 18–23 B1 · 24–27 B2 · 28–30 C1\n"
            "(A fun test, not an official exam.)\n\n"
            "💬 Share your score and your level with us in the comments! Example: 24/30 — B2 🎉\n\n"
            "🇲🇦 ما هو مستواك في اللغة الإنجليزية؟ اختبر نفسك في 30 سؤالاً من المبتدئ إلى الخبير!\n"
            "🇫🇷 Quel est ton niveau d'anglais ? Teste-toi en 30 questions, du débutant à l'expert !\n\n"
            "#EnglishTest #EnglishLevel #LearnEnglish #EnglishGrammar #IELTS"),
        "tags": ["english level test", "english test", "what is your english level", "english quiz",
                 "english grammar test", "a1 a2 b1 b2 c1", "ielts", "toefl", "learn english",
                 "اختبار تحديد المستوى انجليزي", "اختبار اللغة الانجليزية", "تعلم الانجليزية",
                 "test de niveau anglais", "quiz anglais", "niveau d'anglais"],
    }
    json.dump(meta, open(os.path.join(out_dir, "english-level-test_meta.json"), "w"), ensure_ascii=False, indent=2)
    print(f"done: {out} ({tl.t / 60:.1f} min)")


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
    elif what == "adult":
        build_adult_shorts(out_dir, v)
    elif what == "adult2":
        build_adult_shorts(out_dir, v, ADULT_SHORTS_2, first=3)
    elif what == "adultlong":
        build_adult_long(out_dir, v)
    else:
        build_shorts(out_dir, v)

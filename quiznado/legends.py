"""QuizNado 'Guess the Football Legend' — 3 clues per legend, A/B/C, reveal on a drawn jersey (no photos).
python3 legends.py long OUT_DIR PREFIX      -> PREFIX.mp4 (26 legends, 10+ min) + PREFIX_thumbnail.jpg
python3 legends.py frames OUT_DIR           -> preview PNGs
"""
import sys, os, math, random, json
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import weights as Wt
from weights import F, txt, emoji, overlay_rect, fit_font, shadowed, Seg, say, card, render, bar
from render import gradient, user_logo, tick, ding, whoosh, ease, YELLOW, WHITE, DEEP, PURPLE_T, GREEN

RED = (239, 68, 68); LAV = (196, 181, 253); SOFT = (221, 214, 254)
TIERS = [("EASY", (34, 197, 94)), ("MEDIUM", (234, 179, 8)), ("HARD", (249, 115, 22)), ("IMPOSSIBLE", RED)]
# kits: (body, sleeves, text colour, stripes colour or None)
BRA = ((250, 214, 0), (22, 140, 70), (22, 110, 60), None); ARG = ((120, 190, 235), (255, 255, 255), (20, 30, 60), (255, 255, 255))
FRA = ((25, 45, 120), (25, 45, 120), (255, 255, 255), None); ENG = ((250, 250, 250), (250, 250, 250), (25, 40, 90), None)
ITA = ((20, 90, 190), (20, 90, 190), (255, 255, 255), None); ESP = ((200, 25, 35), (200, 25, 35), (250, 210, 40), None)
CIV = ((245, 130, 20), (245, 130, 20), (255, 255, 255), None); SWE = ((250, 210, 0), (250, 210, 0), (20, 60, 140), None)
CMR = ((20, 130, 60), (20, 130, 60), (250, 210, 40), None); WAL = ((200, 20, 40), (200, 20, 40), (255, 255, 255), None)
MAR = ((190, 20, 35), (190, 20, 35), (255, 255, 255), None); NED = ((245, 120, 20), (245, 120, 20), (20, 20, 20), None)
# name, shirt name, number, kit, [clue1, clue2, clue3], [wrong1, wrong2], tier, fact
LEGENDS = [
    ("Pelé", "PELÉ", "10", BRA, ["🇧🇷 Brazilian forward", "Won 3 World Cups: 1958, 1962, 1970", "Played most of his career for Santos"], ["Romário", "Zico"], 0, "The only player with 3 World Cups"),
    ("Diego Maradona", "MARADONA", "10", ARG, ["🇦🇷 Argentine number 10", "Won the 1986 World Cup as captain", "The 'Hand of God' goal vs England"], ["Batistuta", "Kempes"], 0, "A legend of Napoli and Argentina"),
    ("David Beckham", "BECKHAM", "7", ENG, ["English midfielder", "Played for Man United, Real Madrid, LA Galaxy", "Famous for his curling free kicks"], ["Paul Scholes", "Michael Owen"], 0, "Free-kick king with the number 7"),
    ("Ronaldinho", "RONALDINHO", "10", BRA, ["🇧🇷 Brazilian playmaker, always smiling", "Won the Ballon d'Or in 2005", "Magic at Barcelona (2003–2008)"], ["Rivaldo", "Kaká"], 0, "The smile of football"),
    ("Zinedine Zidane", "ZIDANE", "10", FRA, ["🇫🇷 French playmaker", "2 headers in the 1998 World Cup final", "Coached Real Madrid to 3 Champions Leagues"], ["Michel Platini", "Thierry Henry"], 0, "World champion as a player"),
    ("Ronaldo Nazário", "RONALDO", "9", BRA, ["🇧🇷 Brazilian striker called 'R9'", "Top scorer of the 2002 World Cup (8 goals)", "Played for Barcelona, Inter and Real Madrid"], ["Romário", "Adriano"], 0, "'O Fenômeno', the phenomenon"),
    ("Thierry Henry", "HENRY", "14", FRA, ["🇫🇷 French striker", "Arsenal's all-time top scorer", "Unbeaten 'Invincibles' season 2003–04"], ["David Trezeguet", "Nicolas Anelka"], 0, "Arsenal's greatest goalscorer"),
    ("Paolo Maldini", "MALDINI", "3", ITA, ["🇮🇹 Italian defender", "Played his whole career for AC Milan", "Won 5 European Cups / Champions Leagues"], ["Alessandro Nesta", "Fabio Cannavaro"], 1, "One club, 25 seasons"),
    ("Andrea Pirlo", "PIRLO", "21", ITA, ["🇮🇹 Italian midfielder with a famous beard", "World Cup winner in 2006", "Played for AC Milan and Juventus"], ["Francesco Totti", "Gennaro Gattuso"], 1, "The architect of the midfield"),
    ("Steven Gerrard", "GERRARD", "8", ENG, ["English midfielder and captain", "Captain of the 2005 Istanbul comeback", "Spent 17 seasons at Liverpool"], ["Frank Lampard", "Paul Scholes"], 1, "Liverpool's captain fantastic"),
    ("Frank Lampard", "LAMPARD", "8", ENG, ["English midfielder who scored many goals", "Chelsea's all-time top scorer", "Won the Champions League in 2012"], ["John Terry", "Steven Gerrard"], 1, "A midfielder with 200+ Chelsea goals"),
    ("Andrés Iniesta", "INIESTA", "8", ESP, ["🇪🇸 Spanish midfielder", "Scored the winner in the 2010 World Cup final", "Barcelona legend, number 8"], ["Xavi", "Sergio Busquets"], 1, "The goal that made Spain world champions"),
    ("Wayne Rooney", "ROONEY", "10", ENG, ["English striker", "Manchester United's all-time top scorer", "England's top scorer until 2023"], ["Michael Owen", "Harry Kane"], 1, "Man United's record goalscorer"),
    ("Didier Drogba", "DROGBA", "11", CIV, ["🇨🇮 Ivorian striker", "Header + winning penalty in the 2012 CL final", "Chelsea legend"], ["Samuel Eto'o", "Yaya Touré"], 1, "Chelsea's big-game hero"),
    ("Xavi", "XAVI", "6", ESP, ["🇪🇸 Spanish midfielder, master of passing", "Won Euro 2008, World Cup 2010, Euro 2012", "Barcelona legend, later its coach"], ["Andrés Iniesta", "Cesc Fàbregas"], 2, "The heart of Spain's golden team"),
    ("Roberto Carlos", "R. CARLOS", "3", BRA, ["🇧🇷 Brazilian left-back", "An 'impossible' free kick vs France in 1997", "11 seasons at Real Madrid"], ["Cafu", "Marcelo"], 2, "The most famous free kick ever"),
    ("Kaká", "KAKÁ", "22", BRA, ["🇧🇷 Brazilian attacking midfielder", "Won the Ballon d'Or in 2007", "Star of AC Milan"], ["Rivaldo", "Robinho"], 2, "The last Ballon d'Or before Messi & Ronaldo"),
    ("Zlatan Ibrahimović", "IBRAHIMOVIĆ", "10", SWE, ["🇸🇪 Swedish striker", "Bicycle-kick goal vs England in 2012", "Played for Ajax, Juventus, Inter, Barça, Milan, PSG"], ["Henrik Larsson", "Andriy Shevchenko"], 2, "Goals in every league he played"),
    ("Raúl", "RAÚL", "7", ESP, ["🇪🇸 Spanish striker", "Real Madrid's number 7 before Cristiano", "Won 3 Champions Leagues with Real Madrid"], ["Fernando Morientes", "Fernando Torres"], 2, "Real Madrid's legendary number 7"),
    ("Gianluigi Buffon", "BUFFON", "1", ITA, ["🇮🇹 Italian goalkeeper", "World Cup winner in 2006", "Juventus legend for many years"], ["Dino Zoff", "Iker Casillas"], 2, "One of the greatest goalkeepers"),
    ("Javier Zanetti", "ZANETTI", "4", ARG, ["🇦🇷 Argentine defender", "Captain of Inter's 2010 treble", "Most appearances in Inter's history"], ["Diego Simeone", "Roberto Ayala"], 3, "Inter's eternal captain"),
    ("Carles Puyol", "PUYOL", "5", ESP, ["🇪🇸 Spanish defender with curly hair", "Header vs Germany, 2010 World Cup semi-final", "Barcelona captain for many years"], ["Gerard Piqué", "Sergio Ramos"], 3, "The lion-hearted captain"),
    ("Ryan Giggs", "GIGGS", "11", WAL, ["Welsh winger", "Most appearances in Man United history", "Won 13 Premier League titles"], ["Gareth Bale", "Paul Scholes"], 3, "13 league titles with one club"),
    ("Samuel Eto'o", "ETO'O", "9", CMR, ["🇨🇲 Cameroonian striker", "Treble with Barcelona (2009) and Inter (2010)", "4 times African Footballer of the Year"], ["Didier Drogba", "George Weah"], 3, "Two trebles in a row"),
    ("Mustapha Hadji", "HADJI", None, MAR, ["🇲🇦 Moroccan playmaker", "African Footballer of the Year 1998", "Famous goal vs Norway, 1998 World Cup"], ["Badou Zaki", "Noureddine Naybet"], 3, "A Moroccan football legend"),
    ("Johan Cruyff", "CRUYFF", "14", NED, ["🇳🇱 Dutch forward", "3 Ballons d'Or: 1971, 1973, 1974", "Famous for the 'Cruyff turn'"], ["Marco van Basten", "Ruud Gullit"], 3, "The father of 'total football'"),
]

class LG:  # landscape geometry (compatible with weights.background/card/render/bar)
    portrait = False; W, H = 1920, 1080; chip_y = 95
    jersey_box = (90, 175, 760, 1000)
    q_y = 215; clues = [(830, 270 + i * 118, 1860, 270 + i * 118 + 100) for i in range(3)]
    opts = [(830 + i * 352, 650, 830 + i * 352 + 330, 760) for i in range(3)]
    timer = (930, 815, 1860, 848); count = (870, 831, 48)
    qx = 1345; fact_xy = (1345, 905); jw, jh = 560, 640; label_dy = 75

class LGP:  # portrait geometry for the teaser Short
    portrait = True; W, H = 1080, 1920; chip_y = 405
    jersey_box = (250, 455, 830, 1010)
    q_y = 1060; clues = [(40, 1100 + i * 100, 1040, 1100 + i * 100 + 86) for i in range(3)]
    opts = [(30 + i * 345, 1405, 30 + i * 345 + 330, 1510) for i in range(3)]
    timer = (180, 1560, 1000, 1592); count = (95, 1576, 50)
    qx = 540; fact_xy = (540, 1640); jw, jh = 400, 457; label_dy = 50

def jersey(w, h, kit, name, number, mystery=False):
    S = 2; W, H = w * S, h * S
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    body, sleeve, tcol, stripes = kit if not mystery else ((95, 70, 160), (80, 55, 140), (255, 255, 255), None)
    P = lambda x, y: (x * W, y * H)
    left = [P(0.24, 0.10), P(0.02, 0.30), P(0.13, 0.46), P(0.24, 0.37)]
    right = [(W - x, y) for x, y in left]
    bodyp = [P(0.24, 0.10), P(0.40, 0.04), P(0.60, 0.04), P(0.76, 0.10), P(0.76, 0.98), P(0.24, 0.98)]
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    for poly in (left, right, bodyp): sd.polygon([(x + 14, y + 22) for x, y in poly], fill=(20, 0, 50, 110))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18))); d = ImageDraw.Draw(im)
    d.polygon(left, fill=sleeve); d.polygon(right, fill=sleeve); d.polygon(bodyp, fill=body)
    if stripes and not mystery:
        mask = Image.new("L", (W, H), 0); ImageDraw.Draw(mask).polygon(bodyp, fill=255)
        st = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sdd = ImageDraw.Draw(st)
        for k in range(5): x0 = W * (0.27 + k * 0.105); sdd.rectangle([x0, 0, x0 + W * 0.05, H], fill=stripes)
        st.putalpha(Image.fromarray(__import__("numpy").minimum(__import__("numpy").array(st.getchannel("A")), __import__("numpy").array(mask))))
        im.alpha_composite(st); d = ImageDraw.Draw(im)
    d.line([P(0.40, 0.04), P(0.50, 0.075), P(0.60, 0.04)], fill=(255, 255, 255, 200) if not mystery else (180, 170, 220), width=10 * S)
    if mystery:
        d.text(P(0.5, 0.58), "?", font=F(int(H * 0.42)), fill=(255, 255, 255), anchor="mm")
    else:
        f = fit_font(d, name, W * 0.46, int(H * 0.085)); d.text(P(0.5, 0.25), name, font=f, fill=tcol, anchor="mm")
        if number: d.text(P(0.5, 0.60), number, font=F(int(H * 0.36)), fill=tcol, anchor="mm")
        else: d.text(P(0.5, 0.60), "★", font=__import__("PIL.ImageFont", fromlist=["x"]).truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(H * 0.3)), fill=tcol, anchor="mm")
    return im.resize((w, h), Image.LANCZOS)

def clue_card(im, box, i, text, shown):
    if shown <= 0: return
    x0, y0, x1, y1 = box; lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    shadowed(lay, box, 26, WHITE, blur=10, off=6, alpha=60); d = ImageDraw.Draw(lay)
    r = 34; cx, cy = x0 + 22 + r, (y0 + y1) / 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PURPLE_T); d.text((cx, cy), str(i + 1), font=F(40), fill=WHITE, anchor="mm")
    tx = cx + r + 22
    if ord(text[0]) > 0x1F000:  # leading flag emoji
        flag, text = text[:2], text[2:].strip(); e = emoji(flag, 54); lay.alpha_composite(e, (int(tx), int(cy - e.height / 2))); tx += e.width + 16
    d.text((tx, cy), text, font=fit_font(d, text, x1 - tx - 25, 40), fill=DEEP, anchor="lm")
    if shown < 1:
        e = ease(shown); lay = lay.transform(lay.size, Image.AFFINE, (1, 0, -int((1 - e) * 120), 0, 1, 0))
        lay.putalpha(lay.getchannel("A").point(lambda a: int(a * e)))
    im.alpha_composite(lay)

def options(im, g, opts, correct, reveal):
    for i, box in enumerate(g.opts):
        ok = reveal and i == correct; wrong = reveal and not ok
        shadowed(im, box, 28, GREEN if ok else (LAV if wrong else WHITE), blur=10, off=6, alpha=60); d = ImageDraw.Draw(im)
        bx0, by0, bx1, by1 = box; bh = by1 - by0; r = bh * 0.3; cx = bx0 + 18 + r; cy = (by0 + by1) / 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE if ok else PURPLE_T)
        d.text((cx, cy), "ABC"[i], font=F(int(r * 1.2)), fill=GREEN if ok else WHITE, anchor="mm")
        tx = cx + r + 14; t = opts[i]
        if d.textlength(t, font=F(34)) > bx1 - tx - 16:  # long name -> surname only
            w = t.split(); t = " ".join(w[-2:]) if w[-2].lower() in ("van", "de", "da") else w[-1]
        d.text((tx, cy), t, font=fit_font(d, t, bx1 - tx - 16, 38), fill=WHITE if ok else DEEP, anchor="lm")

def legend_seg(g, L, num, total, rnd, think=8, reveal=True, chip=None, note=None):
    name, shirt, number, kit, clues, wrongs, tier, fact = L
    opts = [name] + wrongs; rnd.shuffle(opts); correct = opts.index(name)
    chip = chip or f"LEGEND {num} / {total} • {TIERS[tier][0]}"; snd = []
    t = 0.3; starts = []
    for i, c in enumerate(clues):
        starts.append(t); snd.append((t, Wt.whoosh() * 0.5))
        spoken = c[2:].strip() if ord(c[0]) > 0x1F000 else c
        t += Wt.say(snd, t, f"Clue {i + 1}. {spoken.replace('–', ' to ')}.") + 0.5
    t_opts = t; t_think = t_opts + 0.4
    for s in range(think): snd.append((t_think + s, tick() * (1.5 if s >= think - 3 else 1)))
    t_rev = t_think + think; t_end = t_rev
    if reveal:
        snd.append((t_rev, ding()))
        rv = Wt.say(snd, t_rev + 0.3, f"It's {'ABC'[correct]}: {name}! {fact}.")
        total_d = t_rev + max(4.0, rv + 1.0)
    else:
        total_d = t_rev; t_rev = 1e9
    jm = jersey(g.jw, g.jh, kit, shirt, number, True); jr = jersey(g.jw, g.jh, kit, shirt, number, False)
    def draw(im, t):
        rev = t >= t_rev; x0, y0, x1, y1 = g.jersey_box
        overlay_rect(im, g.jersey_box, 40, (255, 255, 255, 26))
        j = jr if rev else jm
        if rev and t - t_rev < 0.35:
            p = ease((t - t_rev) / 0.35); j = Image.blend(jm, jr, p)
        im.alpha_composite(j, (int((x0 + x1) / 2 - g.jw / 2), int(y0 + 20)))
        lab = name if rev else "Who is this legend?"
        txt(im, ((x0 + x1) / 2, y1 - g.label_dy), lab, 54 if rev else 46, YELLOW if rev else WHITE, 6)
        txt(im, (g.qx, g.q_y), "Here is the answer!" if rev else (note if (note and t >= t_opts) else "Guess the football legend!"), 48, WHITE if rev else YELLOW, 6)
        for i in range(3): clue_card(im, g.clues[i], i, clues[i], min(1, max(0, (t - starts[i]) / 0.35)))
        if t >= t_opts:
            options(im, g, opts, correct, rev)
            if not rev and t >= t_think:
                left = max(0.0, t_end - t); bar(im, g, left / think, max(1, math.ceil(left)))
            if rev: txt(im, g.fact_xy, fact, 46, WHITE, 5)
        if rev and t - t_rev < 0.25:
            im.alpha_composite(Image.new("RGBA", (g.W, g.H), (255, 255, 255, int(80 * (1 - (t - t_rev) / 0.25)))))
    def key(t):
        for st in starts:
            if st <= t < st + 0.36: return None
        if t_rev <= t < t_rev + 0.36: return None
        if t < t_opts: return ("clues", sum(t >= s for s in starts))
        if t < t_think: return "o"
        if t < min(t_rev, t_end): return ("c", int((t - t_think) * 10))
        return "r"
    return Seg(total_d, draw, key, snd, chip), "ABC"[correct]

def make_long(outdir, prefix, seed=7):
    g = LG(); rnd = random.Random(seed); N = len(LEGENDS); segs = []; answers = []
    segs.append(card(g, [("GUESS THE FOOTBALL LEGEND", 92, YELLOW), (f"{N} legends • 3 clues each", 62, WHITE),
                         (f"Count your points: ___ / {N}", 54, SOFT)],
                     f"Welcome to QuizNado! Can you guess {N} football legends from just three clues? "
                     "From easy to impossible. Count your points. Let's go!"))
    tier_say = ["Level one: easy. Everybody knows them!", "Level two: medium. Real fans only!",
                "Level three: hard. Do you remember them?", "Level four: impossible! Only true football experts."]
    prev = -1
    for i, L in enumerate(LEGENDS):
        if L[6] != prev:
            prev = L[6]; nm, col = TIERS[prev]
            if prev == 2:
                segs.append(card(g, [("Enjoying it?", 86, WHITE), ("SUBSCRIBE & LIKE", 104, YELLOW), ("It really helps QuizNado", 50, SOFT)],
                                 "If you like it so far, subscribe and like! It really helps QuizNado.", 3, 0.5))
            segs.append(card(g, [(f"LEVEL {prev + 1}", 120, YELLOW), (nm, 90, col)], tier_say[prev], 2.4, 0.4,
                             f"LEVEL {prev + 1} • {nm}"))
        s, a = legend_seg(g, L, i + 1, N, rnd); segs.append(s); answers.append(f"{i + 1}. {a} {L[0]}")
    segs.append(card(g, [("What's your score?", 96, YELLOW), (f"___ / {N}", 124, WHITE), ("Comment it below!", 60, SOFT)],
                     f"What is your score out of {N}? Write it in the comments! Which legend is your favourite? "
                     "Subscribe to QuizNado for more challenges!", 3, 1.2))
    total = render(segs, g, f"{outdir}/{prefix}.mp4"); thumbnail(f"{outdir}/{prefix}_thumbnail.jpg")
    open(f"{outdir}/{prefix}_answers.txt", "w").write("\n".join(answers) + "\n")
    print("long", round(total, 1), "s", flush=True)

def make_teaser(out, long_thumb, seed=7):
    """The ONE Short: 2 HARD legends with answers + the long video's last legend WITHOUT answer -> full video."""
    g = LGP(); N = len(LEGENDS); hard = [i for i, L in enumerate(LEGENDS) if L[6] == 2]
    picks = [hard[2], hard[5]]  # Kaká, Buffon
    r2 = random.Random(seed)  # replay the long video's option shuffles so the last legend has the same A/B/C order
    for i in range(N - 1): r2.shuffle([LEGENDS[i][0]] + LEGENDS[i][5])
    segs = [card(g, [("3 football legends", 80, WHITE), ("Only 1% know", 84, WHITE), ("the last one!", 84, YELLOW)],
                 "Three football legends. Only one percent know the last one!", 2.4, 0.2, "GUESS THE LEGEND")]
    rr = random.Random(seed + 99)
    for k, i in enumerate(picks):
        s, _ = legend_seg(g, LEGENDS[i], k + 1, 3, rr, think=5, chip=f"LEGEND {k + 1} / 3 • HARD"); segs.append(s)
    s, a = legend_seg(g, LEGENDS[-1], 3, 3, r2, think=6, reveal=False, chip=f"LEGEND {N} • IMPOSSIBLE", note="Answer in the full video!")
    segs.append(s)
    th = Image.open(long_thumb).convert("RGB"); snd = []
    d = say(snd, 0.2, f"Want the answer? Watch the full video, guess the football legend, on the QuizNado channel. Subscribe and like!") + 0.9
    def draw(im, t):
        e = ease(t / 0.4); lay = Image.new("RGBA", (g.W, g.H), (0, 0, 0, 0))
        txt(lay, (g.W / 2, 560), "Want the answer?", 86, YELLOW, 7); txt(lay, (g.W / 2, 665), "Watch the full video", 70, WHITE, 6)
        tw = 940; t2 = th.resize((tw, int(tw * th.height / th.width)), Image.LANCZOS)
        shadowed(lay, (70, 740, 70 + tw, 740 + t2.height), 24, WHITE, blur=16, off=10, alpha=110)
        m = Image.new("L", t2.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, t2.width - 1, t2.height - 1], radius=24, fill=255)
        lay.paste(t2, (70, 740), m); dd = ImageDraw.Draw(lay); cx, cy = 70 + tw - 70, 740 + t2.height - 55
        dd.ellipse([cx - 48, cy - 48, cx + 48, cy + 48], fill=RED); dd.polygon([(cx - 15, cy - 24), (cx - 15, cy + 24), (cx + 26, cy)], fill=WHITE)
        y = 740 + t2.height + 75; txt(lay, (g.W / 2, y), f"Guess the Football Legend • {N} legends", 46, WHITE, 5)
        dd = ImageDraw.Draw(lay); dd.rounded_rectangle([190, y + 70, 890, y + 175], radius=52, fill=RED)
        dd.text((g.W / 2, y + 122), "SUBSCRIBE & LIKE", font=F(60), fill=WHITE, anchor="mm")
        if e < 1: lay.putalpha(lay.getchannel("A").point(lambda a: int(a * e)))
        im.alpha_composite(lay)
    segs.append(Seg(max(5.5, d), draw, lambda t: "s" if t >= 0.4 else None, snd, "QuizNado"))
    total = render(segs, g, out)
    print("teaser", round(total, 1), "s; last legend answer", a, flush=True)

def thumbnail(out):
    im = gradient(1920, 1080); im.alpha_composite(user_logo(190), (50, 40))
    txt(im, (330, 130), "GUESS THE", 100, WHITE, 8, "lm"); txt(im, (960, 280), "FOOTBALL LEGEND", 150, YELLOW, 10)
    for k, kit in enumerate([BRA, ARG, FRA, ESP, ITA]):
        j = jersey(330, 380, kit, "", None, mystery=(k == 2)) if k == 2 else jersey(330, 380, kit, "", "?", False)
        im.alpha_composite(j, (70 + k * 360, 420))
    d = ImageDraw.Draw(im); d.rounded_rectangle([560, 880, 1360, 1000], radius=60, fill=RED)
    d.text((960, 940), f"{len(LEGENDS)} LEGENDS • 3 CLUES", font=F(64), fill=WHITE, anchor="mm")
    im.convert("RGB").resize((1280, 720), Image.LANCZOS).save(out, quality=92)

if __name__ == "__main__":
    if sys.argv[1] == "long": make_long(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "teaser": make_teaser(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "frames":
        o = sys.argv[2]; g = LG(); s, _ = legend_seg(g, LEGENDS[17], 18, 26, random.Random(1))
        for tt, nm in ((5.0, "clues"), (s.dur - 9, "think"), (s.dur - 1.0, "rev")):
            im = Wt.background(g, s.chip); s.draw(im, tt); im.convert("RGB").save(f"{o}/lg_{nm}.png")
        thumbnail(f"{o}/lg_thumb.jpg")

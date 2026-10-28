"""QuizNado 'Follow the yellow ball' concentration test — Shorts (portrait) and multi-level long video (landscape).

python3 concentration.py short OUT.mp4 LEVEL_NAME NBALLS NSWAPS D_START D_END SEED
python3 concentration.py long  OUT_DIR  PREFIX SEED      -> PREFIX.mp4 + PREFIX_thumbnail.jpg (6 levels)
"""
import sys, os, math, random, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import F, gradient, user_logo, tts, music, tick, ding, whoosh, ease, SR, FPS, YELLOW, WHITE, DEEP

RED = (239, 68, 68)
DIFF = [("EASY", (34, 197, 94)), ("MEDIUM", (234, 179, 8)), ("HARD", (249, 115, 22)), ("IMPOSSIBLE", RED)]
LONG_LEVELS = [  # name, balls, swaps, slowest, fastest
    ("EASY", 3, 8, 1.05, 0.75), ("MEDIUM", 3, 14, 0.9, 0.5), ("HARD", 3, 22, 0.8, 0.32),
    ("VERY HARD", 4, 24, 0.75, 0.3), ("EXPERT", 4, 30, 0.7, 0.24), ("IMPOSSIBLE", 5, 36, 0.6, 0.19)]
VOICE = "af_heart"

def ball_sprite(R, core, glow):
    s = int(R * 4); im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([s / 2 - R * 1.3, s / 2 - R * 1.3, s / 2 + R * 1.3, s / 2 + R * 1.3], fill=glow + (120,))
    im = im.filter(ImageFilter.GaussianBlur(R * 0.22)); d = ImageDraw.Draw(im)
    d.ellipse([s / 2 - R, s / 2 - R, s / 2 + R, s / 2 + R], fill=core + (255,))
    hl = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse([s / 2 - R * 0.55, s / 2 - R * 0.7, s / 2 - R * 0.05, s / 2 - R * 0.25], fill=(255, 255, 255, 140))
    im.alpha_composite(hl.filter(ImageFilter.GaussianBlur(R * 0.1)))
    return im

class Geo:
    def __init__(self, portrait, n):
        self.portrait = portrait; self.n = n
        if portrait:
            self.W, self.H = 1080, 1920; self.BY = 1000; self.R = {3: 82, 4: 72, 5: 62}[n]
            sp = {3: 270, 4: 235, 5: 195}[n]; self.title_y = 640; self.bar = (140, 940, 1330, 1395)
            self.note_y = 1300; self.count_y = 1480; self.chip_y = 420; self.num_off = 175; self.big_y = 1000
        else:
            self.W, self.H = 1920, 1080; self.BY = 560; self.R = {3: 80, 4: 74, 5: 68}[n]
            sp = {3: 340, 4: 300, 5: 270}[n]; self.title_y = 255; self.bar = (560, 1360, 800, 850)
            self.note_y = 830; self.count_y = 950; self.chip_y = 150; self.num_off = 165; self.big_y = 560
        self.slots = [self.W / 2 + (i - (n - 1) / 2) * sp for i in range(n)]

def background(g, chip_text):
    W, H = g.W, g.H; bg = gradient(W, H); d = ImageDraw.Draw(bg)
    if g.portrait:
        bg.alpha_composite(user_logo(200), ((W - 200) // 2, 145))
        bg.alpha_composite(user_logo(110, alpha=0.5), ((W - 110) // 2, H - 310))
        d.text((W // 2, H - 180), "@QuizNado • New quiz every day", font=F(30), fill=(221, 214, 254), anchor="mm")
    else:
        bg.alpha_composite(user_logo(135), (35, 22))
        bg.alpha_composite(user_logo(80, alpha=0.5), (W - 120, H - 120))
        d.text((W - 80, H - 20), "@QuizNado", font=F(22), fill=(221, 214, 254), anchor="mm")
    if chip_text:
        f = F(40 if g.portrait else 38); w = d.textlength(chip_text, font=f) + 70
        d.rounded_rectangle([W / 2 - w / 2, g.chip_y - 38, W / 2 + w / 2, g.chip_y + 38], radius=38, fill=YELLOW)
        d.text((W / 2, g.chip_y), chip_text, font=f, fill=DEEP, anchor="mm")
    return bg

def txt(im, xy, s, size, col, stroke=6):
    ImageDraw.Draw(im).text(xy, s, font=F(size), fill=col, anchor="mm", stroke_width=stroke, stroke_fill=DEEP)

def big(im, g, lines, cy=None):
    tot = sum(s * 1.45 for _, s, _ in lines); y = (cy or g.H / 2) - tot / 2
    for t, s, c in lines:
        txt(im, (g.W / 2, y + s * 0.72), t, s, c, 7); y += s * 1.45

def arrow(im, x, y):
    d = ImageDraw.Draw(im); d.polygon([(x - 45, y), (x + 45, y), (x, y + 70)], fill=YELLOW); d.rectangle([x - 17, y - 70, x + 17, y], fill=YELLOW)

def bar(im, g, frac):
    x0, x1, y0, y1 = g.bar
    ov = Image.new("RGBA", (g.W, g.H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) // 2, fill=(255, 255, 255, 40)); im.alpha_composite(ov)
    d = ImageDraw.Draw(im); d.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) // 2, outline=WHITE, width=4)
    if frac > 0.01:
        idx = min(3, int(frac * 4)); col = DIFF[idx][1]
        d.rounded_rectangle([x0 + 6, y0 + 6, x0 + 6 + (x1 - x0 - 12) * frac, y1 - 6], radius=(y1 - y0) // 2 - 6, fill=col)
        for k in (1, 2, 3):
            xx = x0 + (x1 - x0) * k / 4; d.line([xx, y0 + 8, xx, y1 - 8], fill=(255, 255, 255), width=3)
        txt(im, (g.W / 2, y1 + 55), DIFF[idx][0], 50, col, 5)

class Seg:
    """A piece of the video: draw(im, local_t) + duration + sounds (local times)."""
    def __init__(self, dur, draw, sounds=(), chip=None):
        self.dur, self.draw, self.sounds, self.chip = dur, draw, list(sounds), chip

def say(sounds, at, text):
    a = tts(text, VOICE); sounds.append((at, a)); return len(a) / SR

def card_seg(g, lines, voice_text, min_dur=2.5, pad=0.6, chip=None):
    snd = []; d = say(snd, 0.2, voice_text) + 0.2 + pad if voice_text else 0
    def draw(im, t):
        lay = Image.new("RGBA", (g.W, g.H), (0, 0, 0, 0)); big(lay, g, lines, g.big_y)
        e = ease(t / 0.35)
        if e < 1:
            sc = 0.85 + 0.15 * e; w, h = int(g.W * sc), int(g.H * sc); l2 = lay.resize((w, h), Image.BILINEAR)
            l2.putalpha(l2.getchannel("A").point(lambda a: int(a * e))); im.alpha_composite(l2, ((g.W - w) // 2, (g.H - h) // 2))
        else: im.alpha_composite(lay)
    return Seg(max(min_dur, d), draw, snd, chip)

def level_seg(g, n, nswaps, d0, d1, seed, chip, *, intro_voice=None, cta=True, long_mode=False, ask_count=5):
    """show target -> shuffle with bar -> ask + countdown -> reveal."""
    rnd = random.Random(seed); snd = []; R = g.R; sw = R * 2
    tgt = ball_sprite(R, (250, 204, 21), (250, 204, 21)); std = ball_sprite(R, (236, 233, 254), (167, 139, 250))
    start = rnd.randrange(n)
    show = 3.0
    if intro_voice: show = max(show, say(snd, 0.2, intro_voice) + 0.9)
    else: say(snd, 0.2, "Keep your eyes on the yellow ball.")
    t_shuf = show; swaps = []; t = t_shuf + 0.3
    for i in range(nswaps):
        dur = d0 + (d1 - d0) * (i / max(1, nswaps - 1)) ** 0.8
        a, b = sorted(rnd.sample(range(n), 2)); swaps.append((t, dur, a, b, rnd.choice([1, -1])))
        snd.append((t, whoosh() * 0.8)); t += dur + 0.06
    t_ask = t + 0.3; cta_at = t_shuf + (t_ask - t_shuf) * 0.45
    if cta: say(snd, cta_at, "Still following? Subscribe and like!")
    nums = ", ".join(str(k + 1) for k in range(n - 1)) + f" or {n}"
    say(snd, t_ask + 0.1, "Where is the yellow ball? " + ("Write down your answer!" if long_mode else f"Comment {nums}!"))
    for s in range(ask_count): snd.append((t_ask + 1.4 + s, tick()))
    t_rev = t_ask + 1.4 + ask_count
    slot = list(range(n))  # slot[ball]
    def positions(tt):
        sl = list(range(n)); out = None
        for (st, du, a, b, sgn) in swaps:
            ba, bb = sl.index(a), sl.index(b)
            if tt < st: break
            if tt < st + du:
                p = (1 - math.cos(math.pi * (tt - st) / du)) / 2; res = {}
                for ball in range(n):
                    if ball in (ba, bb):
                        fr, to = (a, b) if ball == ba else (b, a)
                        x = g.slots[fr] + (g.slots[to] - g.slots[fr]) * p
                        lift = (1 if ball == ba else -1) * sgn * (110 + 45 * (b - a - 1)) * math.sin(math.pi * p)
                        res[ball] = (x, g.BY - lift)
                    else: res[ball] = (g.slots[sl[ball]], g.BY)
                return res
            sl[ba], sl[bb] = b, a
        return {ball: (g.slots[sl[ball]], g.BY) for ball in range(n)}
    final = positions(1e9)[start]; final_slot = g.slots.index(final[0])
    snd.append((t_rev, ding()))
    rv = say(snd, t_rev + 0.3, f"It was number {final_slot + 1}!" + (" One point if you got it!" if long_mode else " Did you get it right?"))
    total = t_rev + max(3.0, rv + 0.9)
    def draw(im, t):
        pos = positions(t)
        for ball in range(n):
            x, y = pos[ball]; spr = std
            if ball == start:
                if t < t_shuf: spr = Image.blend(tgt, std, max(0, min(1, (t - (t_shuf - 0.6)) / 0.6)))
                elif t >= t_rev: spr = Image.blend(std, tgt, max(0, min(1, (t - t_rev) / 0.3)))
            im.alpha_composite(spr, (int(x - sw), int(y - sw)))
        if t < t_shuf - 0.6:
            arrow(im, pos[start][0], g.BY - R - (140 if g.portrait else 95) + 14 * math.sin(t * 8))
            txt(im, (g.W / 2, g.title_y), "Follow the yellow ball!", 64, WHITE)
        if t < t_ask: bar(im, g, 0 if t < t_shuf else min(1, (t - t_shuf) / (t_ask - t_shuf)))
        if cta and cta_at <= t < cta_at + 3.0 and t < t_ask:
            d = ImageDraw.Draw(im); w = 370
            d.rounded_rectangle([g.W / 2 - w, g.title_y - 50, g.W / 2 + w, g.title_y + 50], radius=50, fill=RED)
            d.text((g.W / 2, g.title_y), "SUBSCRIBE & LIKE", font=F(56), fill=WHITE, anchor="mm")
        if t >= t_ask:
            for k in range(n):
                win = t >= t_rev and k == final_slot
                txt(im, (g.slots[k], g.BY - g.num_off), str(k + 1), 140 if win else 100, YELLOW if win else WHITE, 7)
            if t < t_rev:
                txt(im, (g.W / 2, g.title_y), "Where is the yellow ball?", 64, YELLOW)
                txt(im, (g.W / 2, g.note_y), "Write down your answer!" if long_mode else f"Comment {nums}!", 56, WHITE)
                if t >= t_ask + 1.4:
                    c = max(1, ask_count - int(t - t_ask - 1.4)); r = 70 if not g.portrait else 85
                    d = ImageDraw.Draw(im); d.ellipse([g.W / 2 - r, g.count_y - r, g.W / 2 + r, g.count_y + r], fill=WHITE)
                    d.text((g.W / 2, g.count_y), str(c), font=F(int(r * 1.3)), fill=DEEP, anchor="mm")
            else:
                txt(im, (g.W / 2, g.title_y), f"It was number {final_slot + 1}!", 76, YELLOW)
                txt(im, (g.W / 2, g.note_y), "+1 point if you got it!" if long_mode else "Did you get it right?", 56, WHITE)
                if t - t_rev < 0.25:
                    im.alpha_composite(Image.new("RGBA", (g.W, g.H), (255, 255, 255, int(80 * (1 - (t - t_rev) / 0.25)))))
    return Seg(total, draw, snd, chip), final_slot + 1

def render(segs, g, out):
    total = sum(s.dur for s in segs); mix = music(total) * 0.85; t0 = 0
    for s in segs:
        for at, a in s.sounds:
            i = int((t0 + at) * SR); j = min(len(mix), i + len(a)); mix[i:j] += a[:j - i]
        t0 += s.dur
    wav = out + ".wav"; sf.write(wav, np.clip(mix, -1, 1), SR)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{g.W}x{g.H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE); bgs = {}
    t0 = 0
    for s in segs:
        if s.chip not in bgs: bgs[s.chip] = background(g, s.chip)
        for fi in range(int(round(s.dur * FPS))):
            im = bgs[s.chip].copy(); s.draw(im, fi / FPS); p.stdin.write(im.convert("RGB").tobytes())
        t0 += s.dur
    p.stdin.close(); p.wait(); os.remove(wav)
    tmp = out + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", out, "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out); return total

def make_short(out, level, n, nswaps, d0, d1, seed):
    g = Geo(True, n); chip = f"CONCENTRATION TEST • LEVEL {level}"
    intro = card_seg(g, [("What is your level", 82, WHITE), ("of concentration?", 82, WHITE),
                         (f"{n} balls • Level {level}", 64, YELLOW)],
                     f"What is your level of concentration? Level {level.lower()}, with {n} balls. Follow the yellow ball!", 3.2, 0.3, chip)
    lv, ans = level_seg(g, n, nswaps, d0, d1, seed, chip)
    outro = card_seg(g, [("Comment your level!", 84, YELLOW), ("EASY • HARD • IMPOSSIBLE", 54, WHITE),
                         ("Subscribe for", 70, WHITE), ("a new test every day", 70, WHITE)],
                     "Comment your level, and subscribe to QuizNado for a new test every day!", 3.0, 0.8, chip)
    d = render([intro, lv, outro], g, out); print("short", level, round(d, 1), "s, answer", ans, flush=True); return ans

def make_long(outdir, prefix, seed):
    segs = []; answers = []
    g3 = Geo(False, 3)
    segs.append(card_seg(g3, [("CONCENTRATION TEST", 110, YELLOW), ("6 levels • faster and faster", 64, WHITE),
                              ("Count your points: ___ / 6", 56, (221, 214, 254))],
                         "Welcome to QuizNado! This is the ultimate concentration test. Six levels, faster and faster, "
                         "with more balls. Follow the yellow ball, and give yourself one point for every right answer. Let's go!", 3, 0.6, None))
    for i, (name, n, ns, d0, d1) in enumerate(LONG_LEVELS):
        g = Geo(False, n); chip = f"LEVEL {i + 1} / 6 • {name}"
        segs.append(card_seg(g, [(f"LEVEL {i + 1}", 130, YELLOW), (name, 90, DIFF[min(3, i * 4 // 6)][1] if name != "IMPOSSIBLE" else RED),
                                 (f"{n} balls", 60, WHITE)], f"Level {i + 1}. {name.lower()}. {n} balls.", 2.6, 0.5, chip))
        sg, ans = level_seg(g, n, ns, d0, d1, seed * 10 + i, chip, cta=False, long_mode=True)
        segs.append(sg); answers.append(ans)
        if i in (1, 3):
            segs.append(card_seg(g, [("Enjoying it?", 90, WHITE), ("SUBSCRIBE & LIKE", 110, YELLOW),
                                     ("It really helps QuizNado", 52, (221, 214, 254))],
                                 "If you liked it so far, subscribe and like! It really helps QuizNado.", 3, 0.5, chip))
    segs.append(card_seg(g3, [("What's your score?", 100, YELLOW), ("___ / 6", 130, WHITE),
                              ("Comment it below!", 64, (221, 214, 254))],
                         "What is your score out of six? Write it in the comments! And subscribe to QuizNado for a new challenge every day.", 3, 1.2, None))
    total = render_multi(segs, outdir, prefix)
    thumbnail(f"{outdir}/{prefix}_thumbnail.jpg")
    print("long", round(total, 1), "s, answers", answers, flush=True); return answers

def render_multi(segs, outdir, prefix):
    # all segments are landscape 1920x1080; Geo only changes ball layout, background is the same size
    g = Geo(False, 3); return render(segs, g, f"{outdir}/{prefix}.mp4")

def thumbnail(out):
    g = Geo(False, 3); im = background(g, None); im = gradient(1920, 1080); d = ImageDraw.Draw(im)
    im.alpha_composite(user_logo(220), (70, 50))
    txt(im, (1180, 190), "CONCENTRATION", 130, YELLOW, 9); txt(im, (1180, 340), "TEST", 150, WHITE, 9)
    R = 95; tg = ball_sprite(R, (250, 204, 21), (250, 204, 21)); st = ball_sprite(R, (236, 233, 254), (167, 139, 250))
    for i, x in enumerate([560, 960, 1360]):
        im.alpha_composite(tg if i == 1 else st, (x - 2 * R, 620 - 2 * R))
    arrow(im, 960, 420)
    for i, (nm, col) in enumerate(DIFF):
        x = 240 + i * 480; d = ImageDraw.Draw(im)
        d.rounded_rectangle([x - 205, 860, x + 205, 960], radius=50, fill=col)
        d.text((x, 910), nm, font=F(54), fill=WHITE, anchor="mm", stroke_width=3, stroke_fill=DEEP)
    txt(im, (1650, 620), "6", 200, WHITE, 9); txt(im, (1650, 750), "LEVELS", 60, WHITE, 5)
    im.convert("RGB").resize((1280, 720), Image.LANCZOS).save(out, quality=92)

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "short":
        out, level, n, ns, d0, d1, seed = sys.argv[2:9]
        make_short(out, level, int(n), int(ns), float(d0), float(d1), int(seed))
    elif mode == "long":
        make_long(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    elif mode == "thumb":
        thumbnail(sys.argv[2])

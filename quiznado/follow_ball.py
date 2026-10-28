"""QuizNado 'Follow the ball' concentration test Short (idea: track one ball while balls swap faster and faster).
usage: python3 follow_ball.py OUT.mp4 [level: easy|hard|impossible] [seed]"""
import sys, os, math, random, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import (F, gradient, user_logo, tts, music, tick, ding, whoosh, ease, shadowed,
                    SR, FPS, YELLOW, WHITE, DEEP, PURPLE_T, LAV, GREEN)

W, H = 1080, 1920
LEVELS = {"easy": (10, 1.0, 0.55), "hard": (30, 0.9, 0.28), "impossible": (34, 0.8, 0.20)}
DIFF = [("EASY", (34, 197, 94)), ("MEDIUM", (234, 179, 8)), ("HARD", (249, 115, 22)), ("IMPOSSIBLE", (239, 68, 68))]
SLOTS = [270, 540, 810]; BY = 1000; R = 82

def ball_sprite(core, glow):
    s = R * 4; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([s / 2 - R * 1.55, s / 2 - R * 1.55, s / 2 + R * 1.55, s / 2 + R * 1.55], fill=glow + (150,))
    im = im.filter(ImageFilter.GaussianBlur(34)); d = ImageDraw.Draw(im)
    d.ellipse([s / 2 - R, s / 2 - R, s / 2 + R, s / 2 + R], fill=core + (255,))
    hl = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse([s / 2 - R * 0.55, s / 2 - R * 0.7, s / 2 - R * 0.05, s / 2 - R * 0.25], fill=(255, 255, 255, 140))
    im.alpha_composite(hl.filter(ImageFilter.GaussianBlur(8)))
    return im

def blend_sprite(a, b, t):
    return Image.blend(a, b, max(0, min(1, t)))

def main(out, level="hard", seed=7):
    nswaps, d0, d1 = LEVELS[level]; rnd = random.Random(seed)
    tgt_sprite = ball_sprite((250, 204, 21), (250, 204, 21))
    std_sprite = ball_sprite((236, 233, 254), (167, 139, 250))
    # ---------- background with logo + watermark ----------
    bg = gradient(W, H); d = ImageDraw.Draw(bg)
    bg.alpha_composite(user_logo(200), ((W - 200) // 2, 145))
    wm = user_logo(110, alpha=0.5); bg.alpha_composite(wm, ((W - 110) // 2, H - 310))
    d.text((W // 2, H - 180), "@QuizNado • New quiz every day", font=F(30), fill=(221, 214, 254), anchor="mm")
    def chip(im, text, y, fill=YELLOW, col=DEEP, size=40):
        dd = ImageDraw.Draw(im); f = F(size); w = dd.textlength(text, font=f) + 70
        dd.rounded_rectangle([W / 2 - w / 2, y - 38, W / 2 + w / 2, y + 38], radius=38, fill=fill)
        dd.text((W / 2, y), text, font=f, fill=col, anchor="mm")
    base = bg.copy(); chip(base, f"CONCENTRATION TEST • LEVEL {level.upper()}", 420)

    # ---------- timeline ----------
    audio = []; voice = "af_heart"
    def say(at, text):
        a = tts(text, voice); audio.append((at, a)); return len(a) / SR
    t_intro = 0.0
    dur_intro = max(3.2, say(0.2, "What is your level of concentration? Follow the yellow ball!") + 0.5)
    t_show = dur_intro; dur_show = 3.4
    say(t_show + 0.2, "Keep your eyes on it.")
    t_shuf = t_show + dur_show
    # swaps with accelerating durations
    swaps = []; t = t_shuf + 0.3
    for i in range(nswaps):
        dur = d0 + (d1 - d0) * (i / max(1, nswaps - 1)) ** 0.8
        a, b = rnd.sample([0, 1, 2], 2); swaps.append((t, dur, min(a, b), max(a, b), rnd.choice([1, -1])))
        audio.append((t, whoosh() * 0.8)); t += dur + 0.06
    t_end_shuf = t + 0.3
    cta_at = t_shuf + (t_end_shuf - t_shuf) * 0.45
    say(cta_at, "Still following? Subscribe and like!")
    t_ask = t_end_shuf; T_count = 5
    say(t_ask + 0.1, "Where is the yellow ball? Comment one, two or three!")
    for s in range(T_count): audio.append((t_ask + 1.2 + s, tick()))
    t_rev = t_ask + 1.2 + T_count
    # final position of the target (ball id 0 starts in slot "start")
    start = rnd.choice([0, 1, 2]); pos = [0, 1, 2]  # pos[ball] = slot
    order = [0, 1, 2]
    slot_of = {b: b for b in range(3)}
    tgt_ball = start
    for (_, _, a, b, _) in swaps:
        ba = [k for k, v in slot_of.items() if v == a][0]; bb = [k for k, v in slot_of.items() if v == b][0]
        slot_of[ba], slot_of[bb] = b, a
    final_slot = slot_of[tgt_ball]
    audio.append((t_rev, ding()))
    dur_rev = say(t_rev + 0.3, f"It was number {final_slot + 1}! Did you get it right?") + 0.8
    t_out = t_rev + max(3.2, dur_rev)
    dur_out = say(t_out + 0.2, "Comment your level, and subscribe to QuizNado for level impossible!") + 1.0
    total = t_out + dur_out

    # ---------- audio ----------
    mix = music(total) * 0.9
    for at, s in audio:
        a = int(at * SR); b = min(len(mix), a + len(s)); mix[a:b] += s[:b - a]
    mix = np.clip(mix, -1, 1); wav = out + ".wav"; sf.write(wav, mix, SR)

    # ---------- positions ----------
    def ball_xy(ball, t):
        """x,y of ball at time t, following swaps."""
        slot = {b: b for b in range(3)}
        for (st, du, a, b, sgn) in swaps:
            ba = [k for k, v in slot.items() if v == a][0]; bb = [k for k, v in slot.items() if v == b][0]
            if t < st: break
            if t < st + du:
                p = ease((t - st) / du) if False else (1 - math.cos(math.pi * (t - st) / du)) / 2
                if ball in (ba, bb):
                    fr, to = (a, b) if ball == ba else (b, a)
                    x = SLOTS[fr] + (SLOTS[to] - SLOTS[fr]) * p
                    lift = (1 if ball == ba else -1) * sgn * (130 + 60 * (b - a - 1)) * math.sin(math.pi * p)
                    return x, BY - lift
                return SLOTS[slot[ball]], BY
            slot[ba], slot[bb] = b, a
        return SLOTS[slot[ball]], BY

    def bar(im, frac):
        x0, x1, y0, y1 = 140, 940, 1330, 1395
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ov).rounded_rectangle([x0, y0, x1, y1], radius=33, fill=(255, 255, 255, 40))
        im.alpha_composite(ov); dd = ImageDraw.Draw(im)
        dd.rounded_rectangle([x0, y0, x1, y1], radius=33, outline=WHITE, width=4)
        if frac > 0.01:
            idx = min(3, int(frac * 4)); col = DIFF[idx][1]
            dd.rounded_rectangle([x0 + 6, y0 + 6, x0 + 6 + (x1 - x0 - 12) * frac, y1 - 6], radius=27, fill=col)
            for k in (1, 2, 3):
                xx = x0 + (x1 - x0) * k / 4; dd.line([xx, y0 + 8, xx, y1 - 8], fill=(255, 255, 255, 120), width=3)
            dd.text((W / 2, y1 + 60), DIFF[idx][0], font=F(54), fill=col, anchor="mm", stroke_width=5, stroke_fill=DEEP)

    def big(im, lines, y=None):
        dd = ImageDraw.Draw(im); tot = sum(s * 1.45 for _, s, _ in lines); yy = (y or H / 2) - tot / 2
        for txt, s, c in lines:
            dd.text((W / 2, yy + s * 0.6), txt, font=F(s), fill=c, anchor="mm", stroke_width=7, stroke_fill=DEEP); yy += s * 1.45

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nfr = int(math.ceil(total * FPS)); sw = R * 2
    for fi in range(nfr):
        t = fi / FPS; im = base.copy(); dd = ImageDraw.Draw(im)
        if t < t_show:
            e = ease(t / 0.4)
            big(im, [("What is your level", 82, WHITE), ("of concentration?", 82, WHITE), ("Follow the yellow ball!", 64, YELLOW)], 1000)
            if e < 1: im = Image.blend(base, im, e)
        elif t < t_out:
            # target color: yellow during show, fades to standard at the end of show; yellow again at reveal
            for ball in range(3):
                x, y = ball_xy(ball, t)
                spr = std_sprite
                if ball == start:
                    if t < t_shuf: spr = blend_sprite(tgt_sprite, std_sprite, (t - (t_shuf - 0.6)) / 0.6)
                    elif t >= t_rev: spr = blend_sprite(std_sprite, tgt_sprite, (t - t_rev) / 0.3)
                im.alpha_composite(spr, (int(x - sw), int(y - sw)))
            if t < t_shuf - 0.6:  # bouncing arrow on target
                x, _ = ball_xy(start, t); yy = BY - 230 + 18 * math.sin(t * 8)
                dd = ImageDraw.Draw(im)
                dd.polygon([(x - 45, yy), (x + 45, yy), (x, yy + 70)], fill=YELLOW); dd.rectangle([x - 17, yy - 70, x + 17, yy], fill=YELLOW)
                dd.text((W / 2, 640), "Keep your eyes on it!", font=F(64), fill=WHITE, anchor="mm", stroke_width=6, stroke_fill=DEEP)
            frac = 0 if t < t_shuf else min(1, (t - t_shuf) / (t_end_shuf - t_shuf))
            if t < t_ask: bar(im, frac)
            if cta_at <= t < cta_at + 3.0 and t < t_ask:
                dd = ImageDraw.Draw(im); dd.rounded_rectangle([170, 600, 910, 700], radius=50, fill=(239, 68, 68))
                dd.text((W / 2, 650), "SUBSCRIBE & LIKE", font=F(56), fill=WHITE, anchor="mm")
            if t >= t_ask:
                dd = ImageDraw.Draw(im)
                for k in range(3):
                    win = t >= t_rev and k == final_slot
                    dd.text((SLOTS[k], BY - 175), str(k + 1), font=F(150 if win else 110), fill=YELLOW if win else WHITE,
                            anchor="mm", stroke_width=7, stroke_fill=DEEP)
                if t < t_rev:
                    dd.text((W / 2, 640), "Where is the yellow ball?", font=F(64), fill=YELLOW, anchor="mm", stroke_width=6, stroke_fill=DEEP)
                    dd.text((W / 2, 1300), "Comment 1, 2 or 3!", font=F(60), fill=WHITE, anchor="mm", stroke_width=6, stroke_fill=DEEP)
                    if t >= t_ask + 1.2:
                        n = max(1, T_count - int(t - t_ask - 1.2)); r = 85
                        dd.ellipse([W / 2 - r, 1480 - r, W / 2 + r, 1480 + r], fill=WHITE)
                        dd.text((W / 2, 1480), str(n), font=F(110), fill=DEEP, anchor="mm")
                elif t < t_out:
                    dd.text((W / 2, 640), f"It was number {final_slot + 1}!", font=F(76), fill=YELLOW, anchor="mm", stroke_width=6, stroke_fill=DEEP)
                    dd.text((W / 2, 1300), "Did you get it right?", font=F(60), fill=WHITE, anchor="mm", stroke_width=6, stroke_fill=DEEP)
                    if t - t_rev < 0.25:
                        im.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(80 * (1 - (t - t_rev) / 0.25)))))
        if t >= t_out:
                big(im, [("Comment your level!", 84, YELLOW), ("EASY • HARD • IMPOSSIBLE", 54, WHITE),
                         ("Subscribe for", 70, WHITE), ("LEVEL IMPOSSIBLE", 90, (239, 68, 68))], 1000)
        p.stdin.write(im.convert("RGB").tobytes())
    p.stdin.close(); p.wait(); os.remove(wav)
    print("done", round(total, 1), "s; answer =", final_slot + 1)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "hard", int(sys.argv[3]) if len(sys.argv) > 3 else 7)

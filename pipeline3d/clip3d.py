"""Turn 3D renders (park + Lina poses) into a short talking clip.

Usage: python3 clip3d.py RENDER_DIR OUT.mp4
Needs RENDER_DIR/bg_idle.png and char_{idle,talk,blink,wave}.png (from lina3d.py).
Lina's mouth moves while she talks, she blinks, waves and bounces; the camera
slowly pushes in. Voice, subtitles and music come from the 2D pipeline.
"""
import os
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
import art  # noqa: E402
import build  # noqa: E402

rd, out = sys.argv[1], sys.argv[2]
work = os.path.join(os.path.dirname(out), "work_3dclip")
os.makedirs(work, exist_ok=True)
voice = build.Voice(os.environ.get("MT_TTS_DIR", os.path.join(HERE, "..", "pipeline", "tts")))

LINES = [
    ("lina", "Hi, friends! I'm Lina!", "wave"),
    ("lina", "Welcome to Moon Tales Kids!", "talk"),
    ("lina", "Today we are in the park. Look at the big green trees!", "talk"),
    ("lina", "Can you say tree? Tree!", "talk"),
    ("lina", "Let's learn English together. Bye, bye!", "wave"),
]
t, pieces, spans = 0.8, [], []
for k, (who, text, mode) in enumerate(LINES):
    p = os.path.join(work, f"l{k}.wav")
    d = voice.say(text, who, p)
    pieces.append((t, p))
    spans.append((t, t + d, text, who, mode))
    t += d + 0.5
total = t + 0.8
buf = np.zeros(int(total * build.SR) + 1, dtype=np.float32)
for st, p in pieces:
    a, _ = sf.read(p, dtype="float32")
    s = int(st * build.SR)
    buf[s:s + len(a)] += a[: len(buf) - s]
vpath = os.path.join(work, "voice.wav")
sf.write(vpath, buf, build.SR)
mpath = os.path.join(work, "music.wav")
build.music(total, mpath, seed=12)

talk = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b, _, _, m in spans if m == "talk") or "0"
wave = "+".join(f"between(t,{a - 0.3:.2f},{b + 0.3:.2f})" for a, b, _, _, m in spans if m == "wave") or "0"
mouth_open = f"({talk})*lt(mod(t,0.26),0.13)"
blink = "lt(mod(t+0.7,3.2),0.13)"
# which pose is visible (exactly one at a time)
show_wave = f"gt({wave},0)"
show_talk = f"(1-gt({wave},0))*gt({mouth_open},0)"
show_blink = f"(1-gt({wave},0))*(1-gt({mouth_open},0))*{blink}"
show_idle = f"(1-gt({wave},0))*(1-gt({mouth_open},0))*(1-{blink})"

inputs = []


def img(path):
    inputs.extend(["-loop", "1", "-framerate", "30", "-t", f"{total:.2f}", "-i", path])
    return len(inputs) // 8 - 1


bg = img(os.path.join(rd, "bg_idle.png"))
poses = {p: img(os.path.join(rd, f"char_{p}.png")) for p in ("idle", "talk", "blink", "wave")}
subs = []
for k, (a, b, text, who, _) in enumerate(spans):
    im = art.subtitle(text, who)
    sp = os.path.join(work, f"sub{k}.png")
    im.save(sp)
    subs.append((img(sp), a, b, im.width, im.height))
n_voice = len(inputs) // 8
fc = [
    f"[{bg}:v]scale=2112:1188,crop=1920:1080:x='96-60*t/{total:.2f}':y='54-30*t/{total:.2f}',setsar=1[b0]",
]
cur = "b0"
y = "30-10*abs(sin(2*PI*t*0.9))"
for name, cond in (("idle", show_idle), ("talk", show_talk), ("blink", show_blink), ("wave", show_wave)):
    fc.append(f"[{poses[name]}:v]scale=1920:1080[c_{name}]")
    fc.append(f"[{cur}][c_{name}]overlay=x=0:y='{y}':eval=frame:enable='{cond}'[o_{name}]")
    cur = f"o_{name}"
for k, (idx, a, b, w, h) in enumerate(subs):
    fc.append(f"[{cur}][{idx}:v]overlay=x={(1920 - w) // 2}:y={1045 - h}:enable='between(t,{a - 0.1:.2f},{b + 0.4:.2f})'[s{k}]")
    cur = f"s{k}"
fc.append(f"[{cur}]fade=t=in:st=0:d=0.4,fade=t=out:st={total - 0.5:.2f}:d=0.5,format=yuv420p[v]")
fc.append(f"[{n_voice + 1}:a]volume=0.16[m];[{n_voice}:a][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]")
fpath = os.path.join(work, "filter.txt")
open(fpath, "w").write(";\n".join(fc))
build.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-i", vpath, "-i", mpath,
           "-filter_complex_script", fpath, "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-r", "30",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out])
print(f"done: {out} ({total:.0f} s)")

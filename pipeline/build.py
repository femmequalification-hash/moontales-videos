"""Build a Moon Tales Kids video from a story JSON file.

Usage:  python3 build.py stories/<slug>.json OUT_DIR
Needs:  ffmpeg, kokoro-onnx, soundfile, numpy, Pillow, and the voice model
        files in $MT_TTS_DIR (kokoro.onnx, voices.bin) — see setup.sh.
Output: OUT_DIR/<slug>.mp4, OUT_DIR/<slug>_thumb.jpg, OUT_DIR/<slug>_meta.json
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art  # noqa: E402

SR = 24000
FPS = 30
VOICES = {  # who -> (kokoro voice, pitch factor, speed)
    "narrator": ("af_heart", 1.0, 0.88),
    "lina": ("af_sky", 1.14, 0.95),
    "adams": ("am_puck", 1.24, 0.95),
    "milo": ("af_nicole", 1.2, 1.0),
}
GAP = 0.45


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-3000:])
        raise SystemExit("ffmpeg failed: " + " ".join(cmd[:6]))


class Voice:
    def __init__(self, tts_dir):
        from kokoro_onnx import Kokoro
        self.k = Kokoro(os.path.join(tts_dir, "kokoro.onnx"), os.path.join(tts_dir, "voices.bin"))

    def say(self, text, who, path):
        v, pitch, speed = VOICES.get(who, VOICES["narrator"])
        audio, sr = self.k.create(text, voice=v, speed=speed, lang="en-us")
        audio = np.asarray(audio, dtype=np.float32)
        if pitch != 1.0:
            tmp = path + ".raw.wav"
            sf.write(tmp, audio, sr)
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-af",
                 f"asetrate={sr}*{pitch},aresample={SR},atempo={1/pitch:.5f}", path])
            os.remove(tmp)
            audio, sr = sf.read(path, dtype="float32")
        else:
            if sr != SR:
                raise SystemExit("unexpected sample rate")
            sf.write(path, audio, SR)
        return len(audio) / SR


def music(seconds, path, seed=4):
    """Gentle music-box loop (C major pentatonic), generated, royalty-free."""
    rng = np.random.default_rng(seed)
    sr = 44100
    n = int(seconds * sr) + sr
    out = np.zeros(n, dtype=np.float32)
    beat = 60 / 84
    scale = [60, 62, 64, 67, 69, 72, 74, 76]
    chords = [[48, 55, 64], [45, 52, 60], [41, 48, 57], [43, 50, 59]]

    def tone(midi, dur, amp, decay):
        f = 440 * 2 ** ((midi - 69) / 12)
        t = np.arange(int(dur * sr)) / sr
        env = np.exp(-t * decay) * np.minimum(1, t * 200)
        return amp * env * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) + 0.08 * np.sin(6 * np.pi * f * t))

    melody = [scale[i] for i in rng.integers(0, len(scale), 16)]
    t, k = 0.0, 0
    while t < seconds:
        bar = int(t / (beat * 4))
        if abs(t - bar * beat * 4) < 1e-6:
            for m in chords[bar % 4]:
                s = tone(m, beat * 4.2, 0.06, 0.9)
                i = int(t * sr)
                out[i:i + len(s)] += s[: max(0, n - i)]
        m = melody[k % 16]
        if (k % 8) not in (3, 7):
            s = tone(m + 12, beat * 1.6, 0.11, 2.6)
            i = int(t * sr)
            out[i:i + len(s)] += s[: max(0, n - i)]
        t += beat / 2 if (k % 4) in (1, 2) else beat
        k += 1
    out = out / max(1e-6, np.max(np.abs(out))) * 0.6
    fade = int(3 * sr)
    out[int(seconds * sr) - fade:int(seconds * sr)] *= np.linspace(1, 0, fade)
    out[int(seconds * sr):] = 0
    st = np.stack([out, np.roll(out, 300)], axis=1)
    sf.write(path, st[: int(seconds * sr)], sr)


def char_positions(chars):
    kids = [c for c in chars if c != "milo"]
    xs = {1: [810], 2: [560, 960], 3: [440, 820, 1200]}[max(1, min(3, len(kids)))]
    pos = {c: x for c, x in zip(kids, xs)}
    if "milo" in chars:
        pos["milo"] = (xs[-1] + 420) if kids else 800
    return pos


def render_segment(i, seg, work, voice, title_img=None, recap_words=None):
    """Render one segment (scene) to an mp4 clip. Returns path."""
    d = os.path.join(work, f"s{i:02d}")
    os.makedirs(d, exist_ok=True)
    # --- audio
    t = 0.6
    timeline = []
    pieces = []
    for j, ln in enumerate(seg["lines"]):
        if "pause" in ln:
            t += float(ln["pause"])
            continue
        who = ln.get("who", "narrator")
        p = os.path.join(d, f"l{j:02d}.wav")
        dur = voice.say(ln["text"], who, p)
        timeline.append((t, t + dur, ln["text"], who))
        pieces.append((t, p))
        t += dur + GAP
    total = t + 0.8
    buf = np.zeros(int(total * SR) + 1, dtype=np.float32)
    for start, p in pieces:
        a, _ = sf.read(p, dtype="float32")
        s = int(start * SR)
        buf[s:s + len(a)] += a[: len(buf) - s]
    apath = os.path.join(d, "audio.wav")
    sf.write(apath, buf, SR)

    # --- images
    inputs, filters = [], []

    def add_img(im, name):
        p = os.path.join(d, name)
        im.save(p)
        inputs.extend(["-loop", "1", "-framerate", str(FPS), "-t", f"{total:.3f}", "-i", p])
        return len(inputs) // 8 - 1  # each image input uses 8 args

    setting = seg.get("setting", "park")
    time_ = seg.get("time", "day")
    weather = seg.get("weather", "sunny")
    if title_img is not None:
        bg = title_img.resize((art.BW, art.BH))
    elif recap_words is not None:
        bg = recap_board(recap_words, seg)
    else:
        bg = art.background(setting, time_, weather, seg.get("props", []), seed=i * 7 + 1)
    n_bg = add_img(bg, "bg.png")
    direction = 1 if i % 2 == 0 else -1
    filters.append(f"[{n_bg}:v]crop=1920:1080:x='96+{direction}*(70*t/{total:.3f}-35)':y=54,setsar=1[v0]")
    cur = "v0"
    k = 0

    def over(src, x, y, enable=None):
        nonlocal cur, k
        k += 1
        en = f":enable='{enable}'" if enable else ""
        filters.append(f"[{cur}][{src}:v]overlay=x='{x}':y='{y}':eval=frame{en}[v{k}]")
        cur = f"v{k}"

    outdoor = setting not in ("kitchen", "bedroom", "classroom") and title_img is None and recap_words is None
    if outdoor and time_ != "night" and weather != "rain":
        n = add_img(art.cloud_layer(seed=i), "clouds.png")
        over(n, f"-mod(t*22+{i * 300},1920)", "0")
    chars = seg.get("chars", []) if title_img is None else []
    pos = char_positions(chars)
    for ci, name in enumerate(chars):
        im = art.CHARACTERS[name]()
        sc = 0.88 if name != "milo" else 0.85
        im = im.resize((int(im.width * sc), int(im.height * sc)))
        n = add_img(im, f"c_{name}.png")
        talk = [(a, b) for a, b, _, w in timeline if w == name]
        talk_expr = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in talk) or "0"
        base_y = 885 - im.height
        y = f"{base_y}-4*sin(2*PI*t*0.7+{ci * 1.7})-14*abs(sin(2*PI*t*1.7))*({talk_expr})"
        over(n, str(pos[name] - im.width // 2 + 160), y)
    if outdoor and weather in ("rain", "snow", "windy"):
        layer = art.weather_layer(weather, seed=i)
        n = add_img(layer, "weather.png")
        if weather == "rain":
            over(n, "0", "mod(t*700,1080)-1080")
        elif weather == "snow":
            over(n, "0", "mod(t*110,1080)-1080")
        else:
            over(n, "-mod(t*280,1920)", "0")
    if seg.get("word"):
        n = add_img(art.word_card(seg["word"]), "word.png")
        over(n, "60", "60")
    for j, (a, b, text, who) in enumerate(timeline):
        sub = art.subtitle(text, who, seg.get("word"))
        n = add_img(sub, f"sub{j:02d}.png")
        over(n, str((1920 - sub.width) // 2), str(1045 - sub.height), f"between(t,{a - 0.1:.2f},{b + GAP:.2f})")
    filters.append(f"[{cur}]fade=t=in:st=0:d=0.35,fade=t=out:st={total - 0.35:.3f}:d=0.35,format=yuv420p[vout]")
    n_audio = len(inputs) // 8
    out = os.path.join(work, f"seg{i:02d}.mp4")
    fc = os.path.join(d, "filter.txt")
    with open(fc, "w") as f:
        f.write(";\n".join(filters))
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-i", apath,
         "-filter_complex_script", fc, "-map", "[vout]", "-map", f"{n_audio}:a",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS),
         "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
         "-t", f"{total:.3f}", out])
    return out, total


def recap_board(words, seg):
    c = art.Canvas(art.BW, art.BH)
    art.sky(c, "night", "sunny")
    art.stars(c, 90, 5)
    art.moon(c, 1880, 200, 80)
    c.text(art.BW / 2, 190, seg.get("heading", "Our new words!"), art.font(96, "Bold"),
           art.hexc("#FFE680"), anchor="mm", stroke=6, stroke_fill=art.hexc("#2B2350"))
    cols = 3 if len(words) > 4 else 2
    for idx, w in enumerate(words):
        card = art.word_card(w)
        r, cc = divmod(idx, cols)
        row_n = min(cols, len(words) - r * cols)
        x = art.BW / 2 - (row_n * 560) / 2 + cc * 560 + (560 - card.width) / 2
        y = 330 + r * 260
        c.paste(card, x, y)
    return c.final()


def main():
    story_path, out_dir = sys.argv[1], sys.argv[2]
    tts_dir = os.environ.get("MT_TTS_DIR", os.path.join(os.path.dirname(__file__), "tts"))
    story = json.load(open(story_path))
    slug = story["slug"]
    work = os.path.join(out_dir, "work_" + slug)
    os.makedirs(work, exist_ok=True)
    voice = Voice(tts_dir)

    segs = []
    intro = {"lines": story.get("intro") or [
        {"text": "Hello, friends! Welcome to Moon Tales Kids!"},
        {"text": f"Today's story is called: {story['story_title']}."},
        {"text": "Let's listen, and learn some new English words together!"},
        {"text": "Are you ready? Let's go!"},
    ]}
    segs.append(("title", intro))
    for sc in story["scenes"]:
        segs.append(("scene", sc))
    words = [s["word"] for s in story["scenes"] if s.get("word")]
    seen = []
    for w in words:
        if w not in seen:
            seen.append(w)
    if seen:
        lines = [{"text": "Great job, friends! Let's say our new words one more time."}]
        for w in seen:
            lines += [{"text": f"{w.capitalize()}."}, {"pause": 1.8}]
        lines.append({"text": "Wonderful! You learned " + ("so many" if len(seen) > 3 else str(len(seen))) + " new words today!"})
        segs.append(("recap", {"lines": lines}))
    segs.append(("scene", story.get("outro") or {
        "setting": "park", "time": "night", "weather": "sunny", "chars": ["lina", "adams"],
        "lines": [{"text": "Thank you for watching Moon Tales Kids!"},
                  {"text": "If you liked this story, ask a grown-up to subscribe. A new story is coming soon!"},
                  {"who": "lina", "text": "Bye, bye, friends!"},
                  {"who": "adams", "text": "See you next time!"}]}))

    title_img = art.title_card(story["story_title"], story.get("lesson", "Learn English with stories!"))
    clips, total = [], 0.0
    for i, (kind, seg) in enumerate(segs):
        print(f"segment {i + 1}/{len(segs)} ({kind})", flush=True)
        clip, dur = render_segment(i, seg, work, voice,
                                   title_img=title_img if kind == "title" else None,
                                   recap_words=seen if kind == "recap" else None)
        clips.append(clip)
        total += dur
    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as f:
        f.write("".join(f"file '{c}'\n" for c in clips))
    joined = os.path.join(work, "joined.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
    mpath = os.path.join(work, "music.wav")
    music(total, mpath)
    final = os.path.join(out_dir, slug + ".mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", joined, "-i", mpath, "-filter_complex",
         "[1:a]volume=0.16[m];[0:a][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", final])
    first = story["scenes"][0]
    thumb_scene = story.get("thumbnail_scene", first)
    art.thumbnail(story.get("thumbnail_title", story["story_title"]), story.get("thumbnail_word", seen[0] if seen else "English"),
                  thumb_scene.get("setting", "park"), thumb_scene.get("time", "day"),
                  thumb_scene.get("weather", "sunny"), thumb_scene.get("props", []),
                  [c for c in thumb_scene.get("chars", ["lina", "adams"]) if c != "milo"] or ["lina", "adams"]
                  ).save(os.path.join(out_dir, slug + "_thumb.jpg"), quality=92)
    meta = {k: story[k] for k in ("title", "description", "tags") if k in story}
    meta["duration_seconds"] = round(total, 1)
    json.dump(meta, open(os.path.join(out_dir, slug + "_meta.json"), "w"), ensure_ascii=False, indent=2)
    print(f"done: {final} ({total / 60:.1f} min)")


if __name__ == "__main__":
    main()

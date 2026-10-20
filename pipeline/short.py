"""Make a vertical "Word of the day" YouTube Short (2–3 new words, 45–58 s) from a built story.

Usage:  python3 short.py stories/<slug>.json OUT_DIR
Needs the story to be built first (uses OUT_DIR/work_<slug>/segNN.mp4).
Output: OUT_DIR/<slug>_short.mp4 (1080x1920, under 60 s) and
        OUT_DIR/<slug>_short_meta.json (title, description, tags).

Layout: big "Word of the day" header + word on top, the story scene in the
middle, "Full story on Moon Tales Kids" at the bottom. Background is a blurred,
zoomed copy of the scene. Background music comes from the story's music.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art  # noqa: E402

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-3000:])
        raise SystemExit("ffmpeg failed")


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True).stdout
    return float(out.strip())


def overlay_png(word, path):
    W, H = 1080, 1920
    c = art.Canvas(W, H)
    # top band
    c.rect(40, 90, W - 40, 560, art.hexc("#FFFFFF", 240), r=60)
    c.rect(40, 90, W - 40, 560, None, r=60, outline=art.hexc("#FFB020"), width=12)
    c.text(W / 2, 190, "Word of the day", art.font(72, "SemiBold"), art.hexc("#7A6A9A"), anchor="mm")
    size = 190 if len(word) <= 7 else (150 if len(word) <= 10 else 115)
    c.text(W / 2, 380, word, art.font(size, "Bold"), art.hexc("#FF7A30"), anchor="mm")
    art.moon(c, W - 130, 150, 34)
    # bottom band
    c.rect(70, 1460, W - 70, 1760, art.hexc("#2B2350", 235), r=60)
    c.text(W / 2, 1555, "Full story on", art.font(64, "Medium"), art.hexc("#FFFFFF"), anchor="mm")
    c.text(W / 2, 1660, "Moon Tales Kids", art.font(86, "Bold"), art.hexc("#FFE680"), anchor="mm")
    c.final().save(path)


def main():
    story_path, out_dir = sys.argv[1], sys.argv[2]
    story = json.load(open(story_path))
    slug = story["slug"]
    work = os.path.join(out_dir, "work_" + slug)
    scenes = story["scenes"]
    # segment numbering in build.py: 0 = title, scene k = segment k + 1
    parts = []  # (segment path, word, duration)
    total = 0.0
    for i, sc in enumerate(scenes):
        if not sc.get("word"):
            continue
        seg = os.path.join(work, f"seg{i + 1:02d}.mp4")
        if not os.path.exists(seg):
            raise SystemExit("build the story first: missing " + seg)
        d = dur(seg)
        if parts and total + d > 58.5 and total >= 40:
            break
        parts.append((seg, sc["word"], d))
        total += d
        if total >= 45 or len(parts) == 3:
            break
    total = min(total, 58.5)
    inputs, fc, t = [], [], 0.0
    for k, (seg, w, d) in enumerate(parts):
        inputs += ["-i", seg]
    n = len(parts)
    fc.append("".join(f"[{k}:v][{k}:a]" for k in range(n)) + f"concat=n={n}:v=1:a=1[cv][ca]")
    fc.append("[cv]split=2[a][b]")
    fc.append("[a]scale=-2:1920,crop=1080:1920,boxblur=30:3,eq=brightness=0.06[bg]")
    fc.append("[b]scale=1080:-2[fg]")
    fc.append("[bg][fg]overlay=0:(H-h)/2-40[m0]")
    cur = "m0"
    for k, (seg, w, d) in enumerate(parts):
        ov = os.path.join(work, f"short_overlay{k}.png")
        overlay_png(w, ov)
        inputs += ["-loop", "1", "-framerate", "30", "-t", f"{total:.2f}", "-i", ov]
        fc.append(f"[{cur}][{n + k}:v]overlay=0:0:enable='between(t,{t:.2f},{t + d:.2f})'[m{k + 1}]")
        cur = f"m{k + 1}"
        t += d
    inputs += ["-i", os.path.join(work, "music.wav")]
    fc.append(f"[{cur}]format=yuv420p[v]")
    fc.append(f"[{2 * n}:a]volume=0.12,atrim=0:{total:.2f}[mu]")
    fc.append("[ca][mu]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[au]")
    out = os.path.join(out_dir, slug + "_short.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc),
         "-map", "[v]", "-map", "[au]", "-t", f"{total:.2f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-r", "30",
         "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out])
    words = [w for _, w, _ in parts]
    d = total
    word = words[0]

    # translations from the description lines "emoji word — ar — fr"
    tr = {}
    for line in story.get("description", "").splitlines():
        p = [x.strip() for x in line.split("—")]
        if len(p) >= 3 and p[0].split():
            tr[p[0].split()[-1].lower()] = (p[1], p[2])
    nice = ", ".join(words[:-1]) + " and " + words[-1] if len(words) > 1 else words[0]
    title = f"Learn {len(words)} English words: {nice} 🌙 English for kids #shorts"
    if len(title) > 100:
        title = f"English words for kids: {nice} #shorts"[:100]
    lines = [f"New English words: {nice}!"]
    for w in words:
        if w.lower() in tr:
            lines.append(f"• {w} — {tr[w.lower()][0]} — {tr[w.lower()][1]}")
    desc = ("\n".join(lines)
            + f"\n\nFrom the story \"{story['story_title']}\". Watch the full story on Moon Tales Kids! 🌙"
            + "\n\n#shorts #EnglishForKids #LearnEnglish #MoonTalesKids")
    tags = [f"{w} in english" for w in words] + [
        "english words for kids", "english for kids", "learn english", "kids shorts", "Moon Tales Kids",
        "Lina and Adams", "كلمات انجليزية للاطفال", "تعلم الانجليزية", "mots anglais enfant", "apprendre l'anglais"]
    json.dump({"title": title, "description": desc, "tags": tags, "words": words,
               "duration_seconds": round(d, 1)},
              open(os.path.join(out_dir, slug + "_short_meta.json"), "w"), ensure_ascii=False, indent=2)
    print(f"short done: {out} ({d:.0f} s, words: {words})")


if __name__ == "__main__":
    main()

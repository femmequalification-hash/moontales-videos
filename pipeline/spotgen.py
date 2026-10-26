"""Generate Spot the Difference packs with the channel's own drawings.

Usage: python3 spotgen.py OUT_IMG_DIR SLUG SEED LEVELS(e.g. 0001112233) > spotpacks/SLUG.json
Each puzzle: a scene with 9-10 objects placed on clear background, and 5 edits whose
strength depends on the level (Easy = big obvious changes, Impossible = small subtle ones).
"""
import json
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art  # noqa: E402
from spotscene import OUT_W, OUT_H  # noqa: E402

S = OUT_W / art.BW
SKY = ["balloon", "bird", "butterfly", "kite", "star", "heart"]
GROUND = ["ball", "dog", "gift", "bike", "apple", "orange", "banana", "flower", "hat", "shoes", "umbrella", "cake",
          "book", "sandwich", "carrot", "cup"]
FLIP_OK = {"dog", "bird", "bike", "kite", "umbrella", "banana", "car", "boat", "apple", "orange", "cup"}
NO_COLOR = {"cup", "book"}
SCENES = {
    "park": {"sky": (120, 1950, 120, 560), "ground": (120, 2000, 900, 1120)},
    "garden": {"sky": (120, 1400, 120, 560), "ground": (120, 2000, 950, 1120)},
    "forest": {"sky": (120, 1950, 90, 330), "ground": (120, 2000, 950, 1120)},
    "beach": {"sky": (120, 1950, 120, 520), "ground": (120, 2000, 960, 1120), "sea": (150, 1950, 700, 820)},
    "street": {"sky": (680, 1400, 120, 560), "ground": (120, 2000, 960, 1100)},
    "kitchen": {"wall": (760, 1440, 150, 640), "counter": (1560, 2050, 330, 370), "ground": (150, 1400, 900, 1110)},
    "bedroom": {"wall": (820, 1450, 150, 640), "ground": (480, 1300, 960, 1110)},
    "classroom": {"wall": (80, 520, 150, 700), "ground": (120, 2000, 920, 1110)},
}
ZONE_PROPS = {"sky": SKY, "wall": ["star", "heart", "balloon", "butterfly"], "sea": ["boat"],
              "counter": ["cup", "apple", "orange", "banana", "book"], "ground": GROUND}
_off = {}


def offsets(name):
    """Bounding box of a prop relative to its centre (background coords), computed once."""
    if name not in _off:
        c = art.Canvas(art.BW, art.BH)
        art.prop(c, name, 1056, 594)
        b = c.final().getbbox()
        _off[name] = (b[0] - 1056, b[1] - 594, b[2] - 1056, b[3] - 594)
    return _off[name]


def box_out(name, x, y, pad=10):
    o = offsets(name)
    return [int((x + o[0]) * S) - pad, int((y + o[1]) * S) - pad, int((x + o[2]) * S) + pad, int((y + o[3]) * S) + pad]


def overlap(a, b, m=22):
    return not (a[2] + m < b[0] or b[2] + m < a[0] or a[3] + m < b[1] or b[3] + m < a[1])


def inside(b):
    return b[0] > 8 and b[1] > 8 and b[2] < OUT_W - 8 and b[3] < OUT_H - 8


def calm(bg, b, lim):
    a = bg[max(b[1], 0):b[3], max(b[0], 0):b[2]]
    return a.size and a.reshape(-1, 3).std(axis=0).mean() < lim


def make_puzzle(rng, level, img_path):
    setting = rng.choice(list(SCENES))
    time = rng.choice(["day", "day", "sunset"] + (["night"] if level >= 2 else []))
    weather = "snow" if (setting in ("park", "forest", "garden") and rng.random() < 0.2) else rng.choice(["sunny", "cloudy"])
    if setting in ("kitchen", "bedroom", "classroom"):
        weather = "sunny"
    seed = rng.randint(1, 999)
    bgimg = art.background(setting, time, weather, [], seed=seed).convert("RGB").resize((OUT_W, OUT_H))
    bg = np.asarray(bgimg).astype(np.float32)
    zones = SCENES[setting]
    props, boxes = [], []
    want = rng.randint(9, 11)
    tries = 0
    while len(props) < want and tries < 4000:
        tries += 1
        zname = rng.choice(list(zones))
        if zname == "ground" and rng.random() < 0.35 and len([p for p in props if p["zone"] == "ground"]) > 4:
            continue
        x0, x1, y0, y1 = zones[zname]
        name = rng.choice(ZONE_PROPS[zname])
        if name == "star" and time != "night" and zname == "sky":
            continue
        used = [p["name"] for p in props]
        if used.count(name) >= 1 and rng.random() < 0.8:
            continue
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        b = box_out(name, x, y)
        if not inside(b) or any(overlap(b, o) for o in boxes):
            continue
        if zname in ("sky", "wall") and not calm(bg, b, 22):
            continue
        props.append({"name": name, "x": round(x), "y": round(y), "zone": zname})
        boxes.append(b)
    img = art.background(setting, time, weather, [{"name": p["name"], "x": p["x"], "y": p["y"]} for p in props],
                         seed=seed).convert("RGB").resize((OUT_W, OUT_H))
    img.save(img_path)
    # choose 5 edits: each one is applied and measured, so every difference is really visible
    from spotdiff import apply_edit
    work = img.copy()
    order = sorted(range(len(props)), key=lambda i: -((boxes[i][2] - boxes[i][0]) * (boxes[i][3] - boxes[i][1])))
    if level >= 2:  # prefer small objects for hard levels
        order = order[::-1]
    pool = order[:]
    rng.shuffle(pool)
    hue = {0: (130, 200), 1: (100, 160), 2: (60, 95), 3: (38, 55)}[level]
    grow = {0: 1.55, 1: 1.4, 2: 1.27, 3: 1.18}[level]
    need = {0: 14, 1: 11, 2: 8, 3: 6}[level]  # minimum visible change (mean pixel difference in the box)
    kinds = {0: ["remove", "recolor", "copy", "scale", "remove"], 1: ["remove", "recolor", "copy", "flip", "scale"],
             2: ["recolor", "flip", "scale", "remove", "copy"], 3: ["recolor", "flip", "scale", "remove", "recolor"]}[level]
    flip_ok = FLIP_OK - ({"apple", "orange", "cup"} if level < 2 else set())
    edits, taken, circles = [], set(), []
    for slot, pref in enumerate(kinds):
        done = False
        for kind in [pref] + [k for k in ("recolor", "copy", "scale", "remove", "flip") if k != pref]:
            for i in pool:
                if i in taken:
                    continue
                p, b = props[i], boxes[i]
                if kind == "flip" and p["name"] not in flip_ok:
                    continue
                if kind == "recolor" and p["name"] in NO_COLOR:
                    continue
                if kind in ("remove", "flip") and not calm(bg, b, 26):
                    continue
                e = {"type": kind, "box": b}
                cb = b
                if kind == "recolor":
                    e["hue"] = rng.randint(*hue) * rng.choice([1, -1])
                elif kind == "scale":
                    e["factor"] = grow
                    w, h = b[2] - b[0], b[3] - b[1]
                    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
                    cb = [int(cx - w * grow / 2), int(cy - h * grow / 2), int(cx + w * grow / 2), int(cy + h * grow / 2)]
                    if not inside(cb) or any(overlap(cb, boxes[j], 4) for j in range(len(boxes)) if j != i):
                        continue
                elif kind == "copy":
                    w, h = b[2] - b[0], b[3] - b[1]
                    z = zones.get(p["zone"])
                    ok = False
                    for _ in range(300):
                        tx = rng.uniform(z[0] * S, z[1] * S - w)
                        ty = rng.uniform(z[2] * S - h / 2, z[3] * S - h / 2)
                        cb = [int(tx), int(ty), int(tx + w), int(ty + h)]
                        if inside(cb) and not any(overlap(cb, o) for o in boxes) and \
                                not any(overlap(cb, c, 30) for c in circles) and calm(bg, cb, 26):
                            ok = True
                            break
                    if not ok:
                        continue
                    e["to"] = [cb[0], cb[1]]
                if any(overlap(cb, c, 30) for c in circles):
                    continue
                trial = work.copy()
                apply_edit(trial, e)
                diff = np.abs(np.asarray(trial, np.float32) - np.asarray(work, np.float32))
                reg = diff[max(cb[1], 0):cb[3], max(cb[0], 0):cb[2]]
                if reg.size == 0 or reg.mean() < need:
                    continue
                work = trial
                edits.append(e)
                circles.append(cb)
                taken.add(i)
                done = True
                break
            if done:
                break
    return {"image": img_path, "level": level, "edits": edits, "scene": f"{setting}/{time}/{weather}"}


if __name__ == "__main__":
    out_dir, slug, seed, levels = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    os.makedirs(out_dir, exist_ok=True)
    rng = random.Random(seed)
    puzzles = []
    for k, lv in enumerate(levels):
        for attempt in range(12):
            pz = make_puzzle(rng, int(lv), os.path.join(out_dir, f"{slug}_p{k + 1:02d}.png"))
            if len(pz["edits"]) == 5:
                break
        assert len(pz["edits"]) == 5, f"puzzle {k + 1}: only {len(pz['edits'])} edits"
        puzzles.append(pz)
        print(f"puzzle {k + 1}: level {lv} {pz['scene']}", [e["type"] for e in pz["edits"]], file=sys.stderr)
    json.dump({"puzzles": puzzles}, sys.stdout, indent=1)

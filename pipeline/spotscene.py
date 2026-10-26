"""Draw a spot-the-difference scene with the channel's art and return exact object boxes.

make_scene(setting, props, ...) -> (PIL image, {name: [x0, y0, x1, y1]}) in output pixels.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art  # noqa: E402

OUT_W, OUT_H = 1792, 1008


def bbox_of(name, x, y, time):
    c = art.Canvas(art.BW, art.BH)
    art.prop(c, name, x, y, time=time)
    return c.final().getbbox()


def make_scene(setting, props, time="day", weather="sunny", seed=1, pad=10):
    img = art.background(setting, time, weather, props, seed=seed).convert("RGB").resize((OUT_W, OUT_H))
    s = OUT_W / art.BW
    boxes = {}
    for p in props:
        b = bbox_of(p["name"], p["x"], p["y"], time)
        boxes[p.get("id", p["name"])] = [int(b[0] * s) - pad, int(b[1] * s) - pad, int(b[2] * s) + pad, int(b[3] * s) + pad]
    return img, boxes

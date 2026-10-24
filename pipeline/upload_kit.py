"""Write a ready-to-paste text file (title, description, tags) next to each video.

Usage: python3 upload_kit.py OUT_DIR NAME [NAME...]
NAME is a video file name without .mp4 (e.g. toy-box, toy-box_short2).
Reads NAME_meta.json, or for long story videos stories/<NAME>.json.
Writes OUT_DIR/NAME.txt.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
out_dir = sys.argv[1]
for name in sys.argv[2:]:
    meta_path = os.path.join(out_dir, name + "_meta.json")
    story_path = os.path.join(HERE, "stories", name + ".json")
    m = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    if os.path.exists(story_path):
        s = json.load(open(story_path))
        m = {"title": s["title"], "description": s["description"], "tags": s["tags"]}
    is_short = "_short" in name
    text = (
        f"=== {'YOUTUBE SHORT' if is_short else 'YOUTUBE VIDEO'}: {name}.mp4 ===\n\n"
        f"TITLE:\n{m['title']}\n\n"
        f"DESCRIPTION:\n{m['description']}\n\n"
        f"TAGS (paste in the Tags box):\n{', '.join(m['tags'])}\n\n"
        "SETTINGS:\n- Audience: Yes, it's made for kids\n- Altered or synthetic content: Yes\n"
        "- Category: Education\n- Visibility: Public\n"
        + ("" if is_short else f"- Thumbnail: {name}_thumb.jpg\n")
    )
    open(os.path.join(out_dir, name + ".txt"), "w").write(text)
    print("wrote", name + ".txt")

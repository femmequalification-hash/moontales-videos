"""QuizNado "Easy to Impossible" run helpers (every 3 days, Zahra publishes by hand).

Based on her YouTube Studio numbers (Oct 2026): English tests (plurals, spelling, common
mistakes, mental math, opposites, past tense) and Spot the Difference keep viewers best;
general knowledge, capitals, IQ, synonyms, vocabulary and "level" quizzes do not.

  python3 pack_tools.py next                 -> today's theme, new slug/title number, example pack to copy
  python3 pack_tools.py check PACK.json      -> validates a quiz pack (structure, NEW questions, tags, rainbow)
  python3 pack_tools.py spotmeta RAW.json SLUG NUMBER -> adds titles/tags/shorts to a spotgen.py output
  python3 pack_tools.py fiche SLUG OUT       -> OUT/<date>_QuizNado_fiche.txt (all kits + publishing plan)
  python3 pack_tools.py done SLUG THEME      -> records the run in packs_history.json
"""
import datetime
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.join(os.path.dirname(HERE), "pipeline")
PACKS = os.path.join(PIPE, "quizpacks")
SPOTS = os.path.join(PIPE, "spotpacks")
HIST = os.path.join(HERE, "packs_history.json")

# rotation order = best first; base = slug prefix of existing packs of that theme
THEMES = [
    {"theme": "Plurals Test", "base": "plurals"},
    {"theme": "Spot the Difference", "base": "spot-the-difference", "spot": True},
    {"theme": "Spelling Test", "base": "spelling-test"},
    {"theme": "Common English Mistakes", "base": "mistakes"},
    {"theme": "Mental Math Test", "base": "mental-math"},
    {"theme": "Opposites Test", "base": "opposites"},
    {"theme": "Past Tense Test", "base": "past-tense"},
]
BANNED = ("general knowledge", "capital", "iq test", "synonym", "vocabulary", "level")


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def hist():
    return json.load(open(HIST)) if os.path.exists(HIST) else {"runs": []}


def existing(base, spot=False):
    folder, suf = (SPOTS, "") if spot else (PACKS, "-easy-impossible")
    out = []
    for f in glob.glob(os.path.join(folder, "*.json")):
        s = os.path.basename(f)[:-5]
        if s == base + suf or re.fullmatch(re.escape(base) + r"-\d+" + re.escape(suf), s):
            out.append(f)
    return sorted(out, key=lambda f: int((re.findall(r"-(\d+)", os.path.basename(f)) or ["1"])[-1]))


def cmd_next():
    h = hist()["runs"]
    last = h[-1]["theme"] if h else None
    used = [r["theme"] for r in h]
    cands = [t for t in THEMES if t["theme"] != last]
    t = sorted(cands, key=lambda t: (used.count(t["theme"]), THEMES.index(t)))[0]
    ex = existing(t["base"], t.get("spot"))
    n = len(ex) + 1
    while True:  # first free number
        slug = f"{t['base']}-{n}" + ("" if t.get("spot") else "-easy-impossible")
        if not os.path.exists(os.path.join(SPOTS if t.get("spot") else PACKS, slug + ".json")):
            break
        n += 1
    print(json.dumps({"date": datetime.date.today().isoformat(), "theme": t["theme"], "number": n,
                      "slug": slug, "spot_the_difference": bool(t.get("spot")),
                      "copy_style_from": os.path.relpath(ex[-1], os.path.dirname(HERE)) if ex else None},
                     ensure_ascii=False, indent=1))


def qkey(pack, item):
    shown, opts, ans = item[0], item[1], item[2]
    if pack.get("spoken_cycle") or len({norm(i[0]) for lv in pack["levels"] for i in lv}) < 8:
        return "a|" + norm(ans) + "|" + "|".join(sorted(norm(o) for o in opts))
    return "q|" + norm(shown) + "|" + norm(ans)


def used_keys(skip):
    keys = {}
    for f in glob.glob(os.path.join(PACKS, "*.json")):
        if os.path.abspath(f) == os.path.abspath(skip):
            continue
        p = json.load(open(f))
        for lv in p["levels"]:
            for it in lv:
                keys[qkey(p, it)] = os.path.basename(f)
                keys["s|" + norm(it[0]) + "|" + norm(it[2])] = os.path.basename(f)
    return keys


def cmd_check(path):
    p = json.load(open(path))
    errs = []
    for f in ("slug", "name", "header", "noun", "title", "about", "thumb", "ar", "fr", "hashtags", "tags", "levels",
              "shorts"):
        if f not in p:
            errs.append(f"missing field {f}")
    if errs:
        print("\n".join(errs)); sys.exit(1)
    if os.path.basename(path)[:-5] != p["slug"]:
        errs.append("file name must be <slug>.json")
    if any(b in norm(p["name"]) for b in BANNED):
        errs.append("theme not allowed (weak on the channel)")
    lv = p["levels"]
    if len(lv) != 4 or any(len(l) != 8 for l in lv):
        errs.append("needs 4 levels x 8 questions")
    used = used_keys(path)
    seen = set()
    for li, l in enumerate(lv):
        for qi, it in enumerate(l):
            w = f"L{li + 1}Q{qi + 1}"
            if not (4 <= len(it) <= 5):
                errs.append(f"{w}: item must be [shown, options, answer, why, (spoken)]"); continue
            shown, opts, ans, why = it[:4]
            if len(opts) != 3 or len({norm(o) for o in opts}) != 3:
                errs.append(f"{w}: needs 3 different options")
            if opts.count(ans) != 1:
                errs.append(f"{w}: answer must be exactly one of the options")
            if len(shown) > 60 or any(len(o) > 26 for o in opts) or len(why) > 60:
                errs.append(f"{w}: too long (question ≤ 60, options ≤ 26, why ≤ 60 chars)")
            for k in (qkey(p, it), "s|" + norm(shown) + "|" + norm(ans)):
                if k in used:
                    errs.append(f"{w}: already used in {used[k]}: {shown} -> {ans}")
                    break
            if qkey(p, it) in seen:
                errs.append(f"{w}: repeated in this pack: {shown}")
            seen.add(qkey(p, it))
    sh = p["shorts"]
    if len(sh) != 2:
        errs.append("needs exactly 2 shorts")
    picks = [tuple(x) for s in sh for x in s.get("picks", [])]
    for s in sh:
        if [x[0] for x in s.get("picks", [])] != [0, 1, 2, 3]:
            errs.append("each short needs 4 picks, one per level in order [0,i],[1,i],[2,i],[3,i]")
        if not s.get("title", "").endswith("#shorts") or len(s["title"]) > 100:
            errs.append(f"short title must end with #shorts and be ≤ 100 chars: {s.get('title')}")
    if len(set(picks)) != len(picks):
        errs.append("the 2 shorts must use different questions")
    if any(x[1] > 7 for x in picks):
        errs.append("pick index must be 0-7")
    if (3, 7) in picks:
        errs.append("do not use [3,7] in a Short: it is the long video's teaser question")
    if len(p["title"]) > 100:
        errs.append("title > 100 chars")
    tags = ["QuizNado"] + p["tags"]
    if len(", ".join(dict.fromkeys(tags))) > 450:
        errs.append("tags too long (< 450 chars)")
    if not any(re.search(r"[؀-ۿ]", t) for t in p["tags"]):
        errs.append("tags need Arabic")
    if not any(re.search(r"anglais|français|enfant|jeu|test d'|quiz anglais|orthographe|différence", t) for t in p["tags"]):
        errs.append("tags need French")
    if "rainbow" in json.dumps(p).lower():
        errs.append("no rainbow allowed")
    print("OK" if not errs else "\n".join(errs))
    sys.exit(1 if errs else 0)


def cmd_spotmeta(raw, slug, number):
    d = json.load(open(raw))
    n = int(number)
    d.update({
        "slug": slug, "name": "Spot the Difference",
        "title": f"Spot the Difference {n}: Easy to Impossible 🔎 10 New Puzzles | Find All 50 Differences!",
        "about": "10 NEW spot the difference puzzles, from easy to impossible! Find the 5 differences between the two pictures.",
        "thumb_top": f"SPOT THE DIFFERENCE {n}", "thumb_bottom": "10 PUZZLES · EASY TO IMPOSSIBLE",
        "ar": "ابحث عن الاختلافات الخمسة بين الصورتين — من السهل إلى المستحيل!",
        "fr": "Trouve les 5 différences entre les deux images — du plus facile à l'impossible !",
        "hashtags": "#SpotTheDifference #FindTheDifference #Puzzle #BrainGames",
        "tags": ["spot the difference", "find the difference", "spot 5 differences", "picture puzzle", "brain games",
                 "visual puzzle", "easy to impossible", f"spot the difference {n}", "QuizNado", "ابحث عن الاختلاف",
                 "أوجد الفرق", "ألغاز الصور", "trouve les différences", "jeu des 7 erreurs", "jeu des différences"],
        "shorts": [{"puzzle": 1, "title": f"Can You Find 5 Differences? 👀 Spot the Difference {n} #shorts"},
                   {"puzzle": 7, "title": "Only Geniuses Find All 5 Differences 🤯 #shorts"}],
    })
    if "rainbow" in json.dumps(d).lower():
        print("no rainbow allowed"); sys.exit(1)
    out = os.path.join(SPOTS, slug + ".json")
    json.dump(d, open(out, "w"), ensure_ascii=False, indent=1)
    print(out)


def cmd_fiche(slug, out):
    date = datetime.date.today()
    names = [slug, slug + "_short1", slug + "_short2"]
    days = [date + datetime.timedelta(days=i) for i in range(3)]
    parts = [f"QUIZNADO — {date.isoformat()} — publish by hand on YouTube at 20:00 (Morocco time)", "=" * 60,
             "PLAN (one post per day):"]
    for nm, dd, what in zip(names, days, ["Long video + thumbnail", "Short 1", "Short 2"]):
        parts.append(f"  {dd.strftime('%a %d %b')} 20:00 — {what}: {nm}.mp4")
    parts.append("=" * 60)
    for nm in names:
        p = os.path.join(out, nm + ".txt")
        parts.append(open(p).read() if os.path.exists(p) else f"(missing kit {nm}.txt)")
        parts.append("=" * 60)
    pf = os.path.join(out, f"{date.isoformat()}_QuizNado_fiche.txt")
    open(pf, "w").write("\n".join(parts) + "\n")
    print(pf)


def cmd_done(slug, theme):
    h = hist()
    h["runs"].append({"date": datetime.date.today().isoformat(), "theme": theme, "slug": slug})
    json.dump(h, open(HIST, "w"), ensure_ascii=False, indent=1)
    print("recorded", slug)


if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    {"next": cmd_next, "check": cmd_check, "spotmeta": cmd_spotmeta, "fiche": cmd_fiche, "done": cmd_done}[c](*a)

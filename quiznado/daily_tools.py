"""QuizNado daily helpers.
  python3 daily_tools.py next                 -> prints next number, today's date, rounds topics, short topics
  python3 daily_tools.py check days/DATE.json -> validates the day file (structure, repeats, lengths)
  python3 daily_tools.py fiche days/DATE.json OUT -> writes OUT/DATE_QuizNado_fiche.txt
  python3 daily_tools.py done days/DATE.json  -> adds the day's questions to history.json
"""
import json, os, sys, re, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
HIST = os.path.join(HERE, "history.json")
QPR = 7  # questions per round in the long video (7 x 7 = 49 -> ~12 min)
ROUNDS = ["General Knowledge", "IQ Test", "English Test", "Math Speed", "Riddles", "Science Quiz", "Capitals Quiz"]
SHORT_TOPICS = ["Brain Teasers", "Which Is Bigger", "Animals Quiz", "Odd One Out", "Spelling Test", "Food Quiz",
                "Space Quiz", "Human Body Quiz", "Football Quiz", "Synonyms Test", "History Quiz", "Inventions Quiz",
                "Opposites Test", "World Records Quiz", "Missing Number", "Countries Quiz", "Past Tense Test",
                "Logic Puzzles", "Geography Quiz", "Phrasal Verbs"] + ROUNDS
COMMON_TAGS = ("quiz, quiz time, trivia, general knowledge quiz, brain test, QuizNado, اختبار, أسئلة وأجوبة, "
               "ثقافة عامة, تحدي, اختبر نفسك, quiz culture générale, devinettes, questions réponses")

def norm(q): return re.sub(r"[^a-z0-9]+", " ", q.lower()).strip()
def qkey(q): return norm(q["q"] + " | " + " ".join(sorted(q.get("options", []))))
def hist():
    return json.load(open(HIST)) if os.path.exists(HIST) else {"last_number": 1, "days": [], "questions": []}

def cmd_next():
    h = hist(); n = h["last_number"] + 1
    used = [t for d in h["days"] for t in d.get("short_topics", [])]
    order = sorted(SHORT_TOPICS, key=lambda t: (used.count(t), SHORT_TOPICS.index(t)))
    print(json.dumps({"number": n, "date": datetime.date.today().isoformat(), "long_rounds": ROUNDS,
                      "suggested_short_topics": order[:2], "questions_already_used": len(h["questions"])}, ensure_ascii=False, indent=1))

def cmd_check(path):
    d = json.load(open(path)); h = hist(); used = set(h["questions"]); errs = []
    seen = set()
    def chk_q(q, where):
        if not isinstance(q.get("q"), str) or len(q["q"]) > 95: errs.append(f"{where}: question missing or > 95 chars")
        if len(q.get("options", [])) != 3: errs.append(f"{where}: needs exactly 3 options")
        elif any(len(o) > 26 for o in q["options"]): errs.append(f"{where}: option > 26 chars")
        if q.get("answer") not in (0, 1, 2): errs.append(f"{where}: answer must be 0, 1 or 2")
        k = qkey(q)
        if k in used: errs.append(f"{where}: question already used on an earlier day: {q['q']}")
        if k in seen: errs.append(f"{where}: question repeated today: {q['q']}")
        seen.add(k)
    if d.get("number") != h["last_number"] + 1: errs.append(f"number should be {h['last_number'] + 1}")
    rounds = d.get("long", {}).get("rounds", [])
    if [r.get("topic") for r in rounds] != ROUNDS: errs.append(f"long.rounds topics must be exactly {ROUNDS}")
    for r in rounds:
        if len(r.get("questions", [])) != QPR: errs.append(f"round {r.get('topic')}: needs {QPR} questions")
        for i, q in enumerate(r.get("questions", [])): chk_q(q, f"long/{r.get('topic')}/{i + 1}")
    if len(d.get("shorts", [])) != 2: errs.append("needs exactly 2 shorts")
    for s in d.get("shorts", []):
        for f in ("id", "topic", "hook", "title", "first_line", "extra_tags"):
            if not s.get(f): errs.append(f"short {s.get('id')}: missing {f}")
        if len(s.get("questions", [])) != 5: errs.append(f"short {s.get('id')}: needs 5 questions")
        for i, q in enumerate(s.get("questions", [])): chk_q(q, f"short/{s.get('id')}/{i + 1}")
        if len(s.get("hook", "")) > 34: errs.append(f"short {s.get('id')}: hook > 34 chars")
        if not re.fullmatch(r"[a-z0-9_]+", s.get("id", "")): errs.append(f"short id must be a-z0-9_: {s.get('id')}")
    L = d.get("long", {})
    for f in ("title", "extra_tags"):
        if not L.get(f): errs.append(f"long: missing {f}")
    for t in [L.get("title", "")] + [s.get("title", "") for s in d.get("shorts", [])]:
        if len(t) > 100: errs.append(f"title > 100 chars: {t}")
    for tags in [L.get("extra_tags", "")] + [s.get("extra_tags", "") for s in d.get("shorts", [])]:
        if len(COMMON_TAGS + ", " + tags) > 480: errs.append("tags too long (keep extra_tags short)")
    if "rainbow" in json.dumps(d).lower(): errs.append("no rainbow allowed")
    print("OK" if not errs else "\n".join(errs)); sys.exit(1 if errs else 0)

def desc_short(s):
    return (f"{s['first_line']}\n\n👇 Comment your score! How many did you get right?\n\n"
            "🔔 Subscribe to QuizNado on YouTube for new quizzes every week: general knowledge, IQ tests, English tests, riddles and more!\n\n"
            "اشترك في قناة QuizNado على يوتيوب لتحصل على اختبارات جديدة كل أسبوع 🧠\nAbonne-toi à la chaîne YouTube QuizNado pour de nouveaux quiz chaque semaine !\n\n"
            "#quiz #trivia #QuizNado #shorts")

def desc_long(d):
    rounds = "\n".join(f"{i + 1}️⃣ {t}" for i, t in enumerate(ROUNDS))
    nq = sum(len(r["questions"]) for r in d["long"]["rounds"])
    return (f"Ultimate Quiz #{d['number']}: {nq} brand-new questions in 7 rounds! 🧠\n"
            "Grab a pen, count your points and see if you can beat them all.\n\n"
            f"7 rounds:\n{rounds}\n\n👇 Comment your score out of {nq}!\nPlay it with your family and friends. Who gets the highest score?\n\n"
            "🔔 Subscribe to QuizNado on YouTube for new challenges every week!\n\n"
            f"اختبر نفسك في {nq} سؤالاً جديداً: ثقافة عامة، ذكاء، إنجليزية، رياضيات، ألغاز، علوم وعواصم 🧠\n"
            "اكتب نتيجتك في التعليقات واشترك في QuizNado!\n\n"
            f"{nq} nouvelles questions pour tester ta culture générale, ton QI et ton anglais !\n"
            "Écris ton score en commentaire et abonne-toi à QuizNado !\n\n#quiz #trivia #iqtest #generalknowledge #QuizNado")

def cmd_fiche(path, out):
    d = json.load(open(path)); date = d["date"]; n = d["number"]; L = d["long"]
    parts = [f"QUIZNADO — {date} — publish everything at 20:00 (Morocco time)\n", "=" * 60]
    parts += [f"\n1) LONG VIDEO: {date}_QuizNado_Ultimate_Quiz_{n}.mp4", f"   Thumbnail: {date}_QuizNado_Ultimate_Quiz_{n}_thumbnail.jpg",
              "\nTITLE:", L["title"], "\nDESCRIPTION:", desc_long(d), "\nTAGS:", COMMON_TAGS + ", " + L["extra_tags"], "\n" + "=" * 60]
    for i, s in enumerate(d["shorts"], 1):
        parts += [f"\n{i + 1}) SHORT {i}: {date}_Short_{i}_{s['id']}.mp4", "\nTITLE:", s["title"], "\nDESCRIPTION:", desc_short(s),
                  "\nTAGS:", COMMON_TAGS + ", shorts quiz, " + s["extra_tags"], "\n" + "=" * 60]
    parts += ["\nPIN THIS COMMENT ON EACH VIDEO:", "Comment your score! 👇 Which question got you? 🧠", "",
              "ANSWER KEY (long video):"]
    for r in L["rounds"]:
        parts.append(f"  {r['topic']}: " + " | ".join(f"{q['q']} → {'ABC'[q['answer']]}) {q['options'][q['answer']]}" for q in r["questions"]))
    os.makedirs(out, exist_ok=True)
    p = os.path.join(out, f"{date}_QuizNado_fiche.txt"); open(p, "w").write("\n".join(parts) + "\n"); print(p)

def cmd_done(path):
    d = json.load(open(path)); h = hist()
    qs = [q for r in d["long"]["rounds"] for q in r["questions"]] + [q for s in d["shorts"] for q in s["questions"]]
    h["questions"] += [qkey(q) for q in qs]
    h["days"].append({"date": d["date"], "number": d["number"], "short_topics": [s["topic"] for s in d["shorts"]]})
    h["last_number"] = d["number"]
    json.dump(h, open(HIST, "w"), ensure_ascii=False, indent=0); print("history updated:", d["number"])

if __name__ == "__main__":
    c = sys.argv[1]
    if c == "next": cmd_next()
    elif c == "check": cmd_check(sys.argv[2])
    elif c == "fiche": cmd_fiche(sys.argv[2], sys.argv[3])
    elif c == "done": cmd_done(sys.argv[2])

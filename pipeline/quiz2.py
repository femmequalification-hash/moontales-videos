"""Level quizzes (Beginner / Intermediate / Advanced) + "bonus question" Shorts.

Usage:  python3 quiz2.py OUT_DIR levels   -> quiz-beginner.mp4, quiz-intermediate.mp4, quiz-advanced.mp4
        python3 quiz2.py OUT_DIR shorts   -> quiz-bonus1..10.mp4
Each Short: 3 questions with answers, then a BONUS question whose answer is only in
one of the long level quizzes ("find the answer on the channel"). Every video ends
with "Want more? Subscribe to get a new quiz every week!".
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import quiz  # noqa: E402
from quiz import Q, Timeline, frame, title_frame  # noqa: E402

SUB_LINE = "Want more? Subscribe to get a new quiz every week!"

LEVEL_QUIZ = {
    "beginner": ("Beginner", "A1–A2", [
        ("Grammar", [
            ("I ___ a student.", ["am", "is", "are"], "am", "Use am with I."),
            ("They ___ from Morocco.", ["is", "are", "am"], "are", "Use are with they."),
            ("He ___ football every Sunday.", ["play", "plays", "playing"], "plays", "He, she, it: add -s."),
            ("___ you like tea?", ["Do", "Does", "Are"], "Do", "Questions with you use do."),
            ("This is ___ apple.", ["a", "an", "the"], "an", "Use an before a vowel sound."),
        ]),
        ("Vocabulary", [
            ("Which one is a fruit?", ["carrot", "banana", "bread"], "banana", "A banana is a fruit."),
            ("The opposite of big is...", ["small", "tall", "long"], "small", "Big and small are opposites."),
            ("Monday, Tuesday, ___", ["Thursday", "Wednesday", "Friday"], "Wednesday", "Wednesday comes after Tuesday."),
            ("Which one is a color?", ["purple", "chair", "happy"], "purple", "Purple is a color."),
            ("You sleep in a...", ["bed", "kitchen", "car"], "bed", "We sleep in a bed."),
        ]),
        ("Spelling", [
            ("Which word is spelled correctly?", ["freind", "friend", "frend"], "friend", "I before E: friend."),
            ("Which word is spelled correctly?", ["beautiful", "beutiful", "beautifull"], "beautiful", "B-E-A-U-tiful, one L at the end."),
            ("Which word is spelled correctly?", ["tomorow", "tommorow", "tomorrow"], "tomorrow", "One M, double R."),
            ("Which word is spelled correctly?", ["famly", "family", "familly"], "family", "F-A-M-I-L-Y."),
            ("Which word is spelled correctly?", ["cofee", "coffee", "coffe"], "coffee", "Double F, double E."),
        ]),
        ("Everyday English", [
            ("\"Nice to meet you!\" You answer...", ["Nice to meet you too!", "I'm fine.", "Goodbye!"], "Nice to meet you too!", "Repeat it back with too."),
            ("\"How old are you?\" You answer...", ["I'm 20 years old.", "I'm fine.", "I'm from Rabat."], "I'm 20 years old.", "We say I'm ... years old."),
            ("\"What time is it?\" You answer...", ["It's 5 o'clock.", "It's Monday.", "It's hot."], "It's 5 o'clock.", "Time: It's ... o'clock."),
            ("\"Thank you!\" You answer...", ["You're welcome!", "Yes, please!", "Excuse me!"], "You're welcome!", "The polite answer to thank you."),
            ("\"Can I help you?\" You answer...", ["Yes, please.", "Yes, thanks you.", "I am help."], "Yes, please.", "Thanks you is a common mistake!"),
        ]),
    ]),
    "intermediate": ("Intermediate", "B1", [
        ("Grammar", [
            ("She has worked here ___ five years.", ["since", "for", "during"], "for", "Use for with a length of time."),
            ("If I have time, I ___ call you.", ["will", "would", "am"], "will", "First conditional: if + present, will."),
            ("We ___ TV when the lights went out.", ["were watching", "watched", "are watching"], "were watching", "Past continuous: an action in progress."),
            ("This book is ___ than that one.", ["more interesting", "interestinger", "most interesting"], "more interesting", "Long adjectives: more + adjective."),
            ("You ___ smoke here. It's not allowed.", ["mustn't", "don't have to", "needn't"], "mustn't", "Mustn't = it is not allowed."),
        ]),
        ("Vocabulary", [
            ("A person who fixes cars is a...", ["mechanic", "doctor", "pilot"], "mechanic", "A mechanic repairs cars."),
            ("Which word means the same as begin?", ["start", "finish", "stop"], "start", "Begin and start are synonyms."),
            ("The opposite of cheap is...", ["expensive", "poor", "small"], "expensive", "Cheap and expensive are opposites."),
            ("I'm very ___ in history.", ["interested", "interesting", "interest"], "interested", "-ed for feelings, -ing for things."),
            ("___ a mistake", ["do", "make", "take"], "make", "We make a mistake, never do."),
        ]),
        ("Spelling", [
            ("Which word is spelled correctly?", ["necessary", "neccessary", "necesary"], "necessary", "One C, double S."),
            ("Which word is spelled correctly?", ["business", "buisness", "bussiness"], "business", "B-U-S-I-ness."),
            ("Which word is spelled correctly?", ["separate", "seperate", "separete"], "separate", "There is A RAT in separate!"),
            ("Which word is spelled correctly?", ["address", "adress", "addres"], "address", "Double D, double S."),
            ("Which word is spelled correctly?", ["government", "goverment", "govenment"], "government", "Don't forget the N: govern-ment."),
        ]),
        ("Phrasal verbs", [
            ("\"Look after\" means...", ["take care of", "search for", "look behind"], "take care of", "I look after my little brother."),
            ("\"Find out\" means...", ["discover", "lose", "go outside"], "discover", "Find out = learn new information."),
            ("\"Turn down the music\" means...", ["make it quieter", "turn it off", "change it"], "make it quieter", "Turn down = lower the volume."),
            ("\"Get up\" means...", ["get out of bed", "sit down", "go to sleep"], "get out of bed", "I get up at 7 every morning."),
            ("\"We ran out of milk\" means...", ["we have no more milk", "we bought milk", "we spilled milk"], "we have no more milk", "Run out of = have none left."),
        ]),
    ]),
    "advanced": ("Advanced", "B2–C1", [
        ("Grammar", [
            ("I wish I ___ more time.", ["had", "have", "will have"], "had", "Wish + past simple for the present."),
            ("Had I known, I ___ have come.", ["would", "will", "should to"], "would", "Inverted third conditional."),
            ("Not only ___ late, he also forgot the tickets.", ["was he", "he was", "he is"], "was he", "Not only at the start: invert."),
            ("The report ___ by Friday.", ["must be finished", "must finish", "must finishing"], "must be finished", "Passive: must be + past participle."),
            ("She suggested that he ___ a doctor.", ["see", "seeing", "to see"], "see", "Suggest that + base verb."),
        ]),
        ("Vocabulary", [
            ("Which word means the same as huge?", ["enormous", "tiny", "narrow"], "enormous", "Huge = enormous = very big."),
            ("\"Reluctant\" means...", ["not wanting to do it", "very happy", "very late"], "not wanting to do it", "He was reluctant to leave."),
            ("\"Ubiquitous\" means...", ["found everywhere", "very rare", "very old"], "found everywhere", "Phones are ubiquitous today."),
            ("\"To postpone\" means...", ["to delay", "to cancel", "to prepare"], "to delay", "Postpone = move to a later time."),
            ("\"Meticulous\" means...", ["very careful", "very fast", "very lazy"], "very careful", "Meticulous = paying attention to every detail."),
        ]),
        ("Spelling", [
            ("Which word is spelled correctly?", ["embarrass", "embarass", "embbarass"], "embarrass", "Double R, double S."),
            ("Which word is spelled correctly?", ["occurrence", "occurence", "ocurrence"], "occurrence", "Double C, double R."),
            ("Which word is spelled correctly?", ["millennium", "millenium", "milennium"], "millennium", "Double L, double N."),
            ("Which word is spelled correctly?", ["conscience", "concience", "consciense"], "conscience", "Con-SCIENCE."),
            ("Which word is spelled correctly?", ["entrepreneur", "entrepeneur", "entreprenuer"], "entrepreneur", "Entre-PRE-neur."),
        ]),
        ("Idioms", [
            ("\"Once in a blue moon\" means...", ["very rarely", "at night", "every month"], "very rarely", "It happens once in a blue moon = almost never."),
            ("\"It cost an arm and a leg\" means...", ["very expensive", "very painful", "very dangerous"], "very expensive", "It cost a lot of money."),
            ("\"Let the cat out of the bag\" means...", ["reveal a secret", "lose a pet", "make a mess"], "reveal a secret", "Tell something that was a secret."),
            ("\"Bite off more than you can chew\" means...", ["take on too much", "eat too fast", "be rude"], "take on too much", "Try to do more than you can manage."),
            ("\"The ball is in your court\" means...", ["it's your decision now", "you lost", "let's play"], "it's your decision now", "Now it's your turn to act."),
        ]),
    ]),
}
NEXT = {"beginner": "Intermediate", "intermediate": "Advanced", "advanced": None}

# Shorts: (header, hook, 3 questions, bonus key, bonus video name, title)
SHORTS = [
    ("Plurals", "Can you make these plurals? The last one is a bonus!", [
        ("One mouse, two...", ["mouses", "mice", "meese"], "mice", "Mouse becomes mice!"),
        ("One tooth, two...", ["tooths", "teeth", "teethes"], "teeth", "Tooth becomes teeth!"),
        ("One woman, two...", ["womans", "women", "womens"], "women", "Woman becomes women!")],
     ("beginner", 1, 5), "Can You Make These English Plurals? 🤔 + Bonus Question #shorts"),
    ("Past tense", "Irregular verbs! Most people get the second one wrong.", [
        ("Teach in the past is...", ["teached", "taught", "thought"], "taught", "Teach, taught, taught."),
        ("Catch in the past is...", ["catched", "caught", "cought"], "caught", "Catch, caught, caught."),
        ("Think in the past is...", ["thinked", "thought", "taught"], "thought", "Think, thought, thought.")],
     ("intermediate", 2, 5), "Most People Get These Past Tenses Wrong 😳 #shorts"),
    ("Opposites", "Find the opposite. Only real English experts get all three!", [
        ("The opposite of brave is...", ["cowardly", "strong", "angry"], "cowardly", "Brave and cowardly are opposites."),
        ("The opposite of ancient is...", ["modern", "old", "broken"], "modern", "Ancient = very old. Modern = new."),
        ("The opposite of generous is...", ["selfish", "kind", "rich"], "selfish", "Generous people share; selfish people don't.")],
     ("advanced", 4, 1), "Only English Experts Know These Opposites 🧠 #shorts"),
    ("Silent letters", "Every word has a silent letter. Can you find it?", [
        ("Which letter is silent in KNIFE?", ["K", "N", "F"], "K", "We say 'naif'. The K is silent!"),
        ("Which letter is silent in WRITE?", ["W", "R", "T"], "W", "We say 'rait'. The W is silent!"),
        ("Which letter is silent in ISLAND?", ["S", "L", "D"], "S", "We say 'ai-land'. The S is silent!")],
     ("advanced", 3, 3), "Find the Silent Letter 🤫 99% Miss the Last One #shorts"),
    ("Odd one out", "Which word does not belong? Think fast!", [
        ("Which one is different?", ["apple", "banana", "carrot", "mango"], "carrot", "A carrot is a vegetable, not a fruit."),
        ("Which one is different?", ["doctor", "nurse", "teacher", "hospital"], "hospital", "A hospital is a place, not a job."),
        ("Which one is different?", ["run", "jump", "quickly", "swim"], "quickly", "Quickly is an adverb, not a verb.")],
     ("intermediate", 4, 1), "Find the Odd One Out 🧐 English Brain Test #shorts"),
    ("Prepositions", "In, on or at? This one confuses everybody!", [
        ("I was born ___ 1999.", ["in", "on", "at"], "in", "Use in with years and months."),
        ("We meet ___ Monday.", ["in", "on", "at"], "on", "Use on with days and dates."),
        ("The meeting is ___ 3 pm.", ["in", "on", "at"], "at", "Use at with clock times.")],
     ("beginner", 1, 3), "IN, ON or AT? This Confuses Everybody 😵 #shorts"),
    ("Which is correct?", "Common mistakes! Which sentence is correct?", [
        ("Which one is correct?", ["I am agree.", "I agree.", "I am agreeing."], "I agree.", "Agree is a verb: I agree."),
        ("Which one is correct?", ["He don't like it.", "He doesn't like it.", "He not like it."], "He doesn't like it.", "He, she, it: doesn't."),
        ("Which one is correct?", ["I have 25 years.", "I am 25 years old.", "I have 25 years old."], "I am 25 years old.", "In English, you ARE an age.")],
     ("advanced", 1, 1), "Stop Making These 3 English Mistakes ❌ #shorts"),
    ("UK vs US", "British or American English? Find the American word!", [
        ("Lift (UK) = ___ (US)", ["elevator", "escalator", "stairs"], "elevator", "Lift in the UK, elevator in the US."),
        ("Flat (UK) = ___ (US)", ["apartment", "house", "floor"], "apartment", "Flat in the UK, apartment in the US."),
        ("Biscuit (UK) = ___ (US)", ["cookie", "cracker", "cake"], "cookie", "Biscuit in the UK, cookie in the US.")],
     ("intermediate", 4, 5), "British vs American English 🇬🇧🇺🇸 Can You Match Them? #shorts"),
    ("Synonyms", "Find the word with the same meaning. Ready?", [
        ("Same meaning as happy?", ["glad", "sad", "angry"], "glad", "Happy = glad."),
        ("Same meaning as smart?", ["clever", "slow", "funny"], "clever", "Smart = clever."),
        ("Same meaning as quick?", ["fast", "late", "easy"], "fast", "Quick = fast.")],
     ("advanced", 2, 3), "Find the Synonym 🔁 English Vocabulary Test #shorts"),
    ("English riddles", "Three English riddles. Can you solve them?", [
        ("What has keys but can't open locks?", ["a piano", "a car", "a door"], "a piano", "A piano has keys!"),
        ("What gets wetter the more it dries?", ["a towel", "the sun", "water"], "a towel", "A towel gets wet when it dries you!"),
        ("What has a neck but no head?", ["a bottle", "a snake", "a giraffe"], "a bottle", "A bottle has a neck!")],
     ("advanced", 1, 2), "3 English Riddles 🧩 Can You Solve Them? #shorts"),
]


def register():
    for lk, (_, _, rounds) in LEVEL_QUIZ.items():
        for ri, (_, qs) in enumerate(rounds, 1):
            for qi, (shown, opts, ans, why) in enumerate(qs, 1):
                Q[f"{lk}_{ri}_{qi}"] = ("text", shown, shown.replace("___", ", blank,"), opts, ans, why)
    for si, (_, _, qs, _, _) in enumerate(SHORTS, 1):
        for qi, (shown, opts, ans, why) in enumerate(qs, 1):
            Q[f"bs{si}_{qi}"] = ("text", shown, shown.replace("___", ", blank,"), opts, ans, why)


register()


def build_level(out_dir, voice, lk):
    name, cefr, rounds = LEVEL_QUIZ[lk]
    slug = f"quiz-{lk}"
    work = os.path.join(out_dir, "work_" + slug)
    os.makedirs(work, exist_ok=True)
    tl = Timeline(work, voice)
    nq = sum(len(r[1]) for r in rounds)
    tf = lambda lines, big: title_frame(lines, False, big, chars=False)  # noqa: E731
    intro = tf([f"{nq} questions  ·  4 rounds  ·  5 seconds each", "Can you get a perfect score?"],
               f"{name} English Quiz ({cefr})")
    for text in (f"Welcome to the {name} English Quiz! {nq} questions in four rounds.",
                 "You have five seconds for each question. Keep your score, and share it in the comments at the end!",
                 "Ready? Let's go!"):
        d = tl.say(text)
        tl.show(intro, d + 0.3)
    footers = ["Keep your score! Share it in the comments at the end",
               "Round 2... how many do you have so far?",
               "Halfway! Don't stop now",
               "Last round! Your result is at the end"]
    num = 0
    for ri, (rname, qs) in enumerate(rounds, 1):
        d = tl.say(f"Round {ri}: {rname}!")
        tl.show(tf([f"{len(qs)} questions"], f"Round {ri}: {rname}"), d + 0.6)
        for qi in range(1, len(qs) + 1):
            num += 1
            tl.question(f"{lk}_{ri}_{qi}", False, f"{name} · {rname}", num, nq, answer_voice="narrator",
                        footer=footers[ri - 1])
    nxt = NEXT[lk]
    lines = [f"{nq - 2}–{nq}: Excellent!", f"{nq - 7}–{nq - 3}: Very good", f"0–{nq - 8}: Keep practising!",
             "Share your score in the comments!"]
    res = tf(lines, "Your score?")
    for text in (f"Finished! What's your score? {nq - 2} or more out of {nq} is excellent!",
                 "Share your score with us in the comments!"):
        d = tl.say(text)
        tl.show(res, d + 0.6)
    end_lines = ([f"Next: try the {nxt} Quiz", "on our channel!"] if nxt else
                 ["You finished the hardest quiz!", "Try our other quizzes on the channel"]) + [SUB_LINE]
    end = tf(end_lines, "Want more?")
    nxt_say = (f"Too easy? Try our {nxt} English Quiz on the channel!" if nxt else
               "Congratulations, this was our hardest quiz!")
    for text in (nxt_say, "Want more? Subscribe to get a new quiz every week. See you next time!"):
        d = tl.say(text)
        tl.show(end, d + 0.8)
    out = os.path.join(out_dir, slug + ".mp4")
    tl.render(out, music_vol=0.06)
    # thumbnail
    import art
    H = art.hexc
    col = {"beginner": "#2FA84F", "intermediate": "#F2A31B", "advanced": "#E84A4A"}[lk]
    c = art.Canvas(1280, 720)
    c.rect(0, 0, 1280, 720, H("#2B2350"))
    c.rect(60, 60, 620, 210, H(col), r=40)
    c.text(340, 135, name.upper(), art.font(84, "Bold"), H("#FFFFFF"), anchor="mm")
    c.text(340, 300, "ENGLISH", art.font(120, "Bold"), H("#FFFFFF"), anchor="mm")
    c.text(340, 430, "QUIZ", art.font(150, "Bold"), H("#FFE680"), anchor="mm", stroke=6, stroke_fill=H("#000000"))
    c.text(340, 590, f"{nq} questions · {cefr}", art.font(54, "SemiBold"), H("#CFC6E8"), anchor="mm")
    c.rect(720, 140, 1220, 580, H("#FFFFFF"), r=50)
    c.text(970, 300, "?/" + str(nq), art.font(170, "Bold"), H(col), anchor="mm")
    c.text(970, 470, "Can you get", art.font(56, "Bold"), H("#2B2350"), anchor="mm")
    c.text(970, 530, "a perfect score?", art.font(56, "Bold"), H("#2B2350"), anchor="mm")
    c.final().convert("RGB").save(os.path.join(out_dir, slug + "_thumb.jpg"), quality=92)
    rlist = "\n".join(f"{i}️⃣ {r[0]}" for i, r in enumerate(rounds, 1))
    meta = {
        "title": f"{name} English Quiz ({cefr}) 🧠 {nq} Questions | Can You Get {nq}/{nq}?",
        "description": (
            f"Test your English with our {name} Quiz ({cefr})! 🧠\n"
            f"{nq} questions in 4 rounds, 5 seconds per question. Keep your score!\n\n"
            f"📚 Rounds:\n{rlist}\n\n"
            "💬 Share your score in the comments! Example: 18/20 🎉\n"
            + (f"➡️ Too easy? Try our {nxt} English Quiz on the channel!\n" if nxt else
               "🏆 This is our hardest quiz! Try the Beginner and Intermediate quizzes too.\n") +
            "🔔 Want more? Subscribe to get a new quiz every week!\n\n"
            "🇲🇦 اختبر مستواك في اللغة الإنجليزية — شارك نتيجتك في التعليقات!\n"
            "🇫🇷 Teste ton niveau d'anglais — partage ton score en commentaire !\n\n"
            "#EnglishQuiz #EnglishTest #LearnEnglish #EnglishGrammar"),
        "tags": [f"{lk} english quiz", "english quiz", "english test", f"english test {cefr}", "english grammar quiz",
                 "english vocabulary test", "learn english", "ielts", "اختبار اللغة الانجليزية",
                 "مسابقة انجليزية", "تعلم الانجليزية", "quiz anglais", "test d'anglais", "niveau d'anglais"],
    }
    json.dump(meta, open(os.path.join(out_dir, slug + "_meta.json"), "w"), ensure_ascii=False, indent=2)
    print(f"done: {out} ({tl.t / 60:.1f} min)")


def build_shorts(out_dir, voice, only=None):
    for si, (head, hook, qs, (blk, bri, bqi), title) in enumerate(SHORTS, 1):
        if only and si not in only:
            continue
        work = os.path.join(out_dir, f"work_quiz-bonus{si}")
        os.makedirs(work, exist_ok=True)
        tl = Timeline(work, voice)
        bname = LEVEL_QUIZ[blk][0]
        hk = title_frame([head, "3 questions + 1 bonus"], True, "QUIZ!", chars=False)
        d = tl.say(hook)
        tl.show(hk, d + 0.3)
        for qi in range(1, len(qs) + 1):
            tl.question(f"bs{si}_{qi}", True, head, qi, 4, answer_voice="narrator")
        # bonus question: countdown, no answer
        key = f"{blk}_{bri}_{bqi}"
        spoken = quiz.ask(key)[0]
        d = tl.say("Bonus question! " + spoken)
        tl.show(frame(key, "ask", None, True, "BONUS!", 4, 4), d + 0.4)
        for s in range(quiz.THINK, 0, -1):
            tl.add_sound(quiz.TICK, tl.t)
            tl.show(frame(key, "ask", s, True, "BONUS!", 4, 4), 1.0)
        tease = title_frame(["The answer is in our", f"{bname} English Quiz", "on the channel!",
                             "Want more? Subscribe", "for a new quiz every week!"], True, "Answer?", chars=False)
        d = tl.say(f"Want the answer? Find it in our {bname} English Quiz on the channel! "
                   "And subscribe to get a new quiz every week!")
        tl.show(tease, d + 1.0)
        out = os.path.join(out_dir, f"quiz-bonus{si}.mp4")
        tl.render(out, music_vol=0.07, vertical=True)
        meta = {
            "title": title,
            "description": (f"{head}: 3 questions + 1 BONUS question! 🧠\n"
                            f"👀 The answer to the bonus question is in our {bname} English Quiz on the channel!\n"
                            "💬 Comment your score and your answer to the bonus!\n"
                            "🔔 Want more? Subscribe to get a new quiz every week!\n\n"
                            "🇲🇦 اختبر مستواك في اللغة الإنجليزية — جواب السؤال الإضافي في القناة!\n"
                            "🇫🇷 Teste ton anglais — la réponse du bonus est sur la chaîne !\n\n"
                            "#shorts #EnglishQuiz #LearnEnglish #EnglishTest"),
            "tags": ["english quiz", "english test", "quiz shorts", head.lower(), "learn english", "english grammar",
                     "english vocabulary", "مسابقة انجليزية", "اختبار انجليزي", "quiz anglais", "test d'anglais"],
        }
        json.dump(meta, open(os.path.join(out_dir, f"quiz-bonus{si}_meta.json"), "w"), ensure_ascii=False, indent=2)
        print(f"short {si}: {out} ({tl.t:.0f} s)")


if __name__ == "__main__":
    out_dir, what = sys.argv[1], sys.argv[2]
    tts = os.environ.get("MT_TTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts"))
    if what == "preview":
        from PIL import Image
        a = frame("bs5_1", "ask", 3, True, "Odd one out", 1, 4)
        b = frame("advanced_4_3", "reveal", None, False, "Advanced · Idioms", 18, 20, "Last round! Your result is at the end")
        g = Image.new("RGB", (1365, 540))
        g.paste(a.resize((304, 540)), (0, 0))
        g.paste(b.resize((960, 540)), (320, 0))
        g.save(os.path.join(out_dir, "q2prev.png"))
        sys.exit()
    v = build.Voice(tts)
    if what == "levels":
        for lk in ("beginner", "intermediate", "advanced"):
            build_level(out_dir, v, lk)
    else:
        build_shorts(out_dir, v)

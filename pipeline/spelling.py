"""Spelling test series: 5 vertical Shorts (3 words each) + 1 long video with all 15 words.

Usage:  python3 spelling.py OUT_DIR shorts  -> spelling-short1..5.mp4
        python3 spelling.py OUT_DIR long    -> spelling-test-15.mp4 (+ _thumb.jpg)
Each Short ends with: the full video is on the channel + like & subscribe.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art  # noqa: E402
import build  # noqa: E402
from quiz import Q, Timeline, title_frame  # noqa: E402

H = art.hexc
SETS = [
    ("Part 1", [
        (["beleive", "believe", "belive"], "believe", "I before E: bel-IE-ve."),
        (["restaurant", "restaurent", "resturant"], "restaurant", "Rest-AU-rant."),
        (["calender", "calandar", "calendar"], "calendar", "It ends with -AR: calend-AR."),
    ], "Can You Spell These 3 Words? 🤯 Most People Can't #shorts"),
    ("Part 2", [
        (["wierd", "weerd", "weird"], "weird", "Weird breaks the I before E rule!"),
        (["Febuary", "February", "Februery"], "February", "Don't forget the first R: Feb-R-uary."),
        (["library", "libary", "liberary"], "library", "Li-BRA-ry: two Rs!"),
    ], "Spelling Test 😳 Even Adults Get These Wrong #shorts"),
    ("Part 3", [
        (["knowlege", "knowledge", "knowladge"], "knowledge", "Know + ledge = knowLEDGE."),
        (["successful", "succesful", "sucessful"], "successful", "Double C, double S."),
        (["occassion", "ocasion", "occasion"], "occasion", "Double C, one S."),
    ], "Only Good Spellers Get 3/3 🧠 English Spelling Test #shorts"),
    ("Part 4", [
        (["enviroment", "envirnment", "environment"], "environment", "Don't forget the N: enviroN-ment."),
        (["reccomend", "recommend", "recomend"], "recommend", "One C, double M."),
        (["schedule", "schedual", "shedule"], "schedule", "S-C-H-E-D-U-L-E."),
    ], "Which One Is Correct? 🤔 English Spelling Test #shorts"),
    ("Part 5", [
        (["rythm", "rhythym", "rhythm"], "rhythm", "No vowels except Y: R-H-Y-T-H-M!"),
        (["questionnaire", "questionaire", "questionnare"], "questionnaire", "Double N in questionnaire."),
        (["pronounciation", "pronunciation", "pronunsiation"], "pronunciation", "Pro-NUN-ciation: no O after the first N!"),
    ], "The Hardest English Spelling Test 😱 Can You Get 3/3? #shorts"),
]
SPOKEN = ["Which word is spelled correctly?", "And this one?", "The last one is the hardest!"]

for si, (_, words, _) in enumerate(SETS, 1):
    for wi, (opts, ans, why) in enumerate(words, 1):
        Q[f"sp{si}_{wi}"] = ("text", "Which word is spelled correctly?", SPOKEN[wi - 1], opts, ans, why)

TAGS = ["spelling test", "english spelling", "english test", "english quiz", "commonly misspelled words",
        "learn english", "english vocabulary", "ielts", "اختبار اللغة الانجليزية", "تعلم الانجليزية",
        "الاملاء بالانجليزي", "test d'anglais", "orthographe anglaise", "quiz anglais"]


def build_shorts(out_dir, voice):
    for si, (part, words, title) in enumerate(SETS, 1):
        work = os.path.join(out_dir, f"work_spelling-short{si}")
        os.makedirs(work, exist_ok=True)
        tl = Timeline(work, voice)
        hook = title_frame(["Can you spell", "all 3 words?"], True, "SPELLING TEST", chars=False)
        d = tl.say("Spelling test! Can you spell all three words correctly? Let's see!")
        tl.show(hook, d + 0.3)
        for wi in range(1, len(words) + 1):
            tl.question(f"sp{si}_{wi}", True, f"Spelling test · {part}", wi, len(words), answer_voice="narrator")
        end = title_frame(["Comment your score!", "Want the full video?", "It's on our channel!",
                           "Liked it? Like & Subscribe!"], True, "Score?", chars=False)
        d = tl.say("How many did you get? Comment your score! Want the full spelling test? "
                   "Go to our channel, you'll find it! And if you liked it, like and subscribe!")
        tl.show(end, d + 0.8)
        out = os.path.join(out_dir, f"spelling-short{si}.mp4")
        tl.render(out, music_vol=0.07, vertical=True)
        ws = ", ".join(w[1] for w in words)
        meta = {
            "title": title,
            "description": (f"English spelling test — {part}: can you spell all 3 words? 🧠\n"
                            "💬 Comment your score: 1/3, 2/3 or 3/3?\n"
                            "🎬 Want the full video with 15 words? Go to our channel, you'll find it!\n"
                            "👍 Liked it? Like & subscribe for a new test every week! 🔔\n\n"
                            "🇲🇦 اختبر الإملاء الإنجليزي — الفيديو الكامل في القناة!\n"
                            "🇫🇷 Teste ton orthographe en anglais — la vidéo complète est sur la chaîne !\n\n"
                            "#shorts #SpellingTest #EnglishTest #LearnEnglish"),
            "tags": TAGS,
        }
        json.dump(meta, open(os.path.join(out_dir, f"spelling-short{si}_meta.json"), "w"), ensure_ascii=False,
                  indent=2)
        print(f"short {si}: {out} ({tl.t:.0f} s) — {ws}")


def build_long(out_dir, voice):
    slug = "spelling-test-15"
    work = os.path.join(out_dir, "work_" + slug)
    os.makedirs(work, exist_ok=True)
    tl = Timeline(work, voice)
    tf = lambda lines, big: title_frame(lines, False, big, chars=False)  # noqa: E731
    intro = tf(["15 words that most people misspell", "5 parts · 5 seconds each · keep your score!"],
               "Spelling Test")
    for text in ("Welcome to the big English spelling test! Fifteen words that most people misspell.",
                 "Five parts, three words each. You have five seconds for every word. Keep your score!",
                 "At the end, share your score in the comments. Ready? Let's go!"):
        d = tl.say(text)
        tl.show(intro, d + 0.3)
    footers = ["Keep your score! Share it in the comments at the end",
               "Part 2... how many do you have so far?",
               "Halfway! The words get harder...",
               "Almost there! Don't stop now",
               "Last part: the hardest words!"]
    num = 0
    for si, (part, words, _) in enumerate(SETS, 1):
        d = tl.say(f"{part}!")
        tl.show(tf([f"{len(words)} words"], part), d + 0.6)
        for wi in range(1, len(words) + 1):
            num += 1
            tl.question(f"sp{si}_{wi}", False, f"Spelling Test · {part}", num, 15, answer_voice="narrator",
                        footer=footers[si - 1])
    res = tf(["15/15: Spelling champion! 🏆".replace(" 🏆", ""), "11–14: Excellent", "7–10: Good",
              "0–6: Keep practising!", "Share your score in the comments!"], "Your score?")
    for text in ("Finished! What's your score? Fifteen out of fifteen means you are a spelling champion!",
                 "Share your score with us in the comments!"):
        d = tl.say(text)
        tl.show(res, d + 0.6)
    end = tf(["If you liked it, like and subscribe!", "A new English test every week on our channel"], "Thank you!")
    d = tl.say("If you liked this video, like and subscribe. A new English test every week! See you next time!")
    tl.show(end, d + 1.0)
    out = os.path.join(out_dir, slug + ".mp4")
    tl.render(out, music_vol=0.06)
    c = art.Canvas(1280, 720)
    c.rect(0, 0, 1280, 720, H("#2B2350"))
    c.text(640, 95, "SPELLING TEST", art.font(110, "Bold"), H("#FFE680"), anchor="mm", stroke=6,
           stroke_fill=H("#000000"))
    for k, (w, ok) in enumerate((("Febuary", False), ("February", True), ("rythm", False), ("rhythm", True))):
        x = 330 if k % 2 == 0 else 950
        y = 270 + (k // 2) * 170
        c.rect(x - 280, y - 65, x + 280, y + 65, H("#FFFFFF") if ok else H("#FFFFFF", 200), r=30)
        c.text(x - 30, y, w, art.font(78, "Bold"), H("#2FA84F") if ok else H("#E84A4A"), anchor="mm")
        mark_x = x + 220
        if ok:
            c.line([(mark_x - 30, y), (mark_x - 8, y + 24), (mark_x + 32, y - 28)], H("#2FA84F"), 14)
        else:
            c.line([(mark_x - 25, y - 25), (mark_x + 25, y + 25)], H("#E84A4A"), 14)
            c.line([(mark_x - 25, y + 25), (mark_x + 25, y - 25)], H("#E84A4A"), 14)
    c.rect(290, 590, 990, 690, H("#FF7A30"), r=34)
    c.text(640, 640, "15 words · Can you get 15/15?", art.font(54, "Bold"), H("#FFFFFF"), anchor="mm")
    c.final().convert("RGB").save(os.path.join(out_dir, slug + "_thumb.jpg"), quality=92)
    allw = "\n".join(f"Part {si}: " + ", ".join(w[1] for w in words) for si, (_, words, _) in enumerate(SETS, 1))
    meta = {
        "title": "English Spelling Test 🧠 15 Words Most People Misspell | Can You Get 15/15?",
        "description": (
            "Can you spell these 15 English words? 🧠✍️\n"
            "5 parts, 3 words each, 5 seconds per word. Keep your score!\n\n"
            f"📚 Words in this test:\n{allw}\n\n"
            "💬 Share your score in the comments!\n"
            "👍 If you liked it, like and subscribe for a new English test every week! 🔔\n\n"
            "🇲🇦 اختبر الإملاء في اللغة الإنجليزية: 15 كلمة يخطئ فيها أغلب الناس!\n"
            "🇫🇷 Teste ton orthographe en anglais : 15 mots que la plupart des gens écrivent mal !\n\n"
            "#SpellingTest #EnglishTest #LearnEnglish #EnglishQuiz"),
        "tags": TAGS,
    }
    json.dump(meta, open(os.path.join(out_dir, slug + "_meta.json"), "w"), ensure_ascii=False, indent=2)
    print(f"done: {out} ({tl.t / 60:.1f} min)")


if __name__ == "__main__":
    out_dir, what = sys.argv[1], sys.argv[2]
    tts = os.environ.get("MT_TTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts"))
    v = build.Voice(tts)
    if what == "shorts":
        build_shorts(out_dir, v)
    else:
        build_long(out_dir, v)

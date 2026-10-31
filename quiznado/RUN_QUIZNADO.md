# QuizNado run — every 3 days: 1 "Easy to Impossible" video + 1 teaser Short + fiche

Run by the scheduled task every 3 days. Nobody is watching: do not ask questions. If one item
fails, finish the others and say what failed at the end. Zahra publishes **by hand** on YouTube
(no Metricool, no scheduling tool): long video today at 20:00, the Short tomorrow at 20:00,
nothing on the 3rd day (Morocco time). Files must reach her before 20:00 today.

**Only ONE Short per set** (her rule, 31 Oct 2026: posting a lot hurts views): the teaser Short =
2 hard questions WITH answers, then the long video's IMPOSSIBLE last question WITHOUT answer, ending
on "Want the answer? Watch the full video" with the long video's thumbnail + subscribe & like.

Why this format (her YouTube Studio, Oct 2026): "Easy to Impossible" English tests (plurals,
spelling, common mistakes, mental math, opposites, past tense) and Spot the Difference keep viewers
best (20–30 % watched). General knowledge, capitals, IQ, synonyms, vocabulary, riddles and the
purple "level" quizzes lose people in 3 seconds — never make those. The old 49-question
Ultimate Quiz (`DAILY_QUIZNADO.md`) is retired.

## 0. Already done today?
If `packs_history.json` already has a run with today's date, stop and just report that.

## 1. Setup (~3 min)
```
cd /home/claude/moontales-videos
bash pipeline/setup.sh
cd quiznado && python3 pack_tools.py next     # theme, number, slug, example pack to copy
```
`next` rotates the themes (never the same theme twice in a row).

## 2a. Quiz theme → write `pipeline/quizpacks/<slug>.json`
Copy the structure and style of the `copy_style_from` pack exactly (same fields, same tone,
same kind of title/thumb/tags, same `spoken_cycle` / `read_options` / `math` settings).
- Name/title with the new number: e.g. `"name": "Plurals Test 2"`,
  title `"Plurals Test 2: Easy to Impossible 🧠 32 New Words | ..."` (≤ 100 chars).
- 4 levels × 8 questions = 32, really getting harder: Easy, Medium, Hard, Impossible.
  The LAST question of level 4 is the teaser shown at the start of the video: make it a great one.
- Every item `[shown, [3 options], answer, why, (spoken)]`: exactly one correct option, facts you
  are 100 % sure of (standard British/American spelling both accepted only if the pack says so),
  question ≤ 60 chars, options ≤ 26, `why` ≤ 60 (a short, clear explanation).
- ALL questions must be NEW: `check` refuses anything used in any earlier pack.
- `teaser`: `{"picks": [[2,i],[3,j]], "title": "... #shorts"}` = one HARD and one IMPOSSIBLE question
  (index 0–6, never `[3,7]`: that one is shown unanswered at the end of the Short). No `shorts` field.
  Title idea: `Only 1% Get The Last One 🧠 Answer In The Full Video! #shorts`.
- `tags`: 12–16, mixing **English, Arabic and French**; `ar` and `fr` lines. Never "rainbow".
```
python3 pack_tools.py check ../pipeline/quizpacks/<slug>.json   # fix until it prints OK
```

## 2b. Spot the Difference theme
```
cd ../pipeline
python3 spotgen.py <scratchpad>/spotimg <slug> <YYYYMMDD as seed> 0001112233 > <scratchpad>/raw.json
cd ../quiznado && python3 pack_tools.py spotmeta <scratchpad>/raw.json <slug> <number>
```
(Images live in the scratchpad; still commit the small pack JSON so the numbering goes on.)

## 3. Render (~25 min) — quiz: `quizpack.py`, spot: `spotdiff.py`
```
cd ../pipeline
python3 quizpack.py quizpacks/<slug>.json $OUT preview   # (spot: spotdiff.py spotpacks/<slug>.json $OUT preview)
```
Look at the preview PNGs and the thumbnail (text fits, answers right, no rainbow), then:
```
python3 quizpack.py quizpacks/<slug>.json $OUT long   # makes the thumbnail too
python3 quizpack.py quizpacks/<slug>.json $OUT short  # the teaser Short (uses the thumbnail)
# spot: python3 spotdiff.py spotpacks/<slug>.json $OUT long  then  ... $OUT short
cd ../quiznado && python3 pack_tools.py fiche <slug> $OUT
```
Check one frame of each video (`ffmpeg -ss 20 -i FILE -frames:v 1 check.png`, look at it), and the
last frame of the Short (the end card with the thumbnail).

## 4. Deliver
SendUserFile (status proactive, display attach): `<slug>.mp4`, `<slug>_thumb.jpg`,
`<slug>_short.mp4` and the fiche `.txt`. Then a short SendUserMessage +
PushNotification: "QuizNado ready — publish today at 20:00!" with the 3 titles and the plan
(long video today 20:00, the Short tomorrow 20:00; in YouTube Studio set the Short's
"Related video" = the long video).

## 5. Save
```
python3 pack_tools.py done <slug> "<theme>"
git add quiznado/packs_history.json pipeline/quizpacks/<slug>.json   # (spot: pipeline/spotpacks/<slug>.json)
git commit -m "QuizNado: <title>" && git -c push.negotiate=false push origin main
```
(fetch/rebase first if the push is rejected). Never commit .mp4 or .png files.

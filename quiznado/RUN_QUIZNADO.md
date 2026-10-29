# QuizNado run — every 3 days: 1 "Easy to Impossible" video + 2 Shorts + fiche

Run by the scheduled task every 3 days. Nobody is watching: do not ask questions. If one item
fails, finish the others and say what failed at the end. Zahra publishes **by hand** on YouTube
(no Metricool, no scheduling tool): long video today at 20:00, Short 1 tomorrow at 20:00,
Short 2 the day after at 20:00 (Morocco time). Files must reach her before 20:00 today.

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
- `shorts`: exactly 2, each 4 picks `[[0,i],[1,j],[2,k],[3,l]]`, all 8 picks different, never
  `[3,7]`; catchy titles ending in `#shorts`.
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
python3 quizpack.py quizpacks/<slug>.json $OUT shorts & python3 quizpack.py quizpacks/<slug>.json $OUT long & wait
cd ../quiznado && python3 pack_tools.py fiche <slug> $OUT
```
Check one frame of each video (`ffmpeg -ss 20 -i FILE -frames:v 1 check.png`, look at it).

## 4. Deliver
SendUserFile (status proactive, display attach): `<slug>.mp4`, `<slug>_thumb.jpg`,
`<slug>_short1.mp4`, `<slug>_short2.mp4` and the fiche `.txt`. Then a short SendUserMessage +
PushNotification: "QuizNado ready — publish today at 20:00!" with the 3 titles and the plan
(long today, Short 1 tomorrow, Short 2 the day after, all 20:00).

## 5. Save
```
python3 pack_tools.py done <slug> "<theme>"
git add quiznado/packs_history.json pipeline/quizpacks/<slug>.json   # (spot: pipeline/spotpacks/<slug>.json)
git commit -m "QuizNado: <title>" && git -c push.negotiate=false push origin main
```
(fetch/rebase first if the push is rejected). Never commit .mp4 or .png files.

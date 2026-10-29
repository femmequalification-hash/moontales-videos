# QuizNado daily run — 1 Ultimate Quiz (49 questions, 12+ min) + 2 Shorts + fiche

> RETIRED (Oct 2026): the scheduled task now follows `RUN_QUIZNADO.md` (Easy to Impossible packs, every 3 days).

Run by the daily scheduled task. Nobody is watching: do not ask questions. If one
item fails, finish the others and say what failed at the end. Zahra publishes the
videos herself on YouTube at **20:00 Morocco time**, so the files must reach her before then.

Same design every day (purple background, white question card, A/B/C options,
timer, her QuizNado logo, English voice "af_heart", "subscribe & like" moment,
"comment your score" ending). **Only the questions change.**

## 0. Already done today?
If `quiznado/days/<today's date>.json` exists AND `history.json` has a day with that date,
today's videos were already made and sent: stop and just report that (no new videos).

## 1. Setup (~3 min)
```
cd /home/claude/moontales-videos
bash pipeline/setup.sh          # kokoro voice + python packages
cd quiznado
python3 daily_tools.py next     # (date = today in Morocco, = UTC) prints today's number, date, round topics, 2 suggested Short topics
```

## 2. Write today's questions → `quiznado/days/<DATE>.json`
Copy the structure of `days/EXAMPLE.json` exactly.
- `number` and `date` from `daily_tools.py next`.
- `long.rounds`: the same 7 rounds in the same order (General Knowledge, IQ Test, English
  Test, Math Speed, Riddles, Science Quiz, Capitals Quiz), **7 questions each** (49 in total, so the
  video is longer than 10 minutes — EXAMPLE.json shows only 5 per round: write 7).
  Mix difficulty inside each round: 3 easy, 3 medium, 1 hard (the last one).
- `shorts`: 2 Shorts, use the 2 suggested topics, 5 questions each, a hook ≤ 34 chars
  ("Only geniuses get #5!", "Most people miss #3!"), a catchy title ending in `#shorts`,
  a one-line `first_line` for the description, short `extra_tags` mixing **English, Arabic and French**.
- `long.title`: `ULTIMATE QUIZ #<number>: ...` (≤ 100 chars), `long.extra_tags` mixing EN/AR/FR.
- Every question: 3 options, `answer` = 0/1/2, exactly ONE correct option, facts you are sure of
  (no trick facts that are disputed). Question ≤ 95 chars, options ≤ 26 chars.
  Write math with × and ÷. Varied answer positions (not always B).
- Family-friendly, no politics, no religion debates, never "rainbow".
- Must be NEW: `daily_tools.py check` refuses any question already used before.

```
python3 daily_tools.py check days/<DATE>.json     # must print OK; fix and re-run until OK
```

## 3. Render (long ~25–30 min, Shorts ~3 min each) — run in parallel
```
OUT=<scratchpad>/out
python3 render.py days/<DATE>.json $OUT long   &
python3 render.py days/<DATE>.json $OUT short1 &
python3 render.py days/<DATE>.json $OUT short2 &
wait
python3 daily_tools.py fiche days/<DATE>.json $OUT
```
Check 1 frame of each video (`ffmpeg -ss 30 -i FILE -frames:v 1 check.png`, look at it)
and the thumbnail.

## 4. Deliver
SendUserFile (status proactive, display attach): the long video, its thumbnail, the 2 Shorts
and the fiche `.txt`. Then a short SendUserMessage + PushNotification (if available):
"QuizNado #N ready for 20:00" with the 3 titles.

## 5. Save
```
python3 daily_tools.py done days/<DATE>.json      # adds questions to history.json
git add days/<DATE>.json history.json && git commit -m "QuizNado #N (<DATE>)" && git -c push.negotiate=false push origin main
```
(fetch/rebase first if the push is rejected). Never commit .mp4 files.

# Moon Tales Kids — how to write a story file

Each video is one JSON file in `pipeline/stories/<slug>.json`. `build.py` turns it
into a ~5-minute video. Look at `stories/windy-day.json` as the reference.

## Channel rules (from the owner — always follow)
- Simple English stories for children aged 3–8, teaching **6–8 new English words**.
- Main characters: **Lina** (girl, purple dress) and **Adams** (boy, blue star shirt),
  friends, plus **Milo** the orange cat. Kind, gentle, safe stories; a small problem
  solved with kindness or teamwork; a clear happy ending.
- **Never** a rainbow — not in the story text, not in props, not in the thumbnail.
- Tags must **mix English, Arabic and French**.
- Description: short summary, then the list of new words each with Arabic and French
  translation, a "For parents" line, one Arabic line and one French line, subscribe line.
- Every story must be **different** from the ones already in `stories/`: new topic,
  new words, different settings / times of day. Check the existing files first.

## Length
About 5 minutes = **11–12 scenes**, each with **7–8 lines** (9 scenes gave only ~4 minutes), plus the automatic
intro, word recap and goodbye. Each new word gets its own scene with the pattern:
characters use the word → narrator explains it → "Say it with me: WORD!" →
`{"pause": 1.8}`.

## JSON fields
```
slug              lowercase-with-dashes, unique (used for file names)
story_title       "Lina and Adams and the ..."   (said in the intro)
lesson            short line under the title card, e.g. "Learn fruit words in English!"
title             YouTube title, max 100 characters, include "| Moon Tales Kids"
thumbnail_title   2–4 big words for the thumbnail
thumbnail_word    short orange label on the thumbnail, e.g. "Fruit words"
thumbnail_scene   a scene object (setting/time/weather/props/chars) for the thumbnail
description       YouTube description (see rules above), max 4500 characters
tags              14–20 tags, mixed EN/AR/FR, all tags together under 450 characters
scenes            list of scene objects
```

## Scene object
```
setting   park | garden | forest | beach | street | kitchen | bedroom | classroom
time      day | sunset | night
weather   sunny | cloudy | windy | rain | snow      (outdoor scenes only animate it)
chars     any of ["lina", "adams", "milo"]  (1–3; order = left to right)
props     list of prop names, or {"name": "...", "x": 1600, "y": 900} for a position
          (background is 2112x1188; characters stand around x=700–1400, so keep
           props at x 1400–2000 or x 100–500, ground level y≈900–1000)
word      the new word for this scene (shown on a card + highlighted in subtitles)
board     classroom only: short text written on the chalkboard ("1 2 3", "Shapes")
lines     list of {"text": "..."} (narrator), {"who": "lina"|"adams"|"milo", "text": "..."},
          or {"pause": 1.8}
```

## Props that can be drawn
kite, ball, umbrella, umbrella_over (big umbrella over the characters), book, apple,
cake, cup, star, flower, puddle, boat, bed, table, lamp, banana, orange, carrot,
sandwich, car, bike, dog, bird, fish (in a bowl), hat, shoes, toothbrush, balloon,
gift, butterfly, circle, square, triangle, heart.

Anything not in this list cannot be drawn — talk about it in the text only, or pick
another topic. Good topics: fruits, vegetables, colours (use props of that colour),
shapes, numbers (classroom board), feelings, body/clean habits (toothbrush), clothes
(hat, shoes), pets (dog, fish, bird, cat), toys, transport (car, bike, boat),
birthday, beach day, bedtime, sharing, saying please and thank you, days of the week,
opposites (big/small, hot/cold), seasons, good manners, kindness.

## Voice tips
The narrator voice is calm; the kids' voices are higher. Keep sentences short
(under ~15 words). Write numbers as words. Sounds like "Meow!", "Splash!" are fun.

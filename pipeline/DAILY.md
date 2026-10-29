# Run every 3 days — 1 new Moon Tales Kids video + 2 Shorts

This is what the scheduled task (every 3 days) does, start to finish, with no one watching.
Do not ask questions; if something fails, skip that item, finish the others, and
report what happened at the end.

## 0. Get the code
Do step 3's day check FIRST: if the target day is more than 3 days away, stop
quietly (no message, no notification) — the queue is already full.

- Attach the repo: `add_repo(owner="femmequalification-hash", repo="moontales-videos", access="push")`,
  clone it to `/home/claude/moontales-videos` (one clone, ~10 min timeout).
- `bash pipeline/setup.sh` (installs packages and downloads the free voice model, ~2 min).

## 1. Write 1 new story
- Read `pipeline/STORY_GUIDE.md` and `pipeline/stories/windy-day.json`.
- List `pipeline/stories/*.json` and read their `story_title` and `word`s: the new
  story must use a **new topic and new words** not used before.
- Use a setting / time of day different from the last stories. Write it to `pipeline/stories/<slug>.json`.
- Validate it: JSON loads, title ≤ 100 chars, tags total < 450 chars, every `prop`
  is in the guide's list, no "rainbow" anywhere (`grep -i rainbow` must find nothing).

## 2. Build
For the story:
1. `python3 pipeline/build.py pipeline/stories/<slug>.json OUT` (OUT in the scratchpad), ~10 min.
2. Two Shorts per story (vertical 1080x1920, 40–58 s, 2–3 new words each, different words):
   `python3 pipeline/short.py pipeline/stories/<slug>.json OUT 1` → `OUT/<slug>_short.mp4` + `_short_meta.json`
   `python3 pipeline/short.py pipeline/stories/<slug>.json OUT 2` → `OUT/<slug>_short2.mp4` + `_short2_meta.json`
   Needs step 1 first (it reuses the scene clips). Stories need at least 5 new words
   so part 2 has words left.
3. Check one frame of each: `ffmpeg -ss 30 -i OUT/<file>.mp4 -frames:v 1 OUT/check.png`
   and look at it.

## 3. Pick the day, then the publish times (Morocco time)
Owner's rule (Oct 2026): **one long video every 3 days**, and its 2 Shorts on the
2 days after it — so the channel gets exactly ONE post per day, never more.
Call Metricool `getScheduledPosts(brandId=7530657, fromDate=<today>T00:00:00+00:00,
toDate=<today+14 days>T00:00:00+00:00, timezone="UTC")` and find L = the LAST day that
already has a long video (youtubeData.type "video") scheduled.
- Target day D = L + 3 days. If nothing is scheduled, D = tomorrow.
- If D is more than 3 days after today, stop quietly: the queue is full.
- D, D+1 and D+2 must have no other post; if one has, move D forward until they are free.

| Morocco time | What |
|---|---|
| D at 17:00 | long video |
| D+1 at 17:00 | Short part 1 |
| D+2 at 17:00 | Short part 2 |

Morocco went back to plain GMT (= UTC) on 20 Sept 2026, but Metricool still thinks
"Africa/Casablanca" is UTC+1. So always send times as **UTC**: Morocco 17:00 →
`date="YYYY-MM-DDT17:00:00+00:00"` and `publicationDate.timezone="UTC"`.

## 4. Upload + schedule
1. Upload all files at once:
   `bash pipeline/upload.sh push OUT/<s>.mp4 OUT/<s>_thumb.jpg OUT/<s>_short.mp4 OUT/<s>_short2.mp4`
   → prints one public URL per file.
2. For each of the 3 posts call Metricool `createScheduledPost` with `blogId=7530657`,
   `date=<YYYY-MM-DDTHH:MM:00+00:00>`, and `info`:

   Long video (title/description/tags from the story JSON):
```json
{"autoPublish": true, "descendants": [], "draft": false, "firstCommentText": "",
 "hasNotReadNotes": false, "media": ["<VIDEO_URL>"], "videoThumbnailUrl": "<THUMB_URL>",
 "mediaAltText": [], "providers": [{"network": "youtube"}],
 "publicationDate": {"dateTime": "<YYYY-MM-DDTHH:MM:00>", "timezone": "UTC"},
 "shortener": false, "smartLinkData": {"ids": []}, "text": "<description>",
 "youtubeData": {"title": "<title>", "type": "video", "privacy": "public", "tags": [<tags>],
   "category": "EDUCATION", "madeForKids": true, "isAiGeneratedContent": true}}
```
   Short (title/description/tags from `<slug>_short_meta.json` / `_short2_meta.json`; **no videoThumbnailUrl**
   for Shorts — Metricool rejects the whole post if the channel can't use Shorts thumbnails):
```json
{"autoPublish": true, "descendants": [], "draft": false, "firstCommentText": "",
 "hasNotReadNotes": false, "media": ["<SHORT_URL>"], "mediaAltText": [],
 "providers": [{"network": "youtube"}],
 "publicationDate": {"dateTime": "<YYYY-MM-DDTHH:MM:00>", "timezone": "UTC"},
 "shortener": false, "smartLinkData": {"ids": []}, "text": "<description>",
 "youtubeData": {"title": "<title>", "type": "short", "privacy": "public", "tags": [<tags>],
   "category": "EDUCATION", "madeForKids": true, "isAiGeneratedContent": true}}
```
3. Check each answer's `media` now points at `static.metricool.com` (Metricool copied it).
4. After the last one: `bash pipeline/upload.sh clear`.

## 5. Save + report
- Commit the new story file to `main` and push (end the commit message with the
  attribution lines from the session's instructions).
- Send the owner a short message (SendUserMessage + PushNotification if available):
  the video title and the 2 Shorts with their publish days and times, and anything that failed.

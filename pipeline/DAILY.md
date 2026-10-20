# Daily run — 2 new Moon Tales Kids videos + 2 Shorts

This is what the daily scheduled task does, start to finish, with no one watching.
Do not ask questions; if something fails, skip that item, finish the others, and
report what happened at the end.

## 0. Get the code
(Do step 3's day check first if you like: if there is no free day in the next
10 days, stop and report — the queue is full.)

- Attach the repo: `add_repo(owner="femmequalification-hash", repo="moontales-videos", access="push")`,
  clone it to `/home/claude/moontales-videos` (one clone, ~10 min timeout).
- `bash pipeline/setup.sh` (installs packages and downloads the free voice model, ~2 min).

## 1. Write 2 new stories
- Read `pipeline/STORY_GUIDE.md` and `pipeline/stories/windy-day.json`.
- List `pipeline/stories/*.json` and read their `story_title` and `word`s: the 2 new
  stories must use **new topics and new words** not used before.
- Use different settings and times of day for the 2. Write them to `pipeline/stories/<slug>.json`.
- Validate each: JSON loads, title ≤ 100 chars, tags total < 450 chars, every `prop`
  is in the guide's list, no "rainbow" anywhere (`grep -i rainbow` must find nothing).

## 2. Build
For each story, one after another:
1. `python3 pipeline/build.py pipeline/stories/<slug>.json OUT` (OUT in the scratchpad), ~10 min.
2. `python3 pipeline/short.py pipeline/stories/<slug>.json OUT` → `OUT/<slug>_short.mp4`
   (vertical 1080x1920, 40–58 s, 2–3 new words) and `OUT/<slug>_short_meta.json`
   (title, description, tags). Needs step 1 first (it reuses the scene clips).
3. Check one frame of each: `ffmpeg -ss 30 -i OUT/<file>.mp4 -frames:v 1 OUT/check.png`
   and look at it.

## 3. Pick the day, then the publish times (Morocco time)
**Never post more than 2 long videos + 2 Shorts on one day.** First call Metricool
`getScheduledPosts(brandId=7530657, fromDate=<today>T00:00:00+00:00,
toDate=<today+10 days>T00:00:00+00:00, timezone="UTC")` and find the **first day,
from today on, that has no long video (youtubeData.type "video") scheduled**. Use that
day for the 4 slots below. If today already has posts, today is not free — move on.

| Morocco time | What |
|---|---|
| 10:00 | story 1 — long video |
| 13:00 | story 1 — Short |
| 17:00 | story 2 — long video |
| 20:00 | story 2 — Short |

If the chosen day is today and a slot is already past (or less than 15 minutes
away), use the next free day instead.
Morocco went back to plain GMT (= UTC) on 20 Sept 2026, but Metricool still thinks
"Africa/Casablanca" is UTC+1. So always send times as **UTC**: Morocco 10:00 →
`date="YYYY-MM-DDT10:00:00+00:00"` and `publicationDate.timezone="UTC"`.

## 4. Upload + schedule
1. Upload all files at once:
   `bash pipeline/upload.sh push OUT/<s1>.mp4 OUT/<s1>_thumb.jpg OUT/<s1>_short.mp4 OUT/<s2>.mp4 OUT/<s2>_thumb.jpg OUT/<s2>_short.mp4`
   → prints one public URL per file.
2. For each of the 4 posts call Metricool `createScheduledPost` with `blogId=7530657`,
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
   Short (title/description/tags from `<slug>_short_meta.json`; **no videoThumbnailUrl**
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
- Commit the 2 new story files to `main` and push (end the commit message with the
  attribution lines from the session's instructions).
- Send the owner a short message (SendUserMessage + PushNotification if available):
  the 2 video titles and 2 Shorts with their publish times, and anything that failed.

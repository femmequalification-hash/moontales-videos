# Daily run — 4 new Moon Tales Kids videos

This is what the daily scheduled task does, start to finish, with no one watching.
Do not ask questions; if something fails, skip that video, finish the others, and
report what happened at the end.

## 0. Get the code
- Attach the repo: `add_repo(owner="femmequalification-hash", repo="moontales-videos", access="push")`,
  clone it to `/home/claude/moontales-videos` (one clone, ~10 min timeout).
- `bash pipeline/setup.sh` (installs packages and downloads the free voice model, ~2 min).

## 1. Write 4 new stories
- Read `pipeline/STORY_GUIDE.md` and `pipeline/stories/windy-day.json`.
- List `pipeline/stories/*.json` and read their `story_title` and `word`s: the 4 new
  stories must use **new topics and new words** not used before.
- Mix settings and times of day across the 4. Write them to `pipeline/stories/<slug>.json`.
- Validate each: JSON loads, title ≤ 100 chars, tags total < 450 chars, every `prop`
  is in the guide's list, no "rainbow" anywhere (`grep -i rainbow` must find nothing).

## 2. Build
For each story, one after another (2 CPUs — don't run more than 2 at once):
`python3 pipeline/build.py pipeline/stories/<slug>.json OUT` with OUT in the scratchpad.
Takes ~10 minutes per video. Then check one frame:
`ffmpeg -ss 60 -i OUT/<slug>.mp4 -frames:v 1 OUT/<slug>_check.png` and look at it.

## 3. Publish times (Morocco time)
**10:00, 13:00, 17:00, 20:00** today. If a slot is already past (or less than
15 minutes away), use the same slot **tomorrow**.
Morocco went back to plain GMT (= UTC) on 20 Sept 2026, but Metricool still thinks
"Africa/Casablanca" is UTC+1. So always send times as **UTC**: Morocco 10:00 →
`date="YYYY-MM-DDT10:00:00+00:00"` and `publicationDate.timezone="UTC"`.

## 4. Upload + schedule (one video at a time)
1. `bash pipeline/upload.sh push <slug> OUT` → prints VIDEO_URL and THUMB_URL.
2. Metricool `createScheduledPost` with `blogId=7530657`, `date=<YYYY-MM-DDTHH:MM:00+00:00>`, and `info`:
```json
{"autoPublish": true, "descendants": [], "draft": false, "firstCommentText": "",
 "hasNotReadNotes": false, "media": ["<VIDEO_URL>"], "videoThumbnailUrl": "<THUMB_URL>",
 "mediaAltText": [], "providers": [{"network": "youtube"}],
 "publicationDate": {"dateTime": "<YYYY-MM-DDTHH:MM:00>", "timezone": "UTC"},
 "shortener": false, "smartLinkData": {"ids": []}, "text": "<description>",
 "youtubeData": {"title": "<title>", "type": "video", "privacy": "public", "tags": [<tags>],
   "category": "EDUCATION", "madeForKids": true, "isAiGeneratedContent": true}}
```
3. Check the answer's `media` now points at `static.metricool.com` (Metricool copied it).
4. Next video: `upload.sh push` again (it replaces the previous one).
5. After the last one: `bash pipeline/upload.sh clear`.

## 5. Save + report
- Commit the 4 new story files to `main` and push (ends the commit message with the
  attribution lines from the session's instructions).
- Send the owner a short message (SendUserMessage + PushNotification if available):
  the 4 titles with their publish times, and anything that failed.

---
name: clipspal-hooks
description: Drop in your b-roll, describe what you do, get 5 TikTok-ready videos with AI hook clips + burned-in captions. A free Claude Code skill from ClipsPal. Trigger with "/clipspal-hooks", "make tiktok hooks", "generate hook videos for X", or "clipspal hooks for my [project]".
---

# ClipsPal Hooks

A free skill from ClipsPal. Drop in your b-roll, describe what you do, and
get 5 TikTok-ready videos with AI hook clips + burned-in captions. No
signup, no watermark, runs locally in Claude Code.

ClipsPal posts 2 AI TikToks to grow your app, every day — start free at
clipspal.com.

## HARD RULES (do not violate)

1. **Never call fal.ai directly.** Use `scripts/fal_submit.py` and
   `scripts/fal_poll.py` for every fal interaction. They are the only
   writers to `state.json` — this is what prevents resubmitting jobs.
2. **Before every step, read state.**
   `PROJECT_DIR=<dir> python3 $SKILL/scripts/state.py summary`.
   Skip steps already `done`. Never regenerate a `done` artifact unless
   the user explicitly asks.
3. **If a slot's status is `pending`, poll it. Do not resubmit.**
4. **You generate the matrix yourself; you SELECT hooks from the library.**
   No LLM API calls — you ARE the model. Matrix → `prompts/matrix.md`.
   Hooks → `prompts/hooks.md` + `reference/hook-library.json`.
5. **3-second clips, Vidu q3 image-to-video.** Never Kling, never 5s.
6. **nano-banana for images.** Never Flux, never Imagen.
7. **Default count is 5.** Only generate more if the user says so.
8. **MANDATORY checkpoints — wait for explicit user approval at each:**
   - After step 0 (intake) — confirm cost + folder name before any spend
   - After the matrix (step 3) — before any fal call
   - After the frames (step 5) — before clip submission
   These gates are non-skippable.

## STEP 0 — Intake + prereqs (always run first)

You must do all of the following before generating anything. Run the checks
**before** asking the user for inputs you can derive — but ask for the rest
in one block.

### 0a. Verify prerequisites

```
bash $SKILL/scripts/check_prereqs.sh
```

If it exits non-zero, read the printed fix commands and **offer to run
them** via Bash. Typical fixes:
- `python3 -m pip install --user Pillow`
- `brew install ffmpeg-full && brew unlink ffmpeg && brew link --overwrite ffmpeg-full`

Do not proceed until all prereqs report `[ok]`.

### 0b. Resolve the fal.ai API key

```
bash $SKILL/scripts/fal_key.sh check
```

- If "ok" → continue.
- If "missing" → ask the user once for their fal.ai key
  (link them to https://fal.ai/dashboard/keys). When they paste it,
  persist it:
  ```
  bash $SKILL/scripts/fal_key.sh save <key>
  ```
  This writes `~/.clipspal/fal_key` (chmod 600). Future sessions don't
  need to ask again. `fal_submit.py` / `fal_poll.py` read it
  automatically — you do NOT need to `export FAL_KEY`.

### 0c. Gather the rest of the inputs

Ask the user (in one message, not three) for:

1. **Project description** — what is this content for? (one paragraph)
2. **Broll folder path** — absolute path to a folder of `.mp4`/`.mov`
   files you already have. (If they have none, point them at TikTok
   downloaders, royalty-free libraries, or screen recordings of their
   product.)
3. **Output folder name** — defaults to `./clipspal-hooks/`. They can
   override; never dump artifacts into the bare cwd.
4. **Language** — defaults to "en".

Then validate the broll folder:
```
bash $SKILL/scripts/check_broll.sh <broll_folder>
```
Exit 0 + file list → continue. Exit 1 → tell user the folder is empty
or missing, ask for a fixed path.

### 0d. Print the cost estimate + confirm

Before generating, print:

> This run will use your fal.ai credits:
>   - 5 nano-banana character images (~$0.20)
>   - 5 Vidu 3s reaction clips (~$0.75)
>   - Total: ~$0.95
> Reply "yes" to proceed.

**Wait for explicit "yes"** before moving on.

## STEP 1 — Initialize project workspace

```
export PROJECT_DIR=<chosen output folder, absolute or ./relative>
mkdir -p $PROJECT_DIR/{frames,clips,payloads,output}
python3 $SKILL/scripts/state.py init <slug>
python3 $SKILL/scripts/state.py summary
```

If `state.json` already existed in that folder, this is a **resume** —
keep going from the first non-done step. Tell the user "Picking up where
we left off."

## STEP 2 — Matrix (you, no API)

Read `$SKILL/prompts/matrix.md` and write `<wd>/matrix.json`. Then:
```
python3 $SKILL/scripts/state.py set matrix done
```

## STEP 3 — CHECKPOINT 1: matrix approval (mandatory)

Show the user the 5 rows in a short table (id, ethnicity, setting, emotion,
framing-confirms-centered). Ask:

> Approve these 5 characters, or want me to regenerate any rows?

Wait for the user. Accept: "good"/"approved"/"yes" → proceed; "regenerate
row N", "regen 2,4", "regen all" → rewrite those rows and re-checkpoint.

## STEP 4 — Hooks (you, no API)

Read `$SKILL/prompts/hooks.md` and `$SKILL/reference/hook-library.json`.
Pick 5 templates, fill in slots in audience language, write
`<wd>/hooks.json` with `n`, `text`, and `template_id`. Then:
```
python3 $SKILL/scripts/state.py set hooks done
```

## STEP 5 — First frames (nano-banana, 5 parallel jobs)

Build the nano-banana prompt from each matrix row using the template in
`$SKILL/reference/fal-endpoints.md` (which REQUIRES centered framing
language — use it verbatim).

Write `<wd>/payloads/frame_<n>.json`:
```json
{
  "prompt": "<built prompt>",
  "num_images": 1,
  "output_format": "png",
  "aspect_ratio": "9:16"
}
```

Submit all 5:
```
for n in 1 2 3 4 5; do
  python3 $SKILL/scripts/fal_submit.py frames $n fal-ai/nano-banana \
    $PROJECT_DIR/payloads/frame_$n.json &
done; wait
```

Poll all 5:
```
for n in 1 2 3 4 5; do
  python3 $SKILL/scripts/fal_poll.py frames $n &
done; wait
```

## STEP 6 — CHECKPOINT 2: frame approval (mandatory)

Before any clip job runs, show all 5 frame PNGs (`<wd>/frames/01.png` …
`05.png`) using the Read tool so the user can see them inline. Then ask:

> Approve these characters? "yes" to render 3s clips (~$0.75), "regen N"
> (e.g. "regen 2,4") to redo specific rows, "regen all" to redo all five.

**Wait for an explicit answer.** Do not submit clip jobs until approval.

On "regen N":
```
python3 $SKILL/scripts/state.py reset frames 2,4
```
…then update those matrix rows per user feedback, re-submit those slots,
re-poll, re-checkpoint.

## STEP 7 — Hook clips (Vidu q3 i2v, 5 parallel jobs)

Get each frame's fal CDN URL:
```python
import json, urllib.request, os
state = json.load(open(os.environ["PROJECT_DIR"] + "/state.json"))
key = open(os.path.expanduser("~/.clipspal/fal_key")).read().strip() if not os.environ.get("FAL_KEY") else os.environ["FAL_KEY"]
for slot in state["frames"]:
    rid = slot["request_id"]
    req = urllib.request.Request(
        f"https://queue.fal.run/fal-ai/nano-banana/requests/{rid}",
        headers={"Authorization": f"Key {key}"})
    print(slot["n"], json.load(urllib.request.urlopen(req))["images"][0]["url"])
```

Write `<wd>/payloads/clip_<n>.json`:
```json
{
  "image_url": "<frame n fal cdn url>",
  "prompt": "<motion prompt from matrix row via reference/fal-endpoints.md>",
  "duration": 3
}
```

Submit + poll with `kind=clips`, `model_id=fal-ai/vidu/q3/image-to-video`.

## STEP 8 — Assemble (local)

List the user's broll files (from check_broll.sh output earlier). Round-robin
pair across 5 outputs — if fewer broll files than 5, reuse from the top.

For each `n` in 1..5:
```
bash $SKILL/scripts/assemble.sh \
  <wd>/clips/<n>.mp4 \
  <broll_folder>/<chosen file> \
  "<hook text n>" \
  <wd>/output/<n>.mp4
```

When all 5 done:
```
python3 $SKILL/scripts/state.py set assembly done
```

Print the 5 output paths and `open <wd>/output/` so the user sees them.

## Resume / failure recipes

### Interrupted mid-run
User comes back, runs the skill again from the same folder. Step 1 detects
existing `state.json` → tells the user "resuming". Steps already `done`
are skipped. Pending slots get re-polled.

### A specific Vidu clip failed
```
python3 $SKILL/scripts/state.py reset clips 3
python3 $SKILL/scripts/fal_submit.py clips 3 fal-ai/vidu/q3/image-to-video \
  $PROJECT_DIR/payloads/clip_3.json
python3 $SKILL/scripts/fal_poll.py clips 3
```

### Permission prompt fatigue
Mention to the user: copy `$SKILL/reference/permissions-suggested.json`
into `<their cwd>/.claude/settings.local.json` to allowlist the exact
commands this skill runs.


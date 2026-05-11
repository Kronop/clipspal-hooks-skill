---
name: clipspal-hooks
description: Generate 5 TikTok-ready hook videos from a folder of b-roll. Builds a 5-row character matrix, renders each character as a still via fal-ai/gemini-3.1-flash-image-preview, animates them into 3s reaction clips via fal-ai/vidu/q3/image-to-video, concatenates with the user's b-roll, and burns in captions with ffmpeg. Use when the user wants TikTok hooks, AI UGC reactions, or short-form video openers for an app, product, or content niche.
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
   `PROJECT_DIR=<dir> python3 ${CLAUDE_SKILL_DIR}/scripts/state.py summary`.
   Skip steps already `done`. Never regenerate a `done` artifact unless
   the user explicitly asks.
3. **If a slot's status is `pending`, poll it. Do not resubmit.**
4. **You generate the matrix yourself; you SELECT hooks from the library.**
   No LLM API calls — you ARE the model. Matrix → `prompts/matrix.md`.
   Hooks → `prompts/hooks.md` + `reference/hook-library.json`.
5. **3-second clips, Vidu q3 image-to-video.** Never Kling, never 5s.
6. **`fal-ai/gemini-3.1-flash-image-preview` (Nano Banana 2) for character stills.** Never Flux, Imagen, or the older `fal-ai/nano-banana` — the prod ClipsPal pipeline is on Gemini 3.1 Flash Image and this skill must match it.
7. **Default count is 5.** Only generate more if the user says so.
8. **MANDATORY checkpoints — wait for explicit user approval at each:**
   - After step 0 (intake) — confirm cost + folder name before any spend
   - After the matrix (step 3) — before any fal call
   - After the characters (step 5) — before clip submission
   These gates are non-skippable.

## STEP 0 — Intake + prereqs (always run first)

You must do all of the following before generating anything. Run the checks
**before** asking the user for inputs you can derive — but ask for the rest
in one block.

### 0a. Offer the permission allowlist (one-time)

Before you run any `bash` or `python3` commands, tell the user this skill
will run several scripts and they'll see a permission prompt for each one
unless they pre-allowlist them. Offer:

> I can drop a ready-made allowlist into `.claude/settings.local.json` so
> you don't have to approve every command. Want me to?

If yes: read `${CLAUDE_SKILL_DIR}/reference/permissions-suggested.json` and
merge its `permissions.allow` entries into the user's
`<cwd>/.claude/settings.local.json` (creating the file if needed). Do this
once per project. If the user says no, just proceed and let them approve
prompts case by case.

### 0b. Verify prerequisites

```
bash ${CLAUDE_SKILL_DIR}/scripts/check_prereqs.sh
```

If it exits non-zero, read the printed fix commands and **offer to run
them** via Bash. Typical fixes:
- `python3 -m pip install --user Pillow`
- `brew install ffmpeg` (macOS) or `sudo apt install ffmpeg` (Linux)

Do not proceed until all prereqs report `[ok]`.

### 0c. Resolve the fal.ai API key

```
bash ${CLAUDE_SKILL_DIR}/scripts/fal_key.sh check
```

- If "ok" → continue.
- If "missing" → ask the user once for their fal.ai key
  (link them to https://fal.ai/dashboard/keys). When they paste it,
  persist it:
  ```
  bash ${CLAUDE_SKILL_DIR}/scripts/fal_key.sh save <key>
  ```
  This writes `~/.clipspal/fal_key` (chmod 600). Future sessions don't
  need to ask again. `fal_submit.py` / `fal_poll.py` read it
  automatically — you do NOT need to `export FAL_KEY`.

### 0d. Gather the rest of the inputs

Ask the user (in one message, not three) for:

1. **Project description** — what is this content for? (one paragraph)
2. **Broll folder path** — absolute path to a folder of `.mp4`/`.mov`
   files you already have. **If the user gives a file path, use its
   parent directory.** (If they have none, point them at TikTok
   downloaders, royalty-free libraries, or screen recordings of their
   product.)
3. **Output folder** — defaults to `<broll_folder>/clipspal-hooks-output/`
   so videos land right next to the source broll, not in some unrelated
   cwd. The user can override, but NEVER default to `./clipspal-hooks/`
   in the current working directory — that's how outputs end up in
   random folders the user can't find.
4. **Language** — defaults to "en".

Then validate the broll folder:
```
bash ${CLAUDE_SKILL_DIR}/scripts/check_broll.sh <broll_folder>
```
Exit 0 + file list → continue. Exit 1 → tell user the folder is empty
or missing, ask for a fixed path.

When confirming back to the user, **print the absolute output path** so
they can see exactly where the videos will land. e.g.
`Output: /Users/x/Desktop/myproj/broll/clipspal-hooks-output/`.

### 0e. Print the cost estimate + confirm

Before generating, print:

> This run will use your fal.ai credits:
>   - 5 Gemini 3.1 Flash Image character stills at 1K (~USD 0.40)
>   - 5 Vidu 3s reaction clips (~USD 0.75)
>   - Total: ~USD 1.15
> Reply "yes" to proceed.

(Use "USD 0.XX" instead of "$0.XX" — bare `$0` gets substituted with the
slash-command's first arg when the runbook is rendered, producing
nonsense like "generate.20".)

**Wait for explicit "yes"** before moving on.

## STEP 1 — Initialize project workspace

```
export PROJECT_DIR=<chosen output folder, absolute or ./relative>
mkdir -p $PROJECT_DIR/{characters,clips,payloads,output}
python3 ${CLAUDE_SKILL_DIR}/scripts/state.py init <slug>
python3 ${CLAUDE_SKILL_DIR}/scripts/state.py summary
```

If `state.json` already existed in that folder, this is a **resume** —
keep going from the first non-done step. Tell the user "Picking up where
we left off."

## STEP 2 — Matrix (you, no API)

Read `${CLAUDE_SKILL_DIR}/prompts/matrix.md` and write `<wd>/matrix.json`. Then:
```
python3 ${CLAUDE_SKILL_DIR}/scripts/state.py set matrix done
```

## STEP 3 — CHECKPOINT 1: matrix approval (mandatory)

Show the user the 5 rows in a short table (id, ethnicity, setting, emotion,
framing-confirms-centered). Ask:

> Approve these 5 characters, or want me to regenerate any rows?

Wait for the user. Accept: "good"/"approved"/"yes" → proceed; "regenerate
row N", "regen 2,4", "regen all" → rewrite those rows and re-checkpoint.

## STEP 4 — Hooks (you, no API)

Read `${CLAUDE_SKILL_DIR}/prompts/hooks.md` and `${CLAUDE_SKILL_DIR}/reference/hook-library.json`.
Pick 5 templates, fill in slots in audience language, write
`<wd>/hooks.json` with `n`, `text`, and `template_id`. Then:
```
python3 ${CLAUDE_SKILL_DIR}/scripts/state.py set hooks done
```

## STEP 5 — Characters (gemini-3.1-flash-image-preview, 5 parallel jobs)

Each character is a still image — the first frame Vidu will animate from
next step. Build the prompt from each matrix row using the template in
`${CLAUDE_SKILL_DIR}/reference/fal-endpoints.md` (which REQUIRES centered
framing language — use it verbatim).

Write `<wd>/payloads/character_<n>.json`:
```json
{
  "prompt": "<built prompt>",
  "num_images": 1,
  "output_format": "png",
  "aspect_ratio": "9:16",
  "resolution": "1K"
}
```

Submit all 5:
```
for n in 1 2 3 4 5; do
  python3 ${CLAUDE_SKILL_DIR}/scripts/fal_submit.py characters $n fal-ai/gemini-3.1-flash-image-preview \
    $PROJECT_DIR/payloads/character_$n.json &
done; wait
```

Poll all 5:
```
for n in 1 2 3 4 5; do
  python3 ${CLAUDE_SKILL_DIR}/scripts/fal_poll.py characters $n &
done; wait
```

## STEP 6 — CHECKPOINT 2: character approval (mandatory)

Before any clip job runs, show all 5 character PNGs
(`<wd>/characters/01.png` … `05.png`) using the Read tool so the user
can see them inline. Then ask:

> Approve these characters? "yes" to animate them into 3s clips
> (~USD 0.75), "regen N" (e.g. "regen 2,4") to redo specific characters,
> "regen all" to redo all five.

**Wait for an explicit answer.** Do not submit clip jobs until approval.

On "regen N":
```
python3 ${CLAUDE_SKILL_DIR}/scripts/state.py reset characters 2,4
```
…then update those matrix rows per user feedback, re-submit those slots,
re-poll, re-checkpoint.

## STEP 7 — Hook clips (Vidu q3 i2v, 5 parallel jobs)

Get each character's fal CDN URL:
```python
import json, urllib.request, os
state = json.load(open(os.environ["PROJECT_DIR"] + "/state.json"))
key = open(os.path.expanduser("~/.clipspal/fal_key")).read().strip() if not os.environ.get("FAL_KEY") else os.environ["FAL_KEY"]
for slot in state["characters"]:
    rid = slot["request_id"]
    req = urllib.request.Request(
        f"https://queue.fal.run/fal-ai/gemini-3.1-flash-image-preview/requests/{rid}",
        headers={"Authorization": f"Key {key}"})
    # ^ matches the model_id submitted in step 5. If you change models,
    #   change this URL too.
    print(slot["n"], json.load(urllib.request.urlopen(req))["images"][0]["url"])
```

Write `<wd>/payloads/clip_<n>.json`:
```json
{
  "image_url": "<character n fal CDN url from previous step>",
  "prompt": "<motion prompt from matrix row via reference/fal-endpoints.md>",
  "duration": 3
}
```

Submit + poll with `kind=clips`, `model_id=fal-ai/vidu/q3/image-to-video`.

## STEP 8 — Assemble (local)

**Use the script. Do NOT write your own shell loop.** A previous version
of this runbook asked the LLM to drive a 1..5 loop in the user's shell,
and zsh's 1-indexed arrays vs bash's 0-indexed arrays caused off-by-one
bugs (hook 1 → video 2, hook 5 dropped). The script reads `hooks.json`
directly, so the indexing is deterministic regardless of shell.

```
bash ${CLAUDE_SKILL_DIR}/scripts/assemble_all.sh <wd> <broll_folder>
```

The script handles:
- Round-robin pairing across the broll files (reuses from the top if
  fewer broll files than hooks).
- Single-clip fan-out: if `clips/NN.mp4` doesn't exist for a slot, it
  falls back to `clips/01.mp4`. So the "render 1 clip, produce 5 final
  variants" flow works without any special-case code.
- Parallel ffmpeg jobs, one per output.

When it exits 0:
```
python3 ${CLAUDE_SKILL_DIR}/scripts/state.py set assembly done
```

Print the output paths and `open <wd>/output/` so the user sees them.

## Resume / failure recipes

### Interrupted mid-run
User comes back, runs the skill again from the same folder. Step 1 detects
existing `state.json` → tells the user "resuming". Steps already `done`
are skipped. Pending slots get re-polled.

### A specific Vidu clip failed
```
python3 ${CLAUDE_SKILL_DIR}/scripts/state.py reset clips 3
python3 ${CLAUDE_SKILL_DIR}/scripts/fal_submit.py clips 3 fal-ai/vidu/q3/image-to-video \
  $PROJECT_DIR/payloads/clip_3.json
python3 ${CLAUDE_SKILL_DIR}/scripts/fal_poll.py clips 3
```

### Permission prompt fatigue
Mention to the user: copy `${CLAUDE_SKILL_DIR}/reference/permissions-suggested.json`
into `<their cwd>/.claude/settings.local.json` to allowlist the exact
commands this skill runs.

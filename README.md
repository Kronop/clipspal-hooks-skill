# ClipsPal Hooks — a Claude Code skill

Drop in your b-roll, describe what you do, get 5 TikTok-ready videos with
AI hook clips + burned-in captions. No signup, no watermark, runs locally
in Claude Code.

Built by [ClipsPal](https://clipspal.com). The full pipeline (scripts,
voiceover, subtitles, posting) lives in the app.

![hero](./docs/hero.png) <!-- optional -->

## How it works

1. You describe your project and point at a folder of your existing b-roll.
2. The skill generates a 5-row character matrix (different demographics,
   settings, reactions) tailored to your audience.
3. Each row becomes a centered, photorealistic UGC first frame via
   `fal-ai/nano-banana`.
4. Each frame is animated into a 3-second reaction clip via
   `fal-ai/vidu/q3/image-to-video`.
5. Five hook lines are picked from a curated library and tailored to your
   project.
6. Local `ffmpeg` concatenates each hook clip with one of your b-roll
   files and burns in the hook line (TikTok Sans Bold + Apple color
   emoji, same renderer as the prod free tool).

Output: 5 ready-to-post 1080×1920 mp4s in `./clipspal-hooks/output/`.

## Cost per run

You bring your own [fal.ai API key](https://fal.ai/dashboard/keys). One
run costs your fal account roughly:

- 5 nano-banana character images: ~$0.20
- 5 Vidu 3-second clips: ~$0.75
- **Total: ~$0.95**

## Install

Clone into your Claude Code skills folder:

```bash
git clone https://github.com/Kronop/clipspal-hooks-skill \
  ~/.claude/skills/clipspal-hooks
```

Then make sure you have the dependencies:

```bash
# macOS
brew install ffmpeg-full && brew unlink ffmpeg && brew link --overwrite ffmpeg-full
python3 -m pip install --user Pillow

# Linux
sudo apt install ffmpeg python3-pil
```

(The skill checks these for you at step 0 and prints fix commands if
anything is missing.)

## Use

Open Claude Code in any folder that contains your b-roll, then say:

```
/clipspal-hooks make tiktok hooks for my protein tracker app
```

…or describe it in plain English. The skill will:

1. Verify your prerequisites.
2. Ask for your fal.ai API key (once — persists to `~/.clipspal/fal_key`).
3. Ask for the absolute path to your b-roll folder and an output folder
   name (default `./clipspal-hooks/`).
4. Generate a character matrix and **wait for your approval**.
5. Render 5 first frames and **wait for your approval again** before
   spending the bigger fal credits on Vidu.
6. Render the clips, assemble the videos, and open the output folder.

If you Ctrl-C mid-run, just re-run the same command from the same folder —
the skill picks up exactly where it left off.

## Tune the look

- Want a different hook text style? Edit `scripts/render_overlay.py`
  (font size, color, stroke, position) — same parameters as the prod
  Lambda renderer.
- Want different reaction archetypes? Edit `prompts/matrix.md`.
- Want different hook templates? Edit `reference/hook-library.json`
  (curated copy of the prod hook library).

## What's inside

```
clipspal-hooks/
├── SKILL.md                 # The runbook Claude Code follows.
├── prompts/                 # Prose prompts: matrix + hook selection.
├── scripts/
│   ├── state.py             # state.json + flock — dedupe engine.
│   ├── fal_submit.py        # Submit one fal job per slot, atomic.
│   ├── fal_poll.py          # Poll + download artifact, idempotent.
│   ├── render_overlay.py    # TikTok Sans + Apple color emoji PNG renderer.
│   ├── assemble.sh          # ffmpeg concat + overlay.
│   ├── check_prereqs.sh
│   ├── check_broll.sh
│   └── fal_key.sh
├── fonts/                   # TikTok Sans Bold + Noto fallbacks.
└── reference/
    ├── fal-endpoints.md
    ├── hook-library.json    # The prod hook library.
    └── permissions-suggested.json
```

## License

Code: MIT. See `LICENSE`.

Fonts are bundled under their respective licenses (Noto under SIL Open
Font License). Apple emoji PNGs are fetched at runtime from
[emoji-datasource-apple](https://www.npmjs.com/package/emoji-datasource-apple)
and cached locally — they are not redistributed in this repo.

---

ClipsPal posts 2 AI TikToks to grow your app, every day — start free at
[clipspal.com](https://clipspal.com).

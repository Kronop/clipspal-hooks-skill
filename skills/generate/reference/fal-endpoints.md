# fal.ai endpoints used by this skill

All HTTP calls go through `scripts/fal_submit.py` and `scripts/fal_poll.py`.
Auth: `Authorization: Key $FAL_KEY`.

Queue API:
- Submit:   `POST https://queue.fal.run/<model_id>` (returns `{request_id}`)
- Status:   `GET  https://queue.fal.run/<model_id>/requests/<request_id>/status`
- Result:   `GET  https://queue.fal.run/<model_id>/requests/<request_id>`

## Models

### `fal-ai/gemini-3.1-flash-image-preview` — character still
Used for: rendering each character matrix row into a still image. This
still is the first frame Vidu will animate from in the next step.

Same model the ClipsPal prod pipeline uses (Nano Banana 2 / Gemini 3.1
Flash Image). Replaces the older `fal-ai/nano-banana` (Gemini 2.5).

Input payload (write to `params.json` and pass to `fal_submit.py`):

```json
{
  "prompt": "<built from one matrix row — see prompt template below>",
  "num_images": 1,
  "output_format": "png",
  "aspect_ratio": "9:16",
  "resolution": "1K"
}
```

`resolution` options: `0.5K | 1K | 2K | 4K`. Default `1K` matches what
the prod pipeline produces and keeps cost reasonable. Bump to `2K` for
sharper hero stills (≈1.5× cost).

**Prompt template (build per row):**

```
Vertical 9:16 portrait, photorealistic UGC TikTok screenshot aesthetic, NOT
cinematic, NOT studio. A {age}-year-old {ethnicity} {gender} in {setting}.
The subject is centered horizontally in the frame, face fully visible and
NOT cropped, head positioned in the upper-middle third of the 9:16 canvas.
Lighting: {lighting}. Color palette: {color_palette}. Framing: {framing}.
Pose: {first_frame_pose}. Slight grain, subtle phone-camera imperfection.
No text, no captions, no watermark. Do not push the subject to the left or
right edge; do not crop half of the face.
```

### `fal-ai/vidu/q3/image-to-video` — 3s hook clip
Used for: animating each character still into a 3s reaction clip.

Same endpoint, payload shape, and prompt structure the prod ClipsPal
free-tool pipeline (`scripts/gen-free-hook-video.mjs`) uses — keep this
file in sync if prod changes.

Input payload:

```json
{
  "image_url": "<data uri or signed url to the character still>",
  "prompt": "<motion description, see template below>",
  "duration": 3,
  "resolution": "720p",
  "audio": false
}
```

Notes:
- Duration is an integer in seconds. We always pass `3`.
- `resolution` options: `360p | 540p | 720p | 1080p`. Prod uses `720p`.
  Drop to `540p` to halve the per-second cost (see Cost section).
- `audio: false` — Vidu i2v is silent natively; we set it explicit so
  there's no ambiguity downstream in `assemble.sh`.
- `image_url` can be a `data:image/png;base64,...` URI or the fal CDN
  url returned by the gemini-3.1-flash-image-preview result. Easiest:
  pass the fal CDN url directly from the character-render response.

**Motion prompt template (build per row — mirrors prod's 4-part
structure for visual consistency with the prod free tool):**

```
Character action: Starting from the exact pose in the first frame
({first_frame_pose}), the character {emotion}. The motion should feel
naturalistic and complete its arc within 3 seconds, peaking around the
midpoint and settling at the end. The character's identity, clothing,
hair, and the surrounding room must remain perfectly consistent with
the first frame — only the described motion changes.

Camera movement: {camera_move}. Smooth and steady, no shake.

Animation beyond character: Subtle ambient life — slight breathing
rhythm in the chest, faint shifting of light or air in the room.
Otherwise the environment is still.

Constraints: No text, captions, subtitles, watermarks, or written
words anywhere in the video. No new characters or objects appear. No
cuts. No transitions. Photorealistic; lighting, color, and identity
continuous with the first frame.
```

## Cost reference (approximate, user pays)

Per-image on `fal-ai/gemini-3.1-flash-image-preview` is fixed by
resolution:
- 0.5K: ~$0.06
- 1K:   ~$0.08  (our default — matches prod)
- 2K:   ~$0.12
- 4K:   ~$0.16

Per-second on `fal-ai/vidu/q3/image-to-video`:
- 360p / 540p: ~$0.07/sec → 3s ≈ $0.21
- 720p:        ~$0.154/sec → 3s ≈ $0.46  (our default — matches prod)
- 1080p:       ~$0.154/sec → 3s ≈ $0.46

Per-run totals (5 characters + 5 clips):
- 1K char + 540p clip: 5×$0.08 + 5×$0.21 = **~$1.45 per run**  (budget mode)
- 1K char + 720p clip: 5×$0.08 + 5×$0.46 = **~$2.70 per run**  (default, matches prod)
- 2K char + 720p clip: 5×$0.12 + 5×$0.46 ≈ **~$2.90 per run**  (max quality)

Note: prior versions of this skill quoted ~$0.95 for the run — that
was wrong on both axes (used the older nano-banana model and a stale
Vidu per-clip price). Real cost is closer to ~$2.70 at the prod-match
defaults.

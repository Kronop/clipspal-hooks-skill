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

Input payload:

```json
{
  "image_url": "<data uri or signed url to the character still>",
  "prompt": "<motion description from the matrix row>",
  "duration": 3
}
```

Notes:
- Duration is an integer in seconds. We always pass `3`.
- `image_url` can be a `data:image/png;base64,...` URI or the fal CDN
  url returned by the gemini-3.1-flash-image-preview result. Easiest:
  pass the fal CDN url directly from the character-render response.
- **Motion prompt template (build per row):**

```
{emotion}. Camera: {camera_move}. Subject reaction lands within 2 seconds.
Keep environment stable. No cuts, no text, no on-screen captions.
```

## Cost reference (approximate, user pays)

Per-image pricing on `fal-ai/gemini-3.1-flash-image-preview` is fixed by
resolution:
- 0.5K: ~$0.06
- 1K:   ~$0.08  (our default)
- 2K:   ~$0.12
- 4K:   ~$0.16

Vidu q3 image-to-video (3s): ~$0.15 per clip.

5 characters at 1K + 5 clips ≈ **~$1.15 per run**.
5 characters at 2K + 5 clips ≈ ~$1.35 per run.

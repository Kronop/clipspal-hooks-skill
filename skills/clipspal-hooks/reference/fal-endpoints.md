# fal.ai endpoints used by this skill

All HTTP calls go through `scripts/fal_submit.py` and `scripts/fal_poll.py`.
Auth: `Authorization: Key $FAL_KEY`.

Queue API:
- Submit:   `POST https://queue.fal.run/<model_id>` (returns `{request_id}`)
- Status:   `GET  https://queue.fal.run/<model_id>/requests/<request_id>/status`
- Result:   `GET  https://queue.fal.run/<model_id>/requests/<request_id>`

## Models

### `fal-ai/nano-banana` — character still
Used for: rendering each character matrix row into a still image. This
still is the first frame Vidu will animate from in the next step.

Input payload (write to `params.json` and pass to `fal_submit.py`):

```json
{
  "prompt": "<built from one matrix row — see prompt template below>",
  "num_images": 1,
  "output_format": "png",
  "aspect_ratio": "9:16"
}
```

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
  "image_url": "<data uri or signed url to the character still from nano-banana>",
  "prompt": "<motion description from the matrix row>",
  "duration": 3
}
```

Notes:
- Duration is an integer in seconds. We always pass `3`.
- `image_url` can be a `data:image/png;base64,...` URI or the fal CDN url
  returned by the nano-banana result. Easiest: pass the fal CDN url directly
  from the nano-banana response.
- **Motion prompt template (build per row):**

```
{emotion}. Camera: {camera_move}. Subject reaction lands within 2 seconds.
Keep environment stable. No cuts, no text, no on-screen captions.
```

## Cost reference (approximate, user pays)
- nano-banana: ~$0.04 per image (5 images ≈ $0.20)
- vidu q3 image-to-video (3s): ~$0.15 per clip (5 clips ≈ $0.75)
- 5 characters + 5 clips ≈ $0.95 per run

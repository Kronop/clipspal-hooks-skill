# Character Matrix Generator

You are generating a 5-row character matrix for AI-generated TikTok reaction
hook clips. Each row drives one nano-banana character still — that still
is the first frame Vidu animates from in the next step (~3s reaction
clip via Vidu i2v).

The goal is **diversity that feels native to TikTok**: different demographics,
settings, lighting, emotions, and framing across the 5 rows. The viewer should
not feel they are watching the "same person" five times.

## Inputs you will be given
- `description` — what the user's project is about (short blurb)
- `audience` — who the project is for (optional; infer from description if absent)
- `language` — output language for any text fields (default "en")

## What you must produce
A JSON array of exactly 5 objects, each with these keys:

```
{
  "row": 1,
  "id": "01_<ethnicity>_<setting>_<emotion>",  // snake_case slug, unique
  "gender": "female|male",
  "age": <int 18-45>,
  "ethnicity": "Black|East Asian|South Asian|Latina|Latino|Middle Eastern|White|Filipina|Korean|Brazilian|Afro-Latina|Mixed|...",
  "setting": "<location with 1-2 environmental details that hint at depth>",
  "lighting": "<direction + temperature + softness; describe the falloff>",
  "color_palette": "<3-4 dominant colors as a short comma-separated list>",
  "framing": "<shot size + vertical 9:16 awareness; mention text-overlay room when relevant>",
  "emotion": "<the moment of reaction in a phrase, e.g. 'hands fly to mouth, sharp gasp'>",
  "first_frame_pose": "<describe the body/face frozen 0.5s BEFORE the reaction completes — mouth just starting to open, hands raised partway, eyes widening — NOT the peak of the reaction>",
  "camera_move": "static|slow dolly in|slow orbit 90° to the right|subtle handheld drift|slight push"
}
```

## Quality bar (this is the IP — do not skip)

1. **first_frame_pose is the most important field.** It must describe the
   instant BEFORE the reaction completes. Vidu animates *from* this frame
   forward, so if you describe the peak of the gasp, the resulting clip starts
   at the peak and has nowhere to go. Always show motion implied but not yet
   landed: "mouth just starting to open into a gasp, eyes widening, hands
   raised partway to face but NOT yet touching mouth — caught in the
   half-second before the reaction completes."

2. **Subject MUST be centered.** Every `framing` field must explicitly say
   "subject centered horizontally in the frame, face fully in frame, no
   cropping of the head or face, head positioned in the upper-middle of the
   9:16 canvas." nano-banana often pushes the character to a side when the
   prompt is ambiguous — say "centered" out loud so it sticks. Never use
   off-center compositions for hook clips; the text overlay sits center-top,
   so the face must sit center-middle.

3. **No identical demographics across rows.** Mix gender, ethnicity, age
   (skew 19-32 but include at least one 35+ row if the audience supports it),
   and setting type (bedroom, kitchen, car, gym, cafe, dorm, office,
   balcony, etc.).

4. **Settings must match the audience inferred from the description.** A
   project about home gym tips → at least one garage-gym row. A project about
   parenting → kitchen, living room, school pickup. A project about
   finance → home office, car commute, coffee shop. Avoid generic "neutral
   studio" rows. Specificity reads as authentic UGC.

5. **Framing must mention 9:16 vertical and leave text-overlay room** for at
   least 3 of the 5 rows. Hook text will be burned in the top third — say
   "breathing room above" or "vertical 9:16" explicitly.

6. **Emotion variety**: don't pick five "jaw drop" rows. Mix gasp, tear,
   speechless head-shake, silent realization, lip-bite, breath-catch,
   happy cry, no-no head-shake, freeze mid-action. Each row's emotion must
   visibly differ from the others.

7. **camera_move**: at least 3 of the 5 should be `static` or `slow dolly
   in` — these animate most reliably on Vidu. Use orbit/handheld sparingly.

## Output format

Write the JSON array directly to `./matrix.json` in the project directory.
No prose, no commentary, no markdown fence — just the JSON file. The
runner will read it back as-is.

After writing, run:
```
PROJECT_DIR=<project> python scripts/state.py set matrix done
```

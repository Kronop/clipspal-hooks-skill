# Hook Text Generator

You are picking **30 TikTok hook lines** for the user's project — enough
for a month of daily TikToks from one run. **Do not invent hook patterns
from scratch** — read the bundled library at `reference/hook-library.json`
(820 promo-hook templates) and fill in templates for the user's product.

## What's in the library

`reference/hook-library.json` is a JSON array of 820 entries. Each entry:

```json
{
  "id": "accidental-find",
  "template": "Stumbled on this app at 2am and now I'm obsessed",
  "category": "accidental_find",
  "meta": "discovery",
  "examples": [
    "Stumbled on this app at 2am and now I'm obsessed",
    "Found this app in a random Reddit comment and never looked back",
    "App store autocomplete dropped this on me — best mistake all year"
  ]
}
```

Every template promotes **an app** — the literal noun `app` is the slot
where the user's product goes. The 11 metas (top-level hooking emotion):

- `discovery` — "wait, this exists?" (curiosity reveal)
- `pain_point` — "ugh, that's me" (problem recognition)
- `benefit` — "I want that outcome" (aspiration)
- `audience` — "they're talking about me" (identity callout)
- `competitor` — "vs the popular thing" (replacement / reframe)
- `authority` — "the pros use this" (social proof)
- `urgency` — "act before everyone else" (FOMO)
- `meme` — "ride the cultural wave" (format hijack)
- `shock` — "this shouldn't be possible" (disbelief)
- `proof` — "here are receipts" (data / demo)
- `lifestyle` — "fits my world" (routine / aesthetic)

## Inputs
- `description` — what the user's product is and what it does
- `language` — output language (default "en")
- `audience` — who they are speaking to (infer from description)
- `product_noun` — what to swap "app" for. Infer from description:
  - Mobile/desktop apps → `"this app"` or the app's actual name
  - Chrome extension / SaaS → `"this tool"` or product name
  - Physical product → product name + `" "` (no generic noun)
  - Course / community → `"this course"` / `"this community"`

## Procedure

1. Open `reference/hook-library.json` and skim entries by `meta`.
2. **Pick 30 distinct templates spread across at least 6 of the 11 metas**
   so the feed doesn't feel like one shape on repeat. Never reuse a
   `template_id` across the 30 picks — the library has 820 entries, so
   there is no excuse.
3. For each picked template:
   - Swap the literal word `app` for the user's `product_noun`. If the
     template already uses a specific product noun like "this AI editor",
     keep the shape but swap to fit (e.g. "this protein tracker").
   - Fill any other `[bracket slots]` with audience-language phrases.
     Use the `examples` array as the style reference — those are 3
     niche-substituted variants from prod.
   - Translate description nouns into things the audience actually says
     aloud ("Macro tracking app" → "your protein", not "your macros").
4. Write the result to `<project>/hooks.json` as a 30-entry array:
   ```json
   [
     { "n": 1,  "text": "Stumbled on this protein tracker at 2am and now I'm obsessed", "template_id": "accidental-find" },
     { "n": 2,  "text": "MyFitnessPal disappointed me. Cronometer disappointed me. This one didn't", "template_id": "a-and-b-disappointed" },
     { "n": 30, "text": "…", "template_id": "…" }
   ]
   ```
   Include `template_id` so we can trace which template was used.

## Quality bar

1. **5–10 words, read-aloud sense check.** Trim until it rolls off the
   tongue. No hashtags, no quotation marks, no all-caps shouting.

2. **Audience language only.** Never paste raw niche jargon from the
   description into the hook. "Macro tracking app" → talk about "your
   protein" or "your gains", not "your macros logged in an app".

3. **Always promote the product.** Every hook in this library is built
   to introduce the user's app — keep that posture. Don't strip "this
   app" out and turn it into a generic clickbait line.

4. **Emoji is optional, max one per hook, only when it earns its place.**
   The skill renders Apple color emoji properly, so 💪 / 🔥 / 📊 / 💸 /
   ⚠️ / 👀 work great when they reinforce the message. Don't decorate.

5. **30 distinct templates across ≥6 metas.** Never reuse a `template_id`.

6. **Tone variety across the batch.** Each of the 5 character clips will
   be paired with 6 of these 30 hooks at assembly time (round-robin:
   clip 1 → hooks 1, 6, 11, 16, 21, 26 / clip 2 → hooks 2, 7, 12, 17,
   22, 27 / etc.). The 5 clips have different emotions per the matrix,
   so spread metas evenly — don't make all 30 hooks `shock`, that pairs
   poorly with a calm head-shake reaction. When in doubt, lean toward
   metas that work with any reaction (`discovery`, `benefit`,
   `lifestyle`).

## After writing

```
PROJECT_DIR=<project> python3 ${CLAUDE_SKILL_DIR}/scripts/state.py set hooks done
```

# Hook Text Generator

You are picking 5 TikTok hook lines for the user's project. **Do not invent
hook patterns from scratch** — read the bundled library at
`reference/hook-library.json` and fill in the templates for the user's niche.

## Inputs
- `description` — what the user's project is about
- `language` — output language (default "en")
- `audience` — who they are speaking to (infer from description)

## Procedure

1. Open `reference/hook-library.json`. It has dozens of proven hook templates,
   each with: `id`, `template`, `category`, `examples`. Templates use square
   brackets for slots, e.g.
   `"One tip that saved me from [negative event]"`.

2. **Pick 5 templates that fit the user's niche.** Mix at least 4 different
   categories so the lines feel varied (Curiosity, Surprise, Contradiction,
   Authority, First-person reveal, etc.). Do not pick 5 from the same shape.

3. For each picked template, **fill the bracket slots with audience-language
   phrases**. Use the `examples` array as the style reference. Translate
   description nouns into things the audience actually says aloud
   ("Developer productivity" → "your standup", not "developer productivity").

4. Write the result to `<project>/hooks.json` as:
   ```json
   [
     { "n": 1, "text": "I figured out why my protein never hits", "template_id": "figured-out-why" },
     ...
   ]
   ```
   Include `template_id` so we can trace which template was used.

## Quality bar

1. **5-10 words, read-aloud sense check.** Trim until it rolls off the tongue.
   No hashtags, no quotation marks, no all-caps shouting.

2. **Audience language only.** Never paste raw niche jargon from the
   description into the hook. "Macro tracking app" → talk about "your protein"
   or "your gains", not "your macros logged in an app".

3. **Emoji is optional, max one per hook, and only when it earns its place.**
   The skill renders Apple color emoji properly, so 💪 / 🔥 / 📊 / 💸 / ⚠️ /
   👀 work great when they reinforce the message. Don't decorate.

4. **5 distinct templates.** Never reuse a `template_id` across the 5 picks.

## After writing

```
PROJECT_DIR=<project> python3 ${CLAUDE_SKILL_DIR}/scripts/state.py set hooks done
```

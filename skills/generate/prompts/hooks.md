# Hook Text Generator

You are picking **30 TikTok hook lines** for the user's project — enough
for a month of daily TikToks from one run. **Do not invent hook patterns
from scratch** — read the bundled library at `reference/hook-library.json`
(500+ proven templates) and fill in the templates for the user's niche.

## Inputs
- `description` — what the user's project is about
- `language` — output language (default "en")
- `audience` — who they are speaking to (infer from description)

## Procedure

1. Open `reference/hook-library.json`. It has 500+ proven hook templates,
   each with: `id`, `template`, `category`, `examples`. Templates use square
   brackets for slots, e.g.
   `"One tip that saved me from [negative event]"`.

2. **Pick 30 distinct templates that fit the user's niche.** Spread them
   across at least 8 different categories so the feed doesn't feel like
   one shape on repeat (Curiosity, Surprise, Contradiction, Authority,
   First-person reveal, Warning, How-to, Tier-list, Question, etc.).
   Never reuse a `template_id` across the 30 picks.

3. For each picked template, **fill the bracket slots with audience-language
   phrases**. Use the `examples` array as the style reference. Translate
   description nouns into things the audience actually says aloud
   ("Developer productivity" → "your standup", not "developer productivity").

4. Write the result to `<project>/hooks.json` as a 30-entry array:
   ```json
   [
     { "n": 1, "text": "I figured out why my protein never hits", "template_id": "figured-out-why" },
     { "n": 2, "text": "Nobody talks about this protein mistake", "template_id": "nobody-talks-about" },
     ...
     { "n": 30, "text": "...", "template_id": "..." }
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

4. **30 distinct templates.** Never reuse a `template_id` across the 30
   picks. The library has 500+, so there's no excuse.

5. **Tone variety across the batch.** Each of the 5 character clips will
   be paired with 6 of these 30 hooks at assembly time (round-robin: clip
   1 → hooks 1, 6, 11, 16, 21, 26 / clip 2 → hooks 2, 7, 12, 17, 22, 27
   / etc.). The 5 clips have different emotions per the matrix, so:
   - Don't make all 30 hooks "shocking discovery" — that pairs poorly
     with a calm head-shake reaction.
   - Spread emotional valences evenly: surprise, regret, warning,
     contradiction, authority-flex, curiosity, etc.
   - When in doubt, lean generic — hooks that work with any reaction.

## After writing

```
PROJECT_DIR=<project> python3 ${CLAUDE_SKILL_DIR}/scripts/state.py set hooks done
```

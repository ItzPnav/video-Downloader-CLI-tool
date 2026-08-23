---
name: content-repurposer
description: Take ONE piece of source content — a transcript, blog post, notes, pasted text, or a URL/YouTube link — and explode it into a full multi-channel content kit (5 LinkedIn posts, 3 short-form video scripts, 1 email newsletter, 1 X/Twitter thread, 3–5 carousel/pull-quote ideas) plus a 1-week posting calendar. Use when the user runs `/content-repurposer`, says "repurpose this", "turn this into posts/content", "I just recorded/wrote [X]", "give me content from this", or otherwise hands over a single source asset and wants it spread across channels.
---

# Content Repurposer

Hand over ONE thing you made — a recorded video, a blog post, a podcast transcript, a set of notes, a long email — and get back a week of ready-to-post content across every channel. This skill does the unglamorous, time-consuming part: pulling the best ideas out of a long asset and rewriting them, in the right shape and length, for LinkedIn, short-form video, email, X, and carousels. It is built to be portable — it makes no assumptions about a specific person or brand and asks for the tone if it isn't given.

## When to use

- The user types `/content-repurposer`
- "Repurpose this [video / podcast / blog / transcript / notes]"
- "Turn this into posts" / "turn this into content for the week"
- "I just recorded [X]" / "I just wrote [X]" — and they paste it or link it
- They have one strong asset and want it spread across LinkedIn, short-form, email, X, and carousels
- Any time the input is ONE source and the desired output is many pieces across channels

This is *not* the right skill for generating content from scratch with no source, or for packaging a single YouTube upload (use a dedicated packaging skill for that).

## Workflow

1. **Ingest the source.** Accept any of:
   - **Pasted text** — use it directly.
   - **A local file** (transcript, blog, notes, `.txt` / `.md` / `.srt`) — read it.
   - **A URL or YouTube link** — best-effort: if web-fetch tooling is available, fetch the page or transcript. If it's a YouTube link and no transcript can be retrieved, **ask the user to paste the transcript or captions** rather than guessing the content. Never fabricate what the source said.

2. **Confirm the voice before drafting.** In priority order:
   - If the user states a brand voice or tone, use it.
   - Else, if a brand-voice / tone-of-voice file exists in the project, read it and match it.
   - Else, infer the tone from the source itself (formal vs casual, technical vs plain) and **state the tone you're going to use in one line**, then proceed. If the source is too thin to infer tone, **ask the user** for the tone/audience before drafting. Do not assume any individual's personal voice.

3. **Extract the core (Step 1).** Pull the **5–8 strongest ideas, hooks, and quotable lines** from the source — the arguments, contrarian takes, frameworks, stories, stats, and one-liners that can each stand alone. List these first as the raw material the rest is built from.

4. **Build the kit (Step 2).** Produce all of the following, each piece tied back to one of the core ideas:
   - **5 LinkedIn posts** — each with a scroll-stopping first line, a body (short paragraphs / line breaks), and exactly one CTA.
   - **3 short-form video scripts** (Reels / TikTok / Shorts) — each with a hook, a 3–4 beat body, and on-screen text suggestions per beat.
   - **1 email newsletter** — subject line + preview text + body.
   - **1 X/Twitter thread** — 6–8 tweets, hook tweet first, payoff/CTA last.
   - **3–5 pull-quote / carousel graphic ideas** — the exact line plus a visual suggestion for each.

5. **Map the week (Step 3).** Lay out a 1-week posting calendar assigning each piece to a day and channel, so the user knows what to post when.

6. **Deliver the package** in the format below, then offer to expand any one piece into a finished draft or adjust tone/channels.

## Output package format

---

## ♻️ Content Kit — [Source title / topic]

**Source:** [pasted text / file path / URL]
**Voice:** [stated by user / matched from brand file / inferred — name it]

---

### 🔑 Core Ideas & Quotable Lines

1. [Idea / hook / quotable line]
2. …
*(5–8 total — the raw material everything below is built from.)*

---

### 💼 LinkedIn Posts (5)

**Post 1**
> [Scroll-stopping first line]

[Body — short paragraphs, line breaks for readability.]

**CTA:** [single call to action]

*(Repeat for Posts 2–5, each from a different core idea.)*

---

### 🎬 Short-Form Video Scripts (3)

**Script 1 — [working title]**
- **Hook (0–3s):** [spoken hook] · *on-screen: [text]*
- **Beat 1:** [line] · *on-screen: [text]*
- **Beat 2:** [line] · *on-screen: [text]*
- **Beat 3:** [line] · *on-screen: [text]*
- **Beat 4 / CTA:** [line] · *on-screen: [text]*

*(Repeat for Scripts 2–3.)*

---

### 📧 Email Newsletter (1)

- **Subject:** [subject line]
- **Preview:** [preview text]
- **Body:**

[Newsletter body — greeting, the angle, the payoff, one CTA.]

---

### 🐦 X / Twitter Thread (6–8 tweets)

1. [Hook tweet]
2. …
8. [Payoff + CTA]

---

### 🖼️ Carousel / Pull-Quote Ideas (3–5)

1. **Line:** "[exact pull-quote]" — **Visual:** [suggestion]
2. …

---

### 🗓️ 1-Week Posting Calendar

| Day | Channel | Piece |
|-----|---------|-------|
| Mon | LinkedIn | Post 1 |
| Mon | Short-form | Script 1 |
| Tue | X | Thread |
| Wed | LinkedIn | Post 2 |
| Thu | Email | Newsletter |
| Thu | Short-form | Script 2 |
| Fri | LinkedIn | Post 3 |
| … | … | … |

*(Spread the 5 LinkedIn posts, 3 scripts, thread, email, and carousels across the week — heaviest channel first, no two of the same format back-to-back.)*

---

## Notes for Claude

- **Never fabricate the source.** If you can't fetch a URL/YouTube transcript, ask the user to paste it rather than inventing what it said. Everything in the kit must trace back to a real core idea from the source.
- **Confirm the voice before you draft** when it isn't given — name the tone you're using in one line, or ask if the source is too thin to infer. Stay portable: do not assume any specific person's or brand's voice.
- **Each piece earns its place.** Tie every post, script, and thread back to one of the 5–8 core ideas — don't pad with filler or repeat the same point in five formats without a fresh angle.
- **Match each format's native shape.** LinkedIn = first-line hook + white space. Short-form = spoken hook in the first 3 seconds. Email = subject does the work. X = one idea per tweet. Don't paste the same paragraph into every channel.
- **One CTA per piece.** Keep calls to action specific and singular.
- **Keep it self-contained.** This skill should work in any workspace with no private dependencies — only read a brand-voice file if one already exists in the project.
- After delivering the kit, ask: **"Want me to expand any single piece into a full finished draft, or adjust the tone / swap out a channel?"**

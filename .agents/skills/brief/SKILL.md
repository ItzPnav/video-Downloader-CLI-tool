---
name: brief
description: Generate your morning briefing — pull live email, CRM deals, calendar, and (optionally) a YouTube channel snapshot in parallel, then synthesise into a structured daily brief (Focus, Priority Actions, Schedule, Pipeline Pulse, Content & Brand, Inbox Summary, Revenue Snapshot). Use when you run `/brief`, ask for your "morning briefing", "brief me", "what's on today", "give me my daily brief", or want your morning triage of inbox, pipeline, calendar, and channel.
---

# Brief

Generate your morning briefing. Pull live data from your connected tools (via Composio MCP or whatever integrations you have), synthesise it, and output a structured daily brief.

Execute the following steps in order. Pull all data in parallel where possible, then synthesise.

## Step 1 — Get today's date/time

Get the current local time (e.g. via your calendar tool's current-date-time call, using your own timezone). Use this to:
- Construct `time_min` = start of today (00:00:00) in your timezone as RFC3339
- Construct `time_max` = end of today (23:59:59) in your timezone as RFC3339
- Format today's date for the briefing header (e.g. "Thursday, 5 March")

## Step 2 — Pull all data in parallel

Call your connected tools simultaneously:

**Your email** (e.g. `GMAIL_FETCH_EMAILS` if you use Gmail)
- Fetch recent emails, focus on unread. Aim for the last 24-48 hours.
- Extract: sender, subject, short preview, timestamp. Flag anything that looks urgent, from a client, or that requires a reply.

**Your CRM** (e.g. `HUBSPOT_LIST_DEALS` if you use HubSpot)
- Retrieve all open deals.
- Extract: deal name, value, stage, owner, days since last activity/contact. Flag any deal silent for >5 days or with an overdue action.

**Your YouTube channel — OPTIONAL.** Skip this section entirely if you don't run a channel.
- If you want a channel snapshot, query your own channel using your channel handle `[YOUR_YOUTUBE_HANDLE]` (e.g. `YOUTUBE_GET_CHANNEL_STATISTICS` with `forHandle:"[YOUR_YOUTUBE_HANDLE]"`). Extract: subscriber count, total views.
- For latest video performance: list your channel's videos, take the newest video ID, then fetch its details with `parts:["snippet","statistics"]`. Extract: title, views, likes, published date.

**Your calendar** (e.g. `GOOGLECALENDAR_EVENTS_LIST_ALL_CALENDARS` if you use Google Calendar)
- Parameters: `time_min` and `time_max` from Step 1, `single_events: true`.
- Extract: all events today — name, time, attendees (if any). Ignore generic public-holiday calendar items.

**Revenue** — OPTIONAL. If you connect a payments tool (e.g. Stripe), pull today's/recent revenue. Otherwise skip and note: "Payments tool not connected — connect one to enable revenue data."

## Step 3 — Synthesise into the briefing

Output the briefing in this exact format:

---

## ☀️ Good morning — [Day, Date]

> **Focus:** [One sentence — the single most important thing today. Be specific. E.g. "Reply to the client to unblock onboarding" or "Prep for the discovery call at 9am."]

---

### 🔴 Priority Actions
*Things that need a decision or action from you today.*

List each item as:
- **[Name / Company]** — [What's needed and why it matters. Keep to one line.]
  `[suggested next action]`

Order by urgency. Max 5 items. If nothing is urgent, say so.

---

### 📅 Today's Schedule
*From your calendar.*

List each event:
- **[HH:MM]** — [Event name] [attendees if relevant]

If no events: "No meetings today."

---

### 💼 Pipeline Pulse
*Open deals snapshot.*

For each open deal:
- **[Deal name]** — [value] · [Stage] · [Owner] · [X days in stage]
  [One line of context or next action if flagged]

Summarise at the bottom: "Total pipeline: [X] across [N] deals."

---

### 📺 Content & Brand — OPTIONAL
*YouTube snapshot. Include only if you run a channel.*

- Subscribers: [N] (target: [your subscriber target])
- Latest video: "[Title]" — [views] views · [days] days ago
- [Any notable trend or action needed — e.g. "No video posted in X days — behind your cadence."]

---

### 📬 Inbox Summary
*Priority emails from the last 24-48 hours.*

List notable emails (clients, leads, team):
- **[Sender]** · [Subject] · [X hours/days ago] — [One-line summary]

Flag any that need an urgent reply.

---

### 💰 Revenue Snapshot
*(Connect a payments tool to enable this section.)*

---

## Notes for Claude

- If you keep your own client/team notes, cross-reference them when interpreting data — e.g. to label a deal's owner correctly or add context the CRM doesn't have.
- For deals owned by someone else on your team, only flag them if they need your input (e.g. something you need to approve).
- Keep the tone direct. This is a brief, not a report. No padding.
- If a tool call fails, note it clearly and continue with the rest.
- Treat the YouTube/Content section and the Revenue section as optional — omit cleanly if those tools aren't connected.
- After outputting the brief, ask: "Anything you'd like to dig into further?"

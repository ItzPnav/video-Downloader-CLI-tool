---
name: meeting-prep
description: Pull all context on a person or company before a call — calendar event, email thread history, CRM deal + contact, and your own client notes — into a one-page cheat sheet with Who They Are, Deal Context, Email History, Suggested Agenda, Talking Points, and Watch Out For. Use when you say `/meeting-prep`, ask to "prep for my call/meeting with [name]", "what do I need to know before the [company] call", "brief me on [person] before we speak", or want research on a prospect/client ahead of a discovery, proposal, or onboarding call.
---

# Meeting Prep

Pull everything you need before a call — calendar, email, CRM, and any client notes — and synthesise it into a single-page brief you can glance at on the way into the meeting. It should feel like you had an assistant do 20 minutes of research. This is a cheat sheet, not a report — direct, practical, no padding.

## When to use

- You type `/meeting-prep [person/company name]`
- "Prep me for the [name] call" / "brief me before my meeting with [company]"
- "What do I need to know before I speak to [person]?"
- Ahead of any discovery, proposal, or onboarding call where context lives across your email + CRM + notes
- When you want a quick read on a prospect or existing client before a scheduled event

## Workflow

1. **Identify the meeting.** Check today's calendar via your connected tools (e.g. via Composio MCP — `GOOGLECALENDAR_EVENTS_LIST_ALL_CALENDARS` if you use Google Calendar) with `time_min` = start of today and `time_max` = end of today in your timezone (RFC3339), `single_events: true`. If you gave a name, find the matching event. If not, list today's events and ask which one to prep. Extract: event title, time, duration, attendee names + email addresses, video-call link, and any notes in the description.

2. **Pull all context in parallel** (run these simultaneously via your connected tools):
   - **Email thread history** — if you use Gmail, `GMAIL_FETCH_EMAILS` with `user_id: "me"`, `max_results: 20`, `include_payload: true`, `query: "from:[attendee email] OR to:[attendee email]"`. If multiple attendees, search each — focus on the primary external attendee.
   - **CRM deal** — your CRM (e.g. HubSpot). If you use HubSpot, `HUBSPOT_SEARCH_DEALS` with `limit: 10`, `properties: ["dealname", "amount", "dealstage", "hubspot_owner_id", "closedate", "hs_lastmodifieddate", "notes_last_updated", "hs_next_step", "pipeline"]`. Search by attendee company name or email domain.
   - **CRM contact** — if you use HubSpot, `HUBSPOT_SEARCH_CONTACTS_BY_CRITERIA` by attendee email, `properties: ["firstname", "lastname", "email", "company", "phone", "jobtitle", "lifecyclestage", "notes_last_updated"]`.
   - **Your own client notes (if you keep a file)** — read your client notes file and search for the person or company. This step is optional; skip it if you don't keep one.

3. **Synthesise the prep brief.** Cross-reference every source and output in the exact format below. Never invent facts — if a field is unknown, say so or mark TBD.

## Output format

---

## 📋 Meeting Prep — [Event Title]

**When:** [Day, Date] · [Time] – [End Time] ([Duration])
**With:** [Attendee names and titles if known]
**Where:** [Video-call link / In-person]

---

### 👤 Who They Are

- **Name:** [Full name]
- **Title:** [Job title if known]
- **Company:** [Company name]
- **Email:** [Email]
- **Phone:** [Phone if available]

*[1-2 sentence summary of who they are and their relationship with you — new lead, existing client, referral partner, etc.]*

---

### 📊 Deal Context

*From your CRM + client notes:*

- **Deal:** [Deal name] — [Stage]
- **Value:** [Amount or TBD]
- **Days in stage:** [N]
- **Owner:** [Who owns the deal]
- **Last activity:** [Date and brief description]

*If no deal exists:* "No CRM deal found — this may be a new lead. Consider creating a deal after the call."

---

### 📧 Email History Summary

*From the last [N] emails between you and this person:*

- **Total threads:** [N]
- **Last email:** [Date] — [who sent it, subject, 1-line summary]
- **Key topics discussed:** [bullet list of main themes from email threads]
- **Open threads / unanswered:** [anything waiting for a reply from either side]

---

### 🎯 Suggested Agenda

Based on the context above, here's a suggested agenda:

1. **[Topic]** — [Why this matters now / context]
2. **[Topic]** — [Why this matters now / context]
3. **[Topic]** — [Why this matters now / context]
4. **Next steps** — agree on deliverables and timeline

---

### 💬 Talking Points

- [Specific point to raise, based on email/deal context]
- [Specific point to raise]
- [Specific point to raise]
- [Question to ask them]

---

### ⚠️ Watch Out For

- [Anything to be careful about — e.g. "They went silent for 2 weeks after the proposal", "Price sensitivity flagged in earlier emails", "Someone else owns this deal — check if they're joining"]

---

## Notes for Claude

- Pull as much context as possible from all sources before synthesising. The prep brief should feel like you had an assistant do 20 minutes of research.
- If the attendee is already in your client notes, pull all the detail from there — project status, owner, payment status, etc.
- If the attendee is a completely new contact (not in your email, CRM, or notes), say so clearly and suggest discovery questions.
- If a deal is owned or co-owned by a teammate, flag it in Watch Out For so they can join the call if needed.
- If a tool call fails, note it clearly and continue with the rest.
- Never invent facts — leave fields blank or mark TBD rather than guessing.
- Keep tone direct and practical — this isn't a report, it's a cheat sheet for a call.
- Booking link / handle placeholders, if you reference them: `[YOUR_BOOKING_LINK]`, `[YOUR_HANDLE]`.
- After outputting the brief, ask: "Want me to draft any follow-up after the call, or add anything to the agenda?"

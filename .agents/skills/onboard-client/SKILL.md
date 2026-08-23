---
name: onboard-client
description: Spin up the full client onboarding spine the moment a deal closes — pulls the deal + contact from your CRM, builds a Google Drive workspace, generates a kickoff doc, drafts a warm welcome email in your brand voice, optionally holds a kickoff call, and updates your own client tracker. Use when you run /onboard-client, say "onboard <client>", or when a deal hits Closed Won and the project needs kicking off.
---

# Onboard Client

The repeatable onboarding spine you run the instant a deal closes. One command turns a Closed Won deal into a fully scaffolded project: Drive workspace, kickoff doc, welcome email draft, calendar hold, and an updated client record. Everything external goes through your connected tools (e.g. via Composio MCP). Use your own timezone for dates and any calendar hold. **Never auto-send the email — it's a draft for you to approve.**

## When to use

- You run `/onboard-client` or `/onboard-client <client name>`
- You say "onboard <client>" or "kick off <client>"
- A deal moves to **Closed Won** and the project needs scaffolding
- A new signed client needs a Drive workspace, kickoff doc, and welcome email in one pass

## Workflow

Run all independent reads in parallel, then create artifacts in order.

### Step 1 — Gather context (parallel)

If no client name was given, ask which client / deal to onboard. Then pull in parallel from your connected tools:

- **CRM deal** — from your CRM (e.g. HubSpot via `HUBSPOT_SEARCH_DEALS` if you use it)
  - Useful fields: deal name, amount, deal stage, owner, close date, last activity, next step, pipeline
  - Search by client / company name. Confirm the deal is Closed Won; if it isn't, flag it and ask whether to continue.
- **CRM contact** — from your CRM (e.g. `HUBSPOT_SEARCH_CONTACTS_BY_CRITERIA` if you use it)
  - Search by company name or known email
  - Useful fields: first name, last name, email, company, phone, job title
- **Your client tracker (if you keep one)** — read it and search for the client. Pull any existing notes, scope, owner, and contacts so nothing is overwritten. Optional — skip if you don't keep one.
- **Today's date** — get the current date/time (e.g. `GOOGLECALENDAR_GET_CURRENT_DATE_TIME` if you use Google Calendar) for the kickoff doc date and any calendar hold.

Cross-reference everything. Identify: client name, deal value, primary contact (name + email + title), the owner on your side, agreed scope, and assigned person/developer. Anything you can't confirm, mark `[ASSUMPTION: …]` and surface it at the end.

### Step 2 — Create the Drive workspace

Build the folder tree in your Google Drive (e.g. via `GOOGLEDRIVE_CREATE_FOLDER` if you use it). Create the parent first, capture its `id`, then create each child passing that id as parent.

- **Parent** — name = the client name
- **Children** — × 5, each with `parent_id` = the parent's id:
  - `01 Contract & Scope`
  - `02 Access & Assets`
  - `03 Build`
  - `04 Deliverables`
  - `05 Comms`

Capture every folder id and web link.

### Step 3 — Generate the kickoff doc

Create a doc (e.g. via `GOOGLEDOCS_CREATE_DOCUMENT` if you use Google Docs), title `[Client] — Kickoff & Project Brief`. Contents:

- **Project overview** — one paragraph: what you're building and why, from the deal/scope
- **Agreed scope & deliverables** — bulleted, concrete
- **Milestones** — phased with rough dates from the close date / agreed timeline
- **Primary contacts** — client side (name, title, email, phone) and your side (owner, assigned person/developer)
- **Access & credentials checklist** — exactly what you need from the client to start (CRM admin invite, Google Drive share, API keys, tool logins, sample data, brand assets — tailor to the scope)

Move the doc into `01 Contract & Scope` if straightforward; otherwise note its standalone link.

### Step 4 — Draft the welcome email (DO NOT SEND)

Create an email draft to the primary contact (e.g. via `GMAIL_CREATE_EMAIL_DRAFT` if you use Gmail). Match your brand voice (use your brand notes, if you have them): open with first name, no "Dear", no filler, get to the point, short sign-off. Cover, briefly:

- Welcome + a genuine line that you're glad to be building with them
- What happens next (kickoff call → access setup → build kicks off within a day or two)
- The specific access/info you need from them (mirror the checklist from the kickoff doc — keep it to a short numbered list)
- Kickoff-call booking link: `[YOUR_BOOKING_LINK]`
- A short sign-off in your name

Keep it under ~4 short paragraphs. Create as a **draft only**.

### Step 5 — Calendar hold (optional)

If you asked for a hold, or a kickoff time is known: create a calendar event (e.g. `GOOGLECALENDAR_CREATE_EVENT` if you use Google Calendar) — title `[Client] — Kickoff Call`, your timezone, default 30 min, attendee = primary contact, add the booking link in the description. Otherwise skip and note "no hold placed — booking link in the email."

### Step 6 — Update your client tracker (optional)

If you keep a client tracker, add a new entry in the same format your existing entries use. A sensible shape:

```markdown
### [Client Name]
- **Project:** [Scope / what you're building]
- **Value:** [$X total]
- **Payment structure:** [your payment terms]
- **Owner / lead:** [Assigned person / developer / TBD]
- **Phase:** Closed Won — onboarding
- **Status:** Onboarded [date]. Drive workspace + kickoff doc created, welcome email drafted (awaiting send). [Any scope notes.]
- **Last contact:** [YYYY-MM-DD]
- **Next action:** [Send welcome email / await access / book kickoff call]
- **Primary contact:** [Name (email)]
- **Notes:** [CRM deal ID: XXX. Anything else.]
```

Preserve any existing manual notes if the client is already partially in the file.

## Output — onboarding checklist

After completing the steps, output this for you to review:

```
✅ Onboarded — [Client Name]

📁 Drive workspace:  [parent folder link]
   ├─ 01 Contract & Scope   [✓]
   ├─ 02 Access & Assets    [✓]
   ├─ 03 Build              [✓]
   ├─ 04 Deliverables       [✓]
   └─ 05 Comms              [✓]

📄 Kickoff doc:      [doc link]
📅 Kickoff hold:     [event link / "not placed — booking link in email"]
👤 Client record:    Added to your tracker ✓ (or "skipped — no tracker")

✉️  Welcome email — DRAFT (not sent), to [contact email]:
   --------------------------------------------------
   Subject: [subject]

   [full draft body]
   --------------------------------------------------

⚠️  Flags / assumptions:
   - [ASSUMPTION: …]
```

Show the full email draft inline so you can approve or edit before sending.

## Notes for Claude

- **Never auto-send the email.** It is always a draft. Same for anything sent to the client — you approve first.
- Pull the CRM deal + contact (+ your tracker, if any) in parallel before creating anything. Don't scaffold a workspace until the deal and contact are confirmed.
- Use `[your payment terms]` as a placeholder unless the specific deal says otherwise — fill in your own terms.
- If a person/developer isn't assigned yet, mark `TBD`.
- If the deal isn't actually Closed Won, stop and flag it — don't onboard a deal that hasn't closed.
- Keep the welcome email genuinely short and in your voice — if it reads like a corporate onboarding template, rewrite it.
- If a tool call fails, note it clearly, finish the rest, and list what still needs doing manually.
- After outputting the checklist, ask: "Want me to send the welcome email and place the kickoff hold, or tweak anything first?"

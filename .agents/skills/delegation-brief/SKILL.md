---
name: delegation-brief
description: Turn any task or project into a no-ambiguity delegation brief someone can execute without follow-up questions — interrogates for missing detail, then writes objective, scope, out-of-scope, milestones with definition-of-done, an access checklist, tools, deadlines, comms, and success criteria. Use when the user runs /delegation-brief, says "hand this off", "delegate this", "brief my VA/contractor/freelancer/developer", "outsource this task/project", or wants a clean spec to give a VA, contractor, freelancer, employee, agency, or developer.
---

# Delegation Brief

Take any task or project — described out loud, or pulled from notes/a doc the user provides — and turn it into a delegation brief so tight that a VA, contractor, freelancer, employee, agency, or developer can run it without a single follow-up question. The whole job is removing ambiguity: a vague task in, an executable spec out — for delegating ANY work to ANYONE.

Portable by design: assume no specific CRM, tracker, or tooling. Never invent missing detail — flag it as `[NEEDS INPUT: …]` and ask.

## When to use

- `/delegation-brief` or `/delegation-brief <task/project>`
- "Hand this off" / "delegate this" / "outsource this task/project"
- "Brief my VA / contractor / freelancer / employee / agency / developer on [thing]"
- "Write a clear spec so someone else can do [X] without asking me questions"
- The user is about to give a job to someone and wants zero back-and-forth

## Workflow

1. **Read the source.** If the user pointed at notes, a doc, or a message, read it first and lift the real detail. If they just described the task in chat, work from that. Don't restate — extract what's actually specified.

2. **Interrogate only for what's missing.** If the task is thin, ask the few questions needed to remove ambiguity — no padding, only the gaps. The essentials to nail down:
   - **Objective** — what outcome is actually wanted, and why it matters
   - **Who it's for** — the end audience/client/internal use
   - **Deadline** — hard date or rough window, plus any checkpoints
   - **Quality bar** — what "good" looks like; any examples to match
   - **Constraints** — budget, tools they must/can't use, brand rules, do-nots
   - **Who's doing it** — VA / contractor / freelancer / employee / agency / dev, so the detail level and tools fit them
   Ask these in one tight batch. If the user says "just make assumptions", proceed and mark each one `[NEEDS INPUT: …]`.

3. **Write the brief** to the format below. Every line must trace to something the user said or to the source doc. Anything unconfirmed is a `[NEEDS INPUT: …]` line, never a guessed fact. Each milestone gets a concrete, testable definition of done — that's the point of the whole brief.

4. **Offer to save and/or format for sending.** Ask if the user wants it saved to `outputs/delegation-briefs/<slug>.md` (create the folder; slug = short kebab-case from the task) and/or rewritten as a ready-to-paste message to the person. Keep both portable — no assumed CRM or tracker.

## Output format

```markdown
# Delegation Brief — [Task / project name]
**For:** [VA / contractor / freelancer / employee / agency / developer — name if known]
**Owner:** [who set this and approves the work] · **Date:** [today]

## Objective & context
[Why this matters and the outcome wanted — 2-3 sentences. What "done well" changes for the business/audience.]

## Scope — what's included
- [exactly what the person should produce / do]
- [be specific: quantity, format, length, where it lives]

## Out of scope — do NOT do
*Protects against scope creep.*
- [thing they might assume is included but isn't]
- [anything deferred to later / handled by someone else]

## Steps / milestones
| # | Step / milestone | Definition of done |
|---|------------------|--------------------|
| 1 | [ordered step] | [the concrete, testable bar that means it's finished] |
| 2 | [step] | [definition of done] |

## Access & resources checklist
*What the person needs, and who/where to get it.*
- [ ] [Login / account access] — from [who / where]
- [ ] [Files / docs / data] — at [location / shared by who]
- [ ] [Brand assets, examples, templates] — [link / source]

## Tools to use
- [the tools/platforms they should work in — and any they must NOT use]

## Deadline & checkpoints
- **Final deadline:** [date]
- **Checkpoint(s):** [e.g. rough draft by [date], check-in at [milestone]]

## Comms
- **Updates go to:** [channel — email / chat / wherever the owner reads]
- **Cadence:** [e.g. update every 2 days + flag the moment anything blocks]
- **Questions/escalations to:** [owner — the person who set the task]

## Success criteria
[How the work will be reviewed and accepted — the checklist the owner runs before signing off.]
- [criterion]
- [criterion]

## Budget / pay  *(include only if relevant)*
- [agreed rate / fee / cap, and when it's paid]

## Confirm before you start
*The delegate replies to these so you know they understood.*
- [ ] I understand the objective and what "done" looks like
- [ ] I have all the access/resources above (or have flagged what's missing)
- [ ] I can hit [deadline] — or I've raised it now if not
- [ ] I know where to post updates and who to ask if I'm stuck

## Open questions
- [NEEDS INPUT: …] — confirm before this goes out
```

## Notes for Claude

- **Removing ambiguity is the whole job.** If a delegate could reasonably ask "what did they mean by this?", you haven't finished — tighten it or flag `[NEEDS INPUT: …]`.
- **Definition of done must be testable.** "Draft 5 emails matching the brand voice in the linked examples, ≤120 words each" — not "write some emails".
- **Don't pad.** A two-hour task gets a short brief; a project gets the full structure. Match the depth to the work and to who's doing it.
- **Stay portable.** Don't assume HubSpot, a specific tracker, or any private file. This skill should work for any business that downloads it.
- **Never invent facts.** Missing detail is always `[NEEDS INPUT: …]`, asked of the user — never a confident guess that the delegate then acts on.
- After writing the brief, ask: **"Want me to turn this into a ready-to-send message for them, or a task-tracker checklist you can drop in?"**

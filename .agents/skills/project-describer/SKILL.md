---
name: project-description
description: Write a project description document that explains a software project to both non-technical and technical readers. Use this whenever the user asks to "write a project description," "create an abstract/blueprint into a doc," "explain my project," "make a README-style overview," or gives you rough project notes/an abstract and wants a clean explanatory document produced from it. Trigger even if they don't say "project description" explicitly — e.g. "turn this into something a new dev could read and understand," "write up what this project is for stakeholders and engineers."
---

# Project Description Writer

A project description explains what a project *is* and *why it exists* to two audiences at once: someone non-technical (a stakeholder, a new user, a recruiter) and someone technical (a new engineer joining the project). It must never confuse either reader — technical readers shouldn't feel talked down to, and non-technical readers shouldn't hit unexplained jargon.

## When to use this

Use whenever the user wants a project explained/documented in prose form — from scratch, from rough notes, from an abstract, or from an existing blueprint/spec file. If they've uploaded a PDF, doc, or notes describing the project, read that first and extract facts from it — don't invent architecture or technology choices that aren't stated or reasonably implied.

## The 5 required sections

Every project description must answer these, in this order. Do not skip or merge them.

1. **What is the project about?** — A plain-language explanation of what the thing is, in 1-2 short paragraphs. Use an analogy or comparison to something familiar if it helps ("like a senior engineer who already knows the codebase, vs. a freelancer who re-reads it every time"). A non-technical reader should finish this section knowing what the project *does*.

2. **What problem is it solving?** — Explain the pain point in plain terms first (why the current way of doing things is bad — slow, expensive, redundant, doesn't scale, etc.), then optionally restate it in one precise technical sentence for engineers. Two-layer explanation: plain language first, technical framing second.

3. **What is the workflow (in general terms)?** — A high-level flow, not implementation detail. Use a simple arrow-diagram in a code block (`A → B → C`) to show the general shape, then a short walkthrough of what happens end-to-end for one typical request/use case. Keep this conceptual — no function names, no file paths.

4. **What technologies are being used?** — A table or list mapping each technology to its *role* in the project (not just a name-drop). One line per technology: what it is used for, in context.

5. **How do these technologies connect?** — This is the most important section and the one most documents skip. Walk through, step by step, how data/control flows *through* the technologies listed in section 4 — what each one hands off to the next, and why. End with a one-sentence summary that ties the whole chain together. This section is what actually makes a new developer understand the system, not just the buzzwords.

## Formatting rules

- Output as a single markdown (`.md`) file, saved to the outputs directory, with a descriptive filename (e.g. `<project-name>-project-description.md`), then presented to the user.
- Use `##` headers matching the 5 sections above (numbered).
- Use short paragraphs, bullet lists, and one small diagram/table per section — avoid dense walls of text.
- Bold key terms the first time they're introduced (e.g. **Repository Intelligence Engine (RIE)**).
- Never abbreviate or truncate technical details that were given — if the user provided a full tech stack or architecture, represent all of it, not a subset.
- Do not add sections beyond the 5 unless the user explicitly asks for more (e.g. roadmap, glossary).

## Workflow for building it

1. Gather source material: read any uploaded abstract/blueprint/spec, or ask the user for the missing facts (what it does, what problem it solves, rough architecture, tech stack) if nothing was provided. Don't fabricate architecture details — extract from what's given, and ask rather than guess if a required section has no source material at all.
2. Draft each of the 5 sections in order, applying the plain-language-first, technical-second approach throughout.
3. Write the result as a markdown file (see Formatting rules) and present it to the user.
4. If the user gives feedback (too technical, too long, missing a technology, etc.), revise the existing file in place rather than starting over.

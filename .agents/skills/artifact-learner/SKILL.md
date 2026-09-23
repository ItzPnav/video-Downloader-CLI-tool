---
name: artifact-learner
description: Turn an Obsidian vault directory into one mega learning artifact. Trigger whenever the user gives only a directory path and invokes /artifact-learner (paired with /generative-ui). Do not grep or keyword-search the vault — this skill requires reading every file directly.
---

# Artifact Learner

## Input

The user will give you exactly one thing: `{dir_path}` — a directory path inside their Obsidian vault.

That's it. No other config. Don't ask for anything else.

## How to access the vault (important)

You have direct filesystem access to `{dir_path}`. Use it as follows:

- Walk the full directory tree under `{dir_path}` — every subfolder, every file, no exceptions.
- **Open and read each file directly, in full.** Do NOT use grep, keyword search, semantic search, or any partial-match technique to "find relevant parts." Partial reads and search-based skimming will cause you to miss content and misrepresent the vault. Read everything, then synthesize.
- Do not skip files because their names look irrelevant — subfolder structure in a personal vault is not a reliable filter.

## What to do with it

This is the user's personal Salesforce Obsidian knowledge base. Build ONE mega learning artifact covering everything found, invoking `/generative-ui` to render it. Do not ask the user to re-invoke — generate the full thing in one pass.

Structure the artifact in exactly this order:

### 1. SIMPLE EXPLANATION
- Look specifically for `FiveYearOld.md` files in each folder.
- Summarize their content in plain, ELI5 language.
- If a topic has no `FiveYearOld.md`, generate a short ELI5 summary yourself from its other notes.

### 2. GENERAL EXPLANATION
- A clear, standard-level explanation of each major topic/module found in the vault.
- Organize by folder/topic, not file-by-file.

### 3. FLOWCHART
- For each topic that represents a process, module, or "how it works" concept, generate a flowchart of that flow (e.g. Lead Conversion, Approval Process, Record-Triggered Flow).
- Skip flowcharts for purely conceptual/reference topics that have no process.

### 4. FLASHCARDS
- Generate exactly 15 flashcard-style Q&A questions total, drawn across the entire directory — prioritize the most important/testable concepts across all topics, not evenly split per folder.

### 5. STRUCTURAL VISUAL
- For every subfolder/topic, generate a generic structural visual — nested boxes showing the topic's own hierarchy (e.g. Org → App → Object → Record → Field for data-model topics; or the equivalent top-down structural breakdown for non-DB topics — e.g. Permission Set → Object Permissions → Field Permissions for security, or Flow → Elements → Actions for automation).
- Match the nested-box visual style: outer container = top-level concept, inner containers = sub-levels, leaf items = individual fields/values/elements.

Keep sections clearly labeled and navigable. Prioritize accuracy from the actual notes over generic Salesforce knowledge — if the notes contradict general knowledge, follow the notes.

## Output rules

- One single mega artifact — not one per file, not one per folder.
- Always render through `/generative-ui`. Never output this as plain chat text.
- Do not pause mid-way to ask the user anything — you already have everything you need from `{dir_path}`.

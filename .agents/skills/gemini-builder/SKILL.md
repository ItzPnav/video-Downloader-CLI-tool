---
name: gemini-project-rules-builder
description: "Builds GEMINI.md file where the AI reads readme.md or other files (PIFS or"
---
 
# GEMINI_PROJECT_RULES_BUILDER.md
# Meta-template for generating a project-specific GEMINI.md
# Two inputs only: this file + the target project's README.md.
# No interview, no other files, no user-supplied placeholder values.
 
---
 
## HOW TO USE THIS BUILDER
 
**Inputs (exactly two, nothing else):**
1. This builder file.
2. The target project's `README.md`.
**Process:**
1. Read the README top to bottom. Every `{PLACEHOLDER}` in Sections 1–11 below must be resolved using ONLY what's derivable from the README, per the extraction map in Section 0.1.
2. If a section's required info genuinely isn't present or inferable from the README, delete that whole section — never leave a literal `{PLACEHOLDER}` token in the output. No half-filled sections.
3. Do not ask the user follow-up questions and do not wait for additional files. Make the best defensible inference from README content (stack, folder tree, code fences, badges, wording like "never/always") and move on.
4. Keep the tone of the original: short, imperative, never/always rules — not prose explanations.
5. Output file is `GEMINI.md` (or `<AGENT>.md` for whichever CLI agent reads it), placed at the project root.
6. Re-run this builder (with the current README.md) whenever the project's architecture, storage schema, or design system changes materially — stale rules are worse than no rules.
---
 
## 0.1 EXTRACTION MAP — README → GEMINI.md
 
| GEMINI.md target | Pull from README | If absent |
|---|---|---|
| §1 Project Identity (name, type, author, version, purpose) | Title, badges, overview/intro paragraph, repo owner in links or badges | Version → omit field; author → repo owner if inferable; type → infer from tech stack section |
| §2 File Ownership | Folder structure / project structure block | Delete section |
| §3 UI Design System | Any documented CSS variables, color tokens, font links/tables, screenshots' described style | Delete whole section |
| §4 Data Schema | Documented storage keys, data model snippets, DB schema blocks | Delete whole section |
| §5 Platform/Runtime Hard Rules | Tech stack table, stated platform (e.g. "Manifest V3", "Next.js App Router", "Docker"), setup/install steps | Infer minimal rules from stack name only; if stack itself is unclear, delete section |
| §6 Domain Logic Contracts | Per-feature / per-module descriptions in Features or Architecture sections | Delete whole section |
| §7 README Builder Rules | The README's OWN actual section order, heading style, badge style, table formatting, footer — mirror it exactly so regeneration stays self-consistent | Use README's literal structure as the rule; never invent a different convention |
| §8 Guardrails | Explicit "never/always/do not" language anywhere in the README; version-pinned or zero-dependency claims | Infer from stack constraints only; otherwise delete |
| §9 Coding Style | Code fence conventions, log-prefix examples, language/typing mentioned in README | Delete whole section |
| §10 Quick Reference Snapshot | Tech stack table, feature list, version badge | Fill only rows the README supports; drop unsupported rows |
| §11 Graphify Integration | Only if README explicitly mentions a `graphify-out/` knowledge graph | Delete whole section (default: delete) |
| §12 Custom Slash Commands | Fixed — not derived from README | Always keep as-is, every project |
 
Rule of thumb: the README is authoritative and exhaustive for this process. Nothing outside it is consulted or requested.
 
---
 
# GEMINI.md — {PROJECT_NAME}
# Project memory for {AGENT_NAME}. Read this before touching ANY file.
 
---
 
## 1. PROJECT IDENTITY
 
- **Name:** {PROJECT_NAME}
- **Type:** {PROJECT_TYPE}
- **Author handle:** {AUTHOR_HANDLE}
- **Current version:** {VERSION}
- **Purpose:** {ONE_TO_TWO_SENTENCE_PURPOSE}
---
 
## 2. FILE OWNERSHIP — WHO TOUCHES WHAT
 
```
{FILE_1}          ← {What it owns / when to edit it}
{FILE_2}          ← {What it owns / when to edit it}
{FILE_3}          ← {What it owns / when to edit it}
{CONFIG_FILE}      ← Edit with extreme caution — see Section 5.
README.md          ← Always regenerate using README BUILDER rules in Section 7.
FUTURE_FEATURES.md ← Append-only roadmap. Never delete existing items.
PROGRESS.md         ← Append-only checklist. Check off items, never remove them.
docs/               ← Research notes. Read-only reference. Never modify.
```
 
**Never create:** {THINGS_NOT_TO_CREATE} unless explicitly instructed.
 
---
 
## 3. UI DESIGN SYSTEM — NEVER DEVIATE FROM THIS
 
*(Delete this whole section if the README shows no UI/design tokens.)*
 
### 3.1 CSS Variables (copy exactly)
 
```css
:root {
  --bg:        {HEX};
  --border:    {HEX};
  --primary:   {HEX};
  --accent:    {HEX};
  --text:      {HEX};
  --text-dim:  {HEX};
}
```
 
### 3.2 Fonts
 
```html
<link href="{GOOGLE_FONTS_URL}" rel="stylesheet"/>
```
 
| Font | Usage |
|------|-------|
| {FONT_1} | {Titles / headers} |
| {FONT_2} | {Body text} |
| {FONT_3} | {Monospace / labels} |
 
### 3.3 Visual Identity Rules
 
- {RULE — background style}
- {RULE — border/shadow conventions}
- {RULE — hover/transition conventions}
- {RULE — border-radius or shape limits}
- {RULE — anything explicitly banned}
### 3.4 Component Class Naming (exact — do not rename)
 
```css
.{class-1}  /* {usage} */
.{class-2}  /* {usage} */
```
 
### 3.5 Layout Constraints
 
- {Fixed dimensions}
- {Surfaces exempt from the constraint, and why}
---
 
## 4. DATA SCHEMA — NEVER RESHAPE THIS
 
*(Delete or adapt if the README shows no persistent storage.)*
 
All {DATA_ENTITY} lives in `{STORAGE_MECHANISM}` under the key `{STORAGE_KEY}`.
 
```js
// {STORAGE_KEY}: Array of {ENTITY_TYPE}
{
  {field1}:  {Type},  // {what it represents}
  {field2}:  {Type},  // {what it represents}
  {field3}:  {Type},  // {what it represents}
}
```
 
**Other storage keys (do not delete or rename):**
- `{KEY}` — {purpose}
- `{KEY}` — {purpose}
**Deduplication:** by `{DEDUP_FIELD}`. {Exact dedup logic/condition.}
 
---
 
## 5. {PLATFORM_OR_RUNTIME} HARD RULES
 
1. **{Constraint 1}** — {why it matters / what breaks if violated}
2. **Permissions/scope** — only `{ALLOWED_LIST}`. Do not add more without a very good reason.
3. **{Restricted resource}** — only these entries. Do not broaden to `{DANGEROUS_WILDCARD}`:
   ```
   {entry_1}
   {entry_2}
   ```
4. **{Resource declaration list}** — add new entries here whenever a new {resource type} is created.
5. **{Match/route patterns}** — current list covers all required cases. Do not remove existing patterns; only add.
---
 
## 6. {DOMAIN_LOGIC_NAME} CONTRACTS
 
### {Source/Module 1}
- **Detection/entry condition:** {exact condition}
- **Key DOM/API/field:** {selector or endpoint}
- **Fallback:** {what happens if primary lookup fails}
- **Match/trigger scope needed:** {URL patterns, route, or event}
### {Source/Module 2}
- **Detection/entry condition:** {exact condition}
- **Key DOM/API/field:** {selector or endpoint}
- **Fallback:** {what happens if primary lookup fails}
*(repeat per source/module)*
 
---
 
## 7. README BUILDER RULES
 
Every time README.md is regenerated, follow these rules exactly — derived from the README's own current structure.
 
**Section order (fixed, no exceptions):**
{Header → Overview → Architecture → Features → Tech Stack → Setup → ... → Footer}
 
**Formatting rules:**
1. Badges: {style convention}. Wrap block in `{allowed wrapper tag}`.
2. Architecture: {ASCII diagram in code block / other convention}.
3. Features: {heading style}. {line-length convention}.
4. Tech Stack: markdown table with columns `{col1} | {col2}`.
5. Setup: numbered steps. Each shell command in its own fenced block.
6. {Any other formatting bans}
7. Footer always ends with:
   ```
   # {tagline}
   > *{one-line closing statement}*
   ```
 
**What to pull from where:**
- Roadmap items → from `FUTURE_FEATURES.md`
- Folder structure → from actual file tree
- Feature descriptions → from actual implemented behavior in `{source files}`
---
 
## 8. WHAT NOT TO DO — HARD GUARDRAILS
 
- **Never {anti-pattern 1}** — always {correct pattern} instead
- **Never {anti-pattern 2}** — {consequence if violated}
- **Never add {component}** unless explicitly asked
- **Never widen {permission/scope}** — keep it scoped
- **Never {tech/style violation}** — {reason}
- **Never change {schema/key/class names}** — existing {data/installs/consumers} would break
- **Never use {banned dependency/framework}** — {house convention instead}
- **Never rename {enum-like string values}** — must stay exactly `{value1}`, `{value2}`, ...
---
 
## 9. CODING STYLE
 
- Comments: {convention}
- Async: {convention}
- Logging: prefix with `[{PROJECT_TAG}]` — e.g. `console.log('[{PROJECT_TAG}] ...')`
- Dependencies: {policy}
- Language/typing: {plain JS vs TypeScript, language version, strictness}
---
 
## 10. QUICK REFERENCE — CURRENT STATE SNAPSHOT
 
| Thing | Value |
|-------|-------|
| Version | {VERSION} |
| {Scope dimension} | {list} |
| Storage backend | {STORAGE_MECHANISM} |
| {Key layout constraint} | {value} |
| Fonts | {list} |
| Primary color | {HEX} |
| Dedup method | {method} |
| {Other core algorithm} | {one-line description} |
| Export formats | {list, if applicable} |
 
---
 
## 11. GRAPHIFY / KNOWLEDGE-GRAPH INTEGRATION
 
*(Delete unless the README explicitly documents a `graphify-out/` knowledge graph.)*
 
This project has a knowledge graph at `graphify-out/` with god nodes, community structure, and cross-file relationships.
 
Rules:
- For codebase questions, first run `graphify query "<question>"` when `graphify-out/graph.json` exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts.
- If `graphify-out/wiki/index.md` exists, use it for broad navigation instead of raw source browsing.
- Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review or when query/path/explain don't surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
### 11.1 Schema
 
```
graph.json
  .nodes[]          — {N} nodes
    .id             — stable snake_case key
    .label          — human name
    .source_file    — origin file
    .source_location
    .community      — integer cluster id
    .file_type      — "code" | "doc"
 
  .links[]          — {N} edges
    .source / .target — node ids
    .relation         — "contains" | "calls"
    .confidence       — "EXTRACTED" | "INFERRED"
```
 
### 11.2 Key Communities (fill in after first `graphify update .`)
 
| Community | What lives there | Cohesion |
|-----------|-------------------|----------|
| {n} | {files/functions} | {score} |
 
### 11.3 Staleness Check
 
The graph was built from commit `{COMMIT_HASH}`. Before trusting it, run:
```bash
git rev-parse HEAD
```
If the hash differs, run `graphify update .` (zero API cost) to rebuild.
 
---
 
## 12. CUSTOM SLASH COMMANDS
 
*(Fixed section — include verbatim in every generated GEMINI.md, regardless of stack.)*
 
### /acp — Add, Commit, Push
 
When the user types `/acp`:
 
1. Stage everything: `git add .`
2. Write a commit message summarizing the actual staged changes — **max 6–7 words, imperative mood, no trailing period** (e.g. `fix popup crash on empty state`, `add streak counter to dashboard`).
3. Commit: `git commit -m "{generated message}"`
4. Push: run `git push`. If the current branch has no upstream, run `git push -u origin main` instead.
Rules:
- Never ask the user to approve or edit the commit message — write it and proceed.
- Never skip `git add .` even if only one file changed.
- If `git commit` reports nothing to commit, say so and stop — do not push.
- If the push is rejected (e.g. diverged branch), report the exact git error; do not force-push without being explicitly told to.
---
 
## APPENDIX: FILL-IN CHECKLIST
 
Before deleting this appendix, confirm every placeholder below has been resolved via the README (extraction map in §0.1) or its section removed:
 
- [ ] Section 1 — identity fields
- [ ] Section 2 — real file list, real ownership rules
- [ ] Section 3 — real design tokens (or section deleted)
- [ ] Section 4 — real schema (or section deleted)
- [ ] Section 5 — real platform/runtime rules
- [ ] Section 6 — real per-module contracts (or section deleted)
- [ ] Section 7 — real README structure (mirrored from the input README)
- [ ] Section 8 — real guardrails, not generic placeholders
- [ ] Section 9 — real coding-style conventions
- [ ] Section 10 — real current-state snapshot
- [ ] Section 11 — kept only if README documents graphify
- [ ] Section 12 — /acp command present verbatim (fixed, always kept)

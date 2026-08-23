---
name: proposal
description: Drafts a clean, on-brand client proposal PDF — value-first, with the price on the last page. Use when you want to draft a proposal for a prospect, write up a priced and scoped offer, or send a company a proposal.
---

# Proposal

Generate a proposal for a prospect or client. Pulls together whatever context you have (notes, CRM, email history), defines the scope, writes value-first copy, and delivers a clean branded PDF ready to review and send — never just markdown.

Usage: `/proposal [client or prospect name]`

## When to use

- You want a proposal drafted for a named prospect or company
- "Draft a proposal for [prospect]" / "write up a proposal" / "send [company] a proposal"
- Any time a prospect is ready for a priced, scoped offer

## Workflow

1. **Gather context on the prospect.** Use whatever sources you have — optional, none required:
   - **Your own notes** — any brief, scoping doc, or call notes you keep.
   - **Your CRM (e.g. HubSpot, if you use one)** — find the deal/contact record. Pull deal name, stage, value, contacts, notes, logged emails.
   - **Your email** — recent threads from or about this prospect. Extract what they said they need, pain points, timeline, specific requirements.
   - If you have no context at all, ask the user for the essentials (who, what problem, rough budget) before drafting.

2. **Identify the solution scope.** Define: what problem they're solving; what will be built (specific — "AI-powered patient intake form with triage scoring", not "AI automation"); likely scope (phases, integrations, timeline); and the price (use `[your pricing]`). Never invent scope — if anything is unclear, make a reasonable assumption and flag it with `[ASSUMPTION: ...]` for the user to verify.

3. **Draft the proposal content.** Cover this content (this is the content to cover, NOT the page order — page order is set in Step 4):
   - **The Problem** — 2-3 sentences in their language. Specific, not generic.
   - **What We'll Build** — clear description of the deliverable, broken into phases if appropriate (Phase 1, Phase 2…) with specific bulleted deliverables.
   - **What You Get** — outcomes (business results, not features).
   - **Investment** — see pricing rules in Notes.
   - **Next Steps** — confirm scope → sign off → first payment → project begins.
   - **Timeline:** use `[your timeline]` as the default — adjust only if scope genuinely requires longer.
   - Close with a short, human line and a sign-off.

4. **Build & render the branded PDF (always).** Every proposal ships as a clean, on-brand PDF. Do this without asking.
   - **Start from your own template.** Keep your proposal HTML template and brand assets (logo, fonts, colours) in one place, copy it to a working file like `[output-dir]/YYYY-MM-DD-<slug>.html`, then replace the placeholder content. Keep the locked `<style>` block of your template untouched so every proposal stays consistent.
   - **Hold the design principle — clean, on-brand, minimal:**
     - One typeface, used consistently — `[your brand — fonts]`.
     - No pills/chips — labels are quiet letter-spaced uppercase text.
     - Whitespace + hairline rules instead of boxes. Only price / phase / case panels get a subtle fill (no borders, no gradients).
     - Accent colour used sparingly. Generous whitespace, light/large headlines.
     - Diagrams stay minimal (hairlines + text; no gradient shapes or icon-boxes). Reuse the components already in your template.
     - Use `[your brand — colours, logo]` exactly as defined in your template; don't improvise a new look per proposal.
   - **Page order — value first, price LAST.** Cover → Introduction → Big picture / overview (+ roadmap) → solution detail (before → after) → Why us → **Investment & timeline (the final page)**. Never put roadmap or value content after the price — once they see the number, nothing after it gets read. End on the price + a short CTA + sign-off.
   - **Logo:** make sure your logo reads on your chosen background in the header, cover, and sign-off.
   - **Render to PDF** via headless Chrome (adjust paths to your machine):
     ```bash
     "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu --no-pdf-header-footer --print-to-pdf="[output-dir]/<name>.pdf" "[output-dir]/<name>.html"
     ```
   - **Check the render** — read the PDF pages back and confirm nothing overflows (especially the final page's sign-off). Tighten spacing if needed, then report both file paths.

5. **Present for approval.** After rendering, output:
   - ✅ Approve — ready to send
   - ✏️ Edit — tell me what to change (I'll regenerate the PDF)
   - ❌ Needs rework — tell me what's wrong

## Notes for Claude

- The proposal should feel human and direct, not like a corporate document. If you keep brand notes, follow them.
- Lead with value, keep copy tight, and put the price on the last page (see Step 4). Scale page count to the deal — a small build is ~6–8 pages, a larger multi-phase build can run longer. Don't pad.
- Flag every assumption clearly with `[ASSUMPTION: ...]` — don't invent scope.
- Pricing: use the user's stated price if given. Otherwise default to `[your pricing]`.
- Payment terms (set your own thresholds):
  - **Small projects (below your threshold):** no payment split — paid in full at project start. Include just the single price card, no payment-split block.
  - **Larger projects (at or above your threshold):** default to a deposit + balance split (e.g. deposit on start, balance on completion) per `[your payment terms]`, unless told otherwise.
- Build time default: `[your timeline]` unless scope genuinely requires longer. Keep the same number across the Timeline section and any "next steps" copy — don't contradict yourself.
- Don't include legal terms, SLAs, or NDAs — keep it simple.
- **Always deliver as a branded PDF** — never just markdown or HTML in chat. The HTML file is the source; the PDF is what you present.

Want me to draft a proposal now — which prospect, and do you have a price in mind or should I default to your pricing?

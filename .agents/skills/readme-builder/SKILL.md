# THE_README_BUILDER.md

> **How to use:** Copy the template below. Replace every `[PLACEHOLDER]` with your project's actual content. Follow the rules in each comment block. Delete all `<!-- -->` comments before publishing.

---

## 📐 RULES (read before filling)

1. **Section order is fixed** — Header → Overview → Architecture → Features → Tech Stack → Setup → Production Tips → API Endpoints (optional) → Roadmap → Security Notes → Folder Structure → Footer
2. **All sections are mandatory** except API Endpoints (only include if project has a backend API)
3. **Badges** — always use `style=for-the-badge`. Each badge = one layer/technology. Use distinct colors per badge. No two badges same color.
4. **Architecture** — must be an ASCII diagram inside a plain ` ``` ` code block. No images, no mermaid.
5. **Features** — use `### [ICON] Title` subheadings. 1–3 line description per feature. No bullet walls.
6. **Tech Stack** — must be a markdown table with columns: `Layer | Technology`
7. **Setup** — numbered steps (not bullets). Each shell command in its own `bash` code block.
8. **Footer** — always ends with `# Made with passion by **[YOUR NAME]**` followed by an italicized one-liner tagline. Never skip this.
9. **No HTML tags** anywhere — no `<div>`, `<p>`, `<h1>`, `<details>`, no HTML tables. Exceptions: the badge block (rule 10) and inline `<img>` section icons (rule 11).
10. **Badges block** — wrap in `<div align="center">` only. Add `---` divider after it.
11. **NO EMOJI CHARACTERS ANYWHERE IN THE DOCUMENT.** Not in headings, not in feature titles, not in the footer, not in bullet points. Emoji (📌 🚀 ⚙️ 🔒 etc.) are the single biggest tell that a README was AI-generated — a human reviewer clocks it instantly. Every place the old template used an emoji, use a small inline SVG icon instead:
    - Format: `<img src="[ICON_URL]" width="20" height="20" align="center"/>` immediately before the heading/title text, on the same line.
    - Icons must come from one consistent, real icon set — pick ONE per README and stick to it (e.g. [Simple Icons](https://simpleicons.org) via `https://cdn.simpleicons.org/[icon-name]/[hex-color]`, [Lucide](https://lucide.dev), or [Tabler Icons](https://tabler.io/icons) raw SVG). Do not mix icon sets within one README.
    - Section header icons should be semantic, not decorative: Overview → info/document icon, Architecture → sitemap/flow icon, Features → sparkles/bolt icon, Tech Stack → stack/layers icon, Setup → terminal/download icon, Production Tips → shield icon, API Endpoints → plug/api icon, Roadmap → map/checklist icon, Security Notes → lock icon, Folder Structure → folder icon, Contributing → git-branch icon, License → scale/document icon, Credits → heart/star icon.
    - Feature icons: pick one that matches what the feature actually does (not a random emoji-style symbol).
    - If unsure which real icon URL to use, it's acceptable to fall back to a plain heading with no icon rather than inventing a fake icon URL or reaching for an emoji.

---

## 📄 TEMPLATE

---

# <img src="[ICON_URL]" width="28" height="28" align="center"/> **[PROJECT-NAME]**

### *[11–13 word technical description — simple but specific]*

<!-- Badge block: one badge per major layer. Use style=for-the-badge. Each badge a different color. -->
<div align="center">
<img src="https://img.shields.io/badge/[LABEL]-[TECHNOLOGY]-[COLOR]?style=for-the-badge">
<img src="https://img.shields.io/badge/[LABEL]-[TECHNOLOGY]-[COLOR]?style=for-the-badge">
<img src="https://img.shields.io/badge/[LABEL]-[TECHNOLOGY]-[COLOR]?style=for-the-badge">
<img src="https://img.shields.io/badge/[LABEL]-[TECHNOLOGY]-[COLOR]?style=for-the-badge">
</div>

---

# <img src="[ICON_URL]" width="22" height="22" align="center"/> **Overview**

**[PROJECT-NAME]** is a [one sentence: what it does and who it's for].

It uses:

* **[Core Tech 1]** — [what it does in this project]
* **[Core Tech 2]** — [what it does in this project]
* **[Core Tech 3]** — [what it does in this project]
* **[Core Tech 4]** — [what it does in this project]

> [Optional: one-line note on purpose — academic, production, client project, etc.]

---

# <img src="[ICON_URL]" width="22" height="22" align="center"/> **Architecture**

<!-- Must be ASCII art in a plain code block. Show the data/request flow top-to-bottom. -->

```
[INPUT LAYER — e.g. User / Browser / API Client]
            ↓
[PROCESSING LAYER — e.g. Backend / Service]
            ↓
┌─────────────────────────────┐
│  [CORE LOGIC BLOCK]         │
│  1. [Step one]              │
│  2. [Step two]              │
│  3. [Step three]            │
└─────────────────────────────┘
            ↓
[OUTPUT LAYER — e.g. UI / Response / File]
```

---

# <img src="[ICON_URL]" width="22" height="22" align="center"/> **Features**

### <img src="[ICON_URL]" width="18" height="18" align="center"/> [Feature Name]
[1–3 lines describing what this feature does and why it matters.]

### <img src="[ICON_URL]" width="18" height="18" align="center"/> [Feature Name]
[1–3 lines describing what this feature does and why it matters.]

### <img src="[ICON_URL]" width="18" height="18" align="center"/> [Feature Name]
[1–3 lines describing what this feature does and why it matters.]

### <img src="[ICON_URL]" width="18" height="18" align="center"/> [Feature Name]
[1–3 lines describing what this feature does and why it matters.]

---

# <img src="[ICON_URL]" width="22" height="22" align="center"/> **Tech Stack**

| Layer | Technology |
|-------|------------|
| [Layer name] | [Technology name] |
| [Layer name] | [Technology name] |
| [Layer name] | [Technology name] |
| [Layer name] | [Technology name] |
| [Layer name] | [Technology name] |

---

# <img src="[ICON_URL]" width="22" height="22" align="center"/> **Setup**

<!-- Numbered steps. Each command in its own bash block. -->

1. **Clone the repo:**

```bash
git clone https://github.com/[USERNAME]/[REPO-NAME].git
cd [REPO-NAME]
```

2. **Install dependencies:**

```bash
[install command — e.g. npm install OR pip install -r requirements.txt]
```

3. **Configure environment:**

```bash
cp .env.example .env
# Fill in required keys inside .env
```

4. **[Any additional step — e.g. start infra, seed DB, download models]:**

```bash
[command]
```

5. **Run the app:**

```bash
[start command — e.g. npm run dev OR streamlit run app.py]
```

---

# <img src="[ICON_URL]" width="22" height="22" align="center"/> **Production Tips**

* [Tip 1 — e.g. use environment variables, never hardcode secrets]
* [Tip 2 — e.g. enable SSL, use reverse proxy]
* [Tip 3 — e.g. pre-cache data, use CDN]
* [Tip 4 — e.g. set up DB backups, replicas]

---

<!-- OPTIONAL SECTION — only include if project exposes a backend API -->
# <img src="[ICON_URL]" width="22" height="22" align="center"/> **API Endpoints**

### [Resource Name]

```
[METHOD] [/api/route]         — [description]
[METHOD] [/api/route/:id]     — [description]
[METHOD] [/api/route]         — [description]
```

### [Resource Name]

```
[METHOD] [/api/route]         — [description]
[METHOD] [/api/route]         — [description]
```

---

# <img src="[ICON_URL]" width="22" height="22" align="center"/> **Roadmap**

* [ ] [Planned feature 1]
* [ ] [Planned feature 2]
* [ ] [Planned feature 3]

---

# <img src="[ICON_URL]" width="22" height="22" align="center"/> **Security Notes**

* [Note 1 — e.g. API keys must be in .env, never committed]
* [Note 2 — e.g. admin routes should be protected in production]
* [Note 3 — add or remove as needed]

---

# <img src="[ICON_URL]" width="22" height="22" align="center"/> **Folder Structure**

```
[REPO-NAME]/
│
├── [folder]/          # [what it contains]
├── [folder]/          # [what it contains]
├── [folder]/          # [what it contains]
├── [file]             # [what it is]
└── README.md
```

---

# <img src="[ICON_URL]" width="22" height="22" align="center"/> **Contributing**

PRs and issues are welcome. Fork freely and build on top of this.

---

# <img src="[ICON_URL]" width="22" height="22" align="center"/> **License**

MIT License — use freely.

---

# <img src="[ICON_URL]" width="22" height="22" align="center"/> **Credits**

* [Library / tool name] — [what it's used for]
* [Library / tool name] — [what it's used for]
* [Library / tool name] — [what it's used for]

---

# Made with passion by **[YOUR NAME]**

> *[One-liner tagline — what the project does in one punchy sentence.]*

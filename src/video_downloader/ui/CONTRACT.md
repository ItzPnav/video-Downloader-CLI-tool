# Design & Motion Studio — Shared State Contract (`CONTRACT.md`)

## 1. Producer Attestation
- **Orchestrator:** `design-lead`
- **Primary Synthesis Engine:** `hallmark` + `frontend-ui-animator`
- **Governing Aesthetic Dialect:** `mission-control-design` (Cyber Terminal / Desert Ops Solar Light)
- **Axiom Isolation Attestation:** `apple-design` is strictly excluded from context and generation. Zero rounded corners (`border-radius: 0 !important`), zero backdrop-filter blur panels, and zero organic squircle easing are permitted.
- **Hallmark Pre-Emit Self-Critique:** `/* Hallmark · pre-emit critique: P5 H5 E5 S5 R5 V5 */`

## 2. State Artifacts Inventory
1. `design-tokens.json`: W3C Design Token Community Group (DTCG) token definitions with `axioms` block.
2. `design.md`: Aesthetic philosophy, The Five Unbreakable Laws, typography rules, and anti-slop guardrails.
3. `tokens.css`: Scoped CSS custom properties (`:root` and `[data-theme="light"]`), Quasar/NiceGUI zero-radius overrides, 40px radar coordinate grid, CRT `.scanline` overlay, and tactical component styles.

## 3. Consumer Bindings
- `src/video_downloader/gui.py`: Loads `tokens.css` and `design-tokens.json` directly into the NiceGUI document head and binds all 5 Tool-Kit CLI engines (`ExtractionRaceController`, `converter`, `comic_scraper`, `packager`, `ocr`) to Mission Control tactical telemetry components.

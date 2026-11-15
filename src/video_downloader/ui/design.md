/* Hallmark · pre-emit critique: P5 H5 E5 S5 R5 V5 */

# Tool-Kit CLI — Mission Control Design Specification (`design.md`)

## 1. Core Philosophy: The Tactical Media Console
`Tool-Kit CLI` is a high-performance local process orchestrator (`psutil` + LangGraph 4-agent race, FFmpeg pipelines, Scrapling/Chromium extractors, Pillow packagers, and Tesseract OCR). Its visual interface treats the viewport as a hardened **Mission Control instrument panel**, never a generic rounded SaaS template.

## 2. The Five Unbreakable Laws
1. **The Zero-Radius Mandate (`border-radius: 0 !important`):**
   Every card, button, input, tab, modal, badge, thumbnail, and scrollbar has razor-sharp 90-degree corners.
2. **Dual-Accent Semantic Integrity:**
   - **Cyber Green (`#39FF88` / `var(--green)`):** Strictly reserved for state, online indicators, verified winners, active 3px left selection strips, and crawling fuel gauges.
   - **Tactical Amber (`#FFB627` / `var(--amber)`):** Strictly reserved for primary action CTAs, input focus rings, active operation triggers, and attention readouts.
   - **Tactical Red (`#FF5C4D` / `var(--red)`):** Strictly reserved for process termination, fault alarms, and destructive actions.
3. **Strict Typography Pairing (Roman Only, Never Italic Headers):**
   - **Display Headers:** `'Big Shoulders Display', sans-serif` (weight 800, uppercase, `font-style: normal`, `letter-spacing: 0.02em`, `line-height: 0.95`).
   - **Body, Telemetry, Inputs, Logs, Code:** `'JetBrains Mono', monospace` (weights 400, 500, 700).
4. **Atmospheric Radar Grid & CRT Scanline Overlay:**
   - 40px × 40px coordinate grid (`var(--grid)`) over near-black void (`#0A0D10`) or Desert Ops solar canvas (`#EDEDE9`).
   - Non-interactive `.scanline` overlay (`pointer-events: none`).
5. **No Native OS Dialogs & Zero Emojis:**
   - Never invoke `window.alert()` or `window.confirm()`. Use custom `SystemDialogModal` and the built-in Server-Side Tactical Disk Browser modal.
   - Zero emojis anywhere in UI labels, headers, or buttons. Use technical ASCII/monochrome vector glyphs.

## 3. Signature Tactical Components
- **Physical Rocker Switch (`.rocker-switch`):** 38×20px recessed slot with 14×14px mechanical plate (`cubic-bezier(0.3, 1.5, 0.5, 1)`) and green phosphor bloom when armed.
- **Crawling Striped Fuel Gauge (`.gauge-block` / `.gauge-fill`):** Diagonal striped progress bar (`@keyframes fuelCrawl 1.6s linear infinite`) with monospace header readout (`TELEMETRY // PCT%`).
- **Pulsing Radar Dot & Eyebrow (`.eyebrow`):** 6×6px breathing green radar dot (`@keyframes radarPulse`) paired with uppercase wide-tracked telemetry labels.
- **24-Hour Military ZULU Clock (`.zulu-clock`):** Live `HH:MM:SS ZULU` readout in the top command header.
- **3px Green Selection Strip (`.tactical-row`):** `border-left: 3px solid var(--green)` with `rgba(57, 255, 136, 0.05)` wash on active/completed items.

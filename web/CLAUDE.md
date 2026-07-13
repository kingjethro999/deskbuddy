# DeskBuddy Web — CLAUDE.md

This is the single source of truth for building the DeskBuddy marketing/product
site in Next.js. Read this fully before writing any code. Architecture-first,
no phased half-builds — implement complete sections, not scaffolding with TODOs.

---

## 1. Product Summary (for copy accuracy)

DeskBuddy is a voice-powered desktop companion. Install it from the terminal,
say the wake word ("buddy"), and a styled GUI appears that listens to you and
operates your computer hands-off — opening apps, running commands, typing,
pressing keys, reading files, taking screenshots.

Key facts Claude Code must get right in all copy:
- Tagline: **"Alexa, but for your PC."**
- Built by King Jethro Jerry.
- Hybrid architecture: DeskBuddy is a voice/input skin over a pluggable brain.
  The brain can be **native** (own OpenAI-compatible tool-calling loop) or
  **hermes** (shells out to the `hermes` CLI as the engine). The installer
  provisions Hermes automatically if it's missing.
- Four layers, cleanly separated:
  - **BRAIN** (`brain/`) — the agent, pluggable backends (native / hermes)
  - **EARS + MOUTH** (`voice/`) — STT (Whisper) + TTS (piper / edge / espeak)
  - **HANDS** (`hands/`) — PC control tools (apps, shell, keyboard, mouse, files, screen)
  - **FACE** (`face/`) — the styled GUI window (tkinter now, Electron/Tauri later)
- Custom wake-word engine, built from scratch: MFCC features + DTW template
  matching, numpy only. No Porcupine, no paid SDK, fully offline and free.
  Commands: `buddy enroll` (teach it your wake word), `buddy listen` /
  `buddy --voice` (streaming mic detection).
- The **Wayland lesson**: Wayland blocks apps from injecting input into other
  windows. `hands/providers.py` picks the best method at runtime —
  `X11Provider` (xdotool/wmctrl), `WaylandProvider` (ydotool, needs
  `/dev/uinput`), or `NullProvider` (explains the limitation, suggests an
  "Ubuntu on Xorg" session for full control). This is a trust-building detail,
  not a footnote — technical users notice when a project has actually reckoned
  with a real platform limitation.
- Install is one line, cross-platform:
  - Linux/macOS/WSL2: `curl -fsSL https://raw.githubusercontent.com/kingjethro999/deskbuddy/main/scripts/install.sh | bash`
  - Windows PowerShell: `iex (irm https://raw.githubusercontent.com/kingjethro999/deskbuddy/main/scripts/install.ps1)`
  - Then: `buddy setup` → `buddy enroll` → `buddy`
- Audience is dual: developers who care about the pluggable brain and the
  Wayland/X11 handling, and non-technical users who just want a voice buddy
  that runs their PC. Every section should work on both levels — technical
  depth available, never required to understand the pitch.
- Status: project scaffold, pluggable brain (native + hermes), 8 PC-control
  tools, STT/TTS with graceful fallbacks, terminal wizard, tkinter GUI,
  installer — all working now. Next: always-on wake word via openWakeWord,
  streaming STT with silence detection, screen-vision tool, richer GUI
  (waveform), packaging.

Never invent features, pricing, or stats not in this brief or the repo README.

---

## 2. Tech Stack (exact versions/packages to install)

```bash
npx create-next-app@latest deskbuddy-web --typescript --tailwind --app --src-dir --import-alias "@/*"
```

- **Next.js 15**, App Router, React Server Components by default. Only mark
  `"use client"` on components that actually need interactivity, state, or
  browser APIs (animation triggers, canvas, copy-to-clipboard).
- **Tailwind CSS v4** — use the new CSS-based config (`@theme` in globals.css),
  not a JS tailwind.config unless a plugin requires it.
- **motion** (npm package `motion`, import from `motion/react`) — this is the
  renamed Framer Motion. Use for: fade/slide reveals, hover/tap states, layout
  animations, staggered lists, page transitions.
- **gsap** + **ScrollTrigger** — use for anything scroll-scrubbed or pinned:
  the architecture diagram assembly, the terminal typing simulation tied to
  scroll position, any multi-step sequenced timeline (3+ chained animations).
  Register the plugin once in a client-only utility:
  ```ts
  import { gsap } from "gsap";
  import { ScrollTrigger } from "gsap/ScrollTrigger";
  if (typeof window !== "undefined") gsap.registerPlugin(ScrollTrigger);
  ```
- **@react-three/fiber** + **@react-three/drei** — used in exactly ONE hero
  moment (see Section 5). Do not scatter 3D elsewhere; it's expensive and
  dilutes the effect.
- **lenis** (`@studio-freight/lenis` or the newer `lenis` package) — smooth
  scroll, initialized once in a root client provider, synced with GSAP's
  ticker so ScrollTrigger stays accurate.
- **shadcn/ui** — init with `npx shadcn@latest init`, pull in: `button`,
  `tabs`, `dialog`, `tooltip`, `accordion`. Style: default/neutral base,
  theme overridden via CSS variables (Section 4).
- **lucide-react** — all icons. Never mix in another icon set.
- **clsx** + **tailwind-merge** (`cn()` utility, standard shadcn pattern).
- **sonner** for toast (e.g. "Copied to clipboard").

Do not add: styled-components, emotion, Chakra, MUI, Bootstrap, jQuery,
Framer Motion's old package name, or any icon set besides lucide.

---

## 3. Fonts

Load via `next/font/google`, variable fonts, `display: "swap"`, no external
`<link>` tags (avoids layout shift and extra requests).

- **Display / headings:** Bricolage Grotesque — has warmth and a slight
  structural quirk that fits a "friendly AI buddy" identity without tipping
  into generic startup-sans territory. Use weights 500/600/700 for headings.
- **Body:** Geist Sans — crisp at small sizes, reads well for longer
  explanatory copy (architecture section, Wayland explainer).
- **Monospace:** Geist Mono — used specifically for terminal/install command
  blocks, CLI examples, and file tree diagrams. This matters more than usual
  here because the core first interaction with the product IS a terminal
  command; it needs to look authoritative and copy-pasteable.

```ts
import { Bricolage_Grotesque, Geist, Geist_Mono } from "next/font/google";

const display = Bricolage_Grotesque({ subsets: ["latin"], variable: "--font-display" });
const body = Geist({ subsets: ["latin"], variable: "--font-body" });
const mono = Geist_Mono({ subsets: ["latin"], variable: "--font-mono" });
```

Apply variables on `<html>`, reference as `font-[var(--font-display)]` etc.
in Tailwind, or map them to `font-sans` / `font-mono` in the theme so normal
utility classes just work.

---

## 4. Design Tokens

Dark theme by default — fits the "terminal-native AI agent" identity. Avoid
the generic purple-to-blue AI gradient every SaaS AI product uses; go with an
amber/teal pairing that reads warmer and more "buddy," less "enterprise AI."

```css
@theme {
  --color-bg:            #0B0E0D;   /* near-black, slight green undertone */
  --color-surface:       #121614;   /* card/panel background */
  --color-surface-raised:#181D1B;   /* elevated cards, modals */
  --color-border:        #232A27;

  --color-text-primary:  #EDEFEE;
  --color-text-secondary:#9CA8A3;
  --color-text-muted:    #6B7570;

  --color-accent:        #4AB3D4;   /* teal — primary CTA, links, active states */
  --color-accent-warm:   #E8521A;   /* amber/orange — highlights, wake-word pulse, emphasis */
  --color-accent-dim:    #1B5C52;   /* deep teal — section backgrounds, subtle fills */

  --color-success:       #4ADE80;
  --color-code-bg:       #0D1110;

  --radius-sm: 0.375rem;
  --radius-md: 0.75rem;
  --radius-lg: 1.25rem;
}
```

(These are the same brand-adjacent teal/orange values King has used on prior
projects — reuse them here for visual consistency across his portfolio, but
they also happen to be the right choice on pure design merit: teal reads
calm/technical, orange reads warm/alive, good pairing for "an agent that
listens to you.")

Rules:
- Body copy stays on `--color-text-secondary`, never pure white — reduces
  the "AI slop" high-contrast wall-of-white-text look.
- `--color-accent-warm` is reserved for the wake-word/listening motif
  (mic pulse, waveform, "buddy is listening" states) — don't use it for
  generic buttons, or it loses its meaning.
- `--color-accent` (teal) is the default interactive color: links, primary
  buttons, focus rings, active tab indicators.

---

## 5. Page Structure & Sections

Build as individual components in `src/components/sections/`, composed in
`src/app/page.tsx`. Each section is its own file, no 1000-line page.tsx.

### 5.1 Hero (`hero.tsx`)
- Headline: "Alexa, but for your PC." Subhead: one line on install-from-
  terminal, say "buddy," GUI takes over.
- Terminal block (Geist Mono) showing the curl install command, with a copy
  button. On copy: icon swaps to a checkmark via `motion`, sonner toast
  confirms "Copied."
- Hero visual: **the one R3F moment.** A soft, low-poly animated blob/sphere
  made of instanced points or a distorted icosahedron (drei's `MeshDistortMaterial`
  or a custom shader) that idles with gentle noise-driven movement and pulses
  outward when the page loads, suggesting "listening." Keep it performant:
  low poly count, no post-processing stack, pause the render loop when the
  hero scrolls out of view (`useInView` + conditionally stop the frame loop).
  Must respect `prefers-reduced-motion`: if set, render a static gradient
  orb instead, no animation loop at all.
- CTA buttons: primary ("Install now" — scrolls to quick start), secondary
  ("View on GitHub").

### 5.2 Live Wake-Word Demo (`wake-word-demo.tsx`)
- A canvas or SVG waveform/bar visualizer driven by a sine + noise function
  (NOT real microphone audio — this is illustrative, be honest about that
  if it's ever asked, but don't caption it as fake either, just present it
  as a demo of the listening state).
- Idle state: flat, quiet, muted teal bars.
- On scroll-into-view (GSAP ScrollTrigger), transitions to an "active
  listening" state: bars animate with more amplitude, color shifts toward
  `--color-accent-warm`, a small label types out via GSAP (e.g. text
  reveals "buddy" being said, then the response state).
- This is the section that should make a non-technical visitor instantly
  get the pitch without reading anything.

### 5.3 Architecture Diagram (`architecture.tsx`)
- Pinned scroll section (GSAP `ScrollTrigger` with `pin: true`) — as the user
  scrolls through this section's scroll distance, four layer cards (BRAIN,
  EARS+MOUTH, HANDS, FACE) animate in and connect with drawn SVG lines,
  building the stack top to bottom or center-out.
- Each card: layer name, one-line role, 2-3 concrete examples pulled directly
  from Section 1 (e.g. HANDS → "apps, shell, keyboard, mouse, files, screen").
- Use `lucide-react` icons per layer: Brain → `BrainCircuit`, Ears/Mouth →
  `AudioWaveform` or `Mic`, Hands → `MousePointerClick` or `Keyboard`,
  Face → `AppWindow`.
- End state of the pin: all four connected with a labeled line showing the
  pluggable brain branching to "native" and "hermes."

### 5.4 The Wayland/X11 Story (`platform-story.tsx`)
- Toggle or tabs (shadcn `Tabs`) between "X11" / "Wayland" / "Neither
  detected."
- Short diagram or icon-based flow showing DeskBuddy's runtime provider
  selection: detect session type → pick `X11Provider` (xdotool/wmctrl) or
  `WaylandProvider` (ydotool, needs `/dev/uinput`) → or fall back to
  `NullProvider` with an explanation and the "log into Ubuntu on Xorg"
  suggestion.
- Keep this skippable/collapsible (shadcn `Accordion` works well) for
  non-technical users, but don't hide it — it's a real trust signal for
  developers evaluating the project.

### 5.5 Quick Start (`quick-start.tsx`)
- shadcn `Tabs`: "GUI only" vs "Developer / CLI" install paths.
- GUI tab: the one-line curl/iex install, then `buddy setup` → `buddy enroll`
  → `buddy`.
- Dev tab: the full dev quick start from the README (`venv`, `pip install -e .`,
  `buddy doctor`, `buddy --text`, `buddy --voice`, pytest command).
- Every code block: Geist Mono, syntax-dim background (`--color-code-bg`),
  copy button on each block independently.

### 5.6 Status / Roadmap (`status.tsx`)
- Two-column or two-list layout: "Working now" vs "Next."
- Stagger-in animation via `motion` (`staggerChildren` on the list container)
  when scrolled into view — simple, not GSAP-scrubbed, this section doesn't
  need scroll-linked complexity.
- Use `lucide-react`'s `CheckCircle2` for shipped items, `Circle` or `Clock`
  for upcoming.

### 5.7 Footer (`footer.tsx`)
- Attribution line ("Built by King Jethro Jerry"), GitHub link, and a nod to
  Hermes as the inspiration/optional engine, per the README's framing.

---

## 6. Animation Rules (cross-cutting)

- **Purposeful over decorative.** Every animation should reinforce meaning
  (listening, connecting, assembling) — not autoplay-everything on load.
  Nothing animates just to prove it can.
- **Scroll-linked by default** for anything narrative (architecture, wake-word
  demo). **Load/interaction-linked** (motion, not GSAP) for anything local
  (button hover, tab switch, accordion open, list stagger).
- **`prefers-reduced-motion` must be respected everywhere**, not just the
  hero. Wrap a shared hook, e.g.:
  ```ts
  const prefersReducedMotion = useReducedMotion(); // from `motion/react`
  ```
  and gate GSAP timelines behind `window.matchMedia("(prefers-reduced-motion: reduce)").matches`
  at setup time — either skip the animation entirely or drop to instant/opacity-only.
- **Performance:** kill/pause GSAP ScrollTriggers and R3F render loops for
  sections not in view. Use `will-change` sparingly and only on the element
  actually animating, not parents.
- Lenis smooth scroll must be synced to GSAP's ticker so ScrollTrigger
  calculations stay correct:
  ```ts
  lenis.on("scroll", ScrollTrigger.update);
  gsap.ticker.add((time) => lenis.raf(time * 1000));
  gsap.ticker.lagSmoothing(0);
  ```

---

## 7. File Structure

```
deskbuddy-web/
  src/
    app/
      layout.tsx          # fonts, Lenis provider, theme, metadata
      page.tsx             # composes sections in order
      globals.css          # @theme tokens, base styles
    components/
      sections/
        hero.tsx
        wake-word-demo.tsx
        architecture.tsx
        platform-story.tsx
        quick-start.tsx
        status.tsx
        footer.tsx
      ui/                  # shadcn primitives live here
      shared/
        terminal-block.tsx # reusable copy-able code block (Geist Mono)
        smooth-scroll-provider.tsx  # Lenis + GSAP ticker sync, client component
        section-heading.tsx
    lib/
      gsap.ts              # ScrollTrigger registration, shared config
      utils.ts             # cn() helper
    hooks/
      use-reduced-motion-safe.ts
```

---

## 8. Content & Copy Rules

- Never use em dashes or en dashes in any copy, headings, or generated text
  anywhere on the site (consistent constraint across King's projects — use
  periods, commas, or parentheses instead).
- Copy should read confidently but not oversell — no "revolutionary,"
  "game-changing," "next-generation." Let the wake-word demo and architecture
  diagram do the persuading.
- Every technical claim (Wayland/X11 handling, MFCC+DTW wake word, pluggable
  brain) must match Section 1 exactly. If Claude Code is unsure of a detail,
  check the repo README rather than inferring.

---

## 9. Accessibility & SEO

- Full keyboard navigation through tabs/accordion/copy buttons (shadcn
  primitives handle most of this out of the box, don't override focus styles
  away).
- All animated/canvas visualizations need an `aria-label` or adjacent text
  equivalent describing what they show, since they're decorative/illustrative
  rather than data-bearing.
- Semantic heading hierarchy (`h1` once in hero, `h2` per section).
- `next/og` or a static OG image for social previews; metadata title/description
  drawn from Section 1's tagline and summary, not generic Next.js defaults.

---

## 10. Definition of Done for a Section

A section is complete when: it has real copy (not lorem ipsum), it degrades
gracefully with `prefers-reduced-motion`, it works at mobile width (animations
simplify, GSAP pins disabled or shortened on small viewports), and it uses
only the tokens/fonts/icon set defined above — no ad hoc colors or a stray
icon library slipping in.
# FaradAI — Design System

> Visual identity spec for **FaradAI** (*Asistente de Física*).
>
> Use this document as the brand reference when generating any FaradAI
> artifact: UI components, slides, posters, or any visual piece. It is
> written to be machine-readable — paste it into an AI prompt as-is and
> the model should have everything it needs to stay on-brand.
>
> **Source of truth.** The Figma file (shared with the project's UX
> designer, Justo) and the CSS custom properties in
> `app/static/tokens.css`. If they ever disagree: the Figma file wins for
> visual intent; `tokens.css` wins for what the running app actually shows.

---

## 1. Brand overview

- **Project name:** **FaradAI** — a play on *Faraday* + *AI*. The capital
  *AI* at the end is the only stylization; the rest is one word.
- **Subject:** *Asistente de Física* — a Socratic chat assistant that
  helps first-year students of *Física 1* at UNR work through exercises
  without solving them directly.
- **Sponsor:** Nair — Physics professor, Facultad de Ciencias Bioquímicas y
  Farmacéuticas, Universidad Nacional de Rosario (UNR).
- **Audience:** first-year university students, ~18 years old, often on
  low-end hardware and slow connections.
- **Tone:** pedagogical, calm, encouraging, never condescending. The
  assistant *guides with questions*, never with answers. The visual
  identity should feel like a quiet study partner, not a chatbot.

## 2. Brand principles

1. **Clarity over cleverness.** The student should never have to decode
   the interface.
2. **Calm.** Soft green palette, generous whitespace, no harsh contrast.
3. **One voice.** The chat *is* the product. Everything else defers to it.
4. **Academic-friendly.** Looks credible to a faculty committee, friendly
   to a tired 18-year-old at 11pm.
5. **Light by default.** First paint must be fast on a slow connection.
   Self-host fonts, avoid heavy imagery.

## 3. Logo

Two variants are committed in `app/static/img/`:

- **`logo-icon.svg`** — the **F** mark. Monochrome, filled with
  `--color-text` (`#202725`). Use when space is tight: sidebar header at
  small sizes, favicon, app icons, anywhere the wordmark won't fit.
- **`logo-wordmark.svg`** — the **FaradAI** wordmark with the icon
  embedded. Use when you can spare a full brand line: cover slides,
  posters, documentation, the sidebar header.

### Logo do

- Use on light backgrounds only: `--color-surface` (`#FFFFFF`) or
  `--color-brand-bg` (`#E3EAE7`).
- Keep clear space around the logo equal to the icon's height.
- Below ~120px width: use the icon variant. Above ~120px: switch to the
  wordmark.

### Logo don't

- Don't recolor the logo. No green, no white-on-green, no gradient, no
  outline-only versions. The dark monochrome is the brand.
- Don't place it on a busy background or a photograph.
- Don't stretch, skew, rotate, or add drop shadows.

## 4. Color palette

All hex values come from `app/static/tokens.css`. The palette is
intentionally narrow.

### Brand greens

| Token                          | Hex       | Role                                                       |
|--------------------------------|-----------|------------------------------------------------------------|
| `--color-brand-primary`        | `#D4FBED` | User bubble, primary button, focus glow accent             |
| `--color-brand-primary-hover`  | `#C7E8D8` | Hover state for primary; greeting name color               |
| `--color-brand-primary-soft`   | `#ABDDC4` | Input border at rest, focus ring (3px halo)                |
| `--color-brand-bg`             | `#E3EAE7` | Page background, soft surface tint behind the app shell    |

### Neutrals

| Token                  | Hex       | Role                                                  |
|------------------------|-----------|-------------------------------------------------------|
| `--color-text`         | `#202725` | Body text, logo fill                                  |
| `--color-text-muted`   | `#555C59` | Captions, hints, metadata, disabled labels            |
| `--color-surface`      | `#FFFFFF` | Cards, sidebar, chat column                          |
| `--color-surface-alt`  | `#F8FAF9` | Disabled input fill, subtle alt surface              |
| `--color-border`       | `#D7DFDB` | Subtle dividers, disabled controls                   |

### States (reserved)

| Token            | Hex       | Role                |
|------------------|-----------|---------------------|
| `--color-error`  | `#D64242` | Validation errors   |

### Usage ratios

The brand greens are intentionally **soft**. For body text use
`--color-text` (`#202725`) on `--color-surface` (`#FFFFFF`) — that's the
contrast pair that carries readability. Greens are accents, not
backgrounds for text.

If a generated artifact needs more than the four greens, ask before
introducing new ones. The discipline is part of the brand.

## 5. Typography

### Geist (primary UI font)

- Sans-serif. By **Vercel**. License: SIL OFL 1.1. Self-hosted as
  `.woff2` under `app/static/fonts/`.
- Weights used: **400** regular (body), **500** medium (user bubble,
  emphasis), **600** semibold (buttons, headings).
- Use Geist for everything except the two display moments listed below.

### Source Serif 4 (display only)

- Serif. By **Adobe**. License: SIL OFL 1.1. Self-hosted as `.woff2`.
- **Reserved for two moments only:**
  1. The **"FaradAI"** wordmark in the sidebar header.
  2. The student's **name** in the welcome greeting
     (*"¡Hola, **Sofía**!"* — name in serif italic).
- One weight: **400 regular**.

> The serif is a brand signal, not a default body face. Using it
> elsewhere dilutes it.

### Type scale

| Token               | Value          | Use                                  |
|---------------------|----------------|--------------------------------------|
| `--font-size-sm`    | `0.875rem` (14px) | Captions, hints, disclaimer        |
| `--font-size-base`  | `1rem` (16px)     | Body, inputs, buttons              |
| `--font-size-lg`    | `1.125rem` (18px) | Emphasis                           |
| `--font-size-xl`    | `1.25rem` (20px)  | H1, brand wordmark                 |
| `--font-size-2xl`   | `2rem` (32px)     | Hero greeting                      |

### Line heights

| Token                  | Value  | Use                          |
|------------------------|--------|------------------------------|
| `--line-height-tight`  | `1.25` | Greeting, hero, large headings |
| `--line-height-base`   | `1.5`  | Body and chat messages        |

### Font stacks (for non-CSS contexts)

```text
Sans:  Geist, system-ui, -apple-system, BlinkMacSystemFont,
       "Segoe UI", Roboto, sans-serif

Serif: "Source Serif 4", Georgia, "Times New Roman", serif
```

## 6. Spacing

A 4-pixel base scale. Stick to these — they line up with the Figma grid.

| Token         | Value            | Approx |
|---------------|------------------|--------|
| `--space-xs`  | `0.25rem`        | 4px    |
| `--space-sm`  | `0.5rem`         | 8px    |
| `--space-md`  | `1rem`           | 16px   |
| `--space-lg`  | `1.25rem`        | 20px   |
| `--space-xl`  | `1.5rem`         | 24px   |
| `--space-2xl` | `2rem`           | 32px   |

## 7. Radii

| Token           | Value          | Use                                  |
|-----------------|----------------|--------------------------------------|
| `--radius-sm`   | `0.25rem` (4px)  | Subtle corner rounding             |
| `--radius-md`   | `0.5rem` (8px)   | Medium rounded                     |
| `--radius-lg`   | `1rem` (16px)    | Chat bubble                        |
| `--radius-pill` | `9999px`         | Chips, send button, fully rounded  |

The chat experience leans heavily on `--radius-pill`. Use it for any
"speech-like" element to keep the conversational tone.

## 8. Shadows

Two-layer drop-shadows (ambient + key), tinted with the brand text color
(`#202725`) at low opacity. Three tiers.

| Token        | Layers                                                                                  |
|--------------|-----------------------------------------------------------------------------------------|
| `--shadow-sm`| `0 1px 1px rgba(18,22,21,0.05), 0 2px 4px rgba(18,22,21,0.08)`                            |
| `--shadow-md`| `0 2px 3px rgba(18,22,21,0.08), 0 6px 10px rgba(18,22,21,0.14)`                           |
| `--shadow-lg`| `0 4px 8px rgba(18,22,21,0.12), 0 12px 20px rgba(18,22,21,0.18)`                          |

**Note for print artifacts:** the original Figma alphas (0.02–0.10) were
too faint against the pale background; each tier was bumped ~2× for
screen use. Print artifacts (posters, slides) can use slightly heavier
alphas because paper reflects less than screens.

## 9. UI components

The component layer lives in `app/static/style.css`. These are the
patterns the system supports — useful as reference if you're adapting the
brand to non-screen artifacts.

### Sidebar (left column, 280px wide on desktop)

- Brand (icon + wordmark) at top.
- **Índice de temas** section listing topics grouped by area
  (Cinemática, Dinámica, Teoría de errores).
- Sticky on desktop; stacks above the chat column on mobile (≤768px).

### Chat column

- Vertical stack of messages.
- Generous vertical padding (`--space-xl`).
- Scrolls independently.

### Messages

- **User bubble.** Green pill (`--color-brand-primary`), right-aligned,
  medium weight (500), with `--shadow-sm`. Rounded to `--radius-pill`.
- **Assistant message.** *No bubble.* Left-aligned plain text on the
  surface. This mirrors the designer's frames: the AI speaks plain; only
  the user gets a pill.
- **Welcome greeting.** Oversized (32px), student's name in serif italic
  in `--color-brand-primary-hover`.

### Inputs

- Rounded to `--radius-pill`.
- Border `--color-brand-primary-soft` at rest, `--color-brand-primary`
  on focus with a 3px `--color-brand-primary-soft` ring + `--shadow-sm`.
- Disabled: `--color-surface-alt` fill, `--color-border` border, no
  pointer.

### Buttons

- **Primary** (e.g. *Continuar*, *Enviar*): `--color-brand-primary`
  fill, semibold, `--radius-pill`. Hover: `--color-brand-primary-hover`.
- **Disabled**: `--color-border` fill, `--color-text-muted` text.

## 10. Layout patterns

### App shell (web)

Two-column flex layout:

- Sidebar: fixed `280px`, sticky, `--shadow-sm` on the right edge.
- Chat column: `flex: 1`, fills the remaining space.
- Max width `1200px`, centered.
- Below `768px`: stacks vertically. Sidebar becomes a top section with a
  bottom border (`--color-border`).

### Suggested poster layout (academic A0)

A typical academic poster for this brand would use a **three-column
grid**:

- **Column 1** — Context. Title, sponsor (Nair, UNR), what the
  assistant does in one sentence.
- **Column 2** — How it works. RAG over the course's own PDFs, Socratic
  layer, name-based identity, persistence.
- **Column 3** — Try it now. QR code + URL, contact.

Top band: **FaradAI** wordmark + UNR institutional badge. Bottom band:
small citation line and/or disclaimer.

## 11. Print and non-screen applications

When the brand leaves the screen, a few adjustments help.

### Color fidelity

- Screens are emissive (RGB). Paper is reflective. The pale green
  `#D4FBED` will print almost white on uncoated paper.
  - For posters: use `#C7E8D8` (`--color-brand-primary-hover`) as the
    "primary" green on print — it's the readable version.
  - Reserve `#D4FBED` for the lightest tints only.
- Convert to CMYK for offset, or use the printer's ICC profile for
  digital print. Test on the actual paper before final.

### Sizing guidance for posters

| Element            | A0 (841×1189 mm)  | A1 (594×841 mm) |
|--------------------|-------------------|------------------|
| Body text          | ~24pt             | ~18pt           |
| Section heading    | ~48pt             | ~36pt           |
| Brand wordmark     | ~120mm wide       | ~90mm wide      |
| QR code (minimum)  | 30×30 mm          | 25×25 mm        |

### Typography in print

- Geist and Source Serif 4 are **SIL OFL 1.1** — safe to embed in print
  artifacts as long as the license file travels with the file.
- For print, prefer OpenType (`.otf`) or TrueType (`.ttf`) over `.woff2`
  if the layout tool needs them. Convert with `fonttools` or download
  the static fonts from Google Fonts.

### QR code placement

- Place the QR **near the call to action** (*"Probalo ahora" / "Try it
  now"*), not buried in a footer.
- Give it generous quiet zone — at least 4 modules of white space around
  the code.
- **Always include the URL in human-readable text next to the QR.** For
  accessibility, and for anyone whose phone won't scan.
- Use a high-contrast pairing: dark QR on `--color-surface`, not on a
  pale green tint.

## 12. Do / Don't

### Do

- Pull values from `tokens.css` rather than hard-coding hex codes.
- Use Geist for body. Reserve Source Serif 4 for the brand wordmark and
  the welcome greeting.
- Keep contrast on body text using `--color-text` on `--color-surface`.
- Test on small screens before shipping visual changes.
- When generating an artifact for the brand, paste this file (or the
  relevant section) into the AI prompt so the model stays on-system.

### Don't

- Don't introduce new greens outside the palette. If a new shade is
  needed, discuss with the designer.
- Don't use Source Serif 4 for body text.
- Don't place the logo on a colored background.
- Don't weaken the Socratic layer's brand association with playful,
  gamified, or "chatbot" visuals. The assistant is a teacher.

## 13. Source of truth

- **CSS tokens** — `app/static/tokens.css` (colors, typography, spacing,
  radii, shadows as CSS custom properties).
- **Component styles** — `app/static/style.css` (consumes tokens).
- **Logo assets** — `app/static/img/logo-icon.svg`,
  `app/static/img/logo-wordmark.svg`.
- **Fonts** — `app/static/fonts/Geist-Regular.woff2`,
  `Geist-Medium.woff2`, `Geist-SemiBold.woff2`,
  `SourceSerif4-Regular.woff2`.
- **Figma file** — owned by Justo (project UX designer). Local PNG
  exports of the frames live in `docs/design/figma-exports/` (gitignored;
  not source files).
- **This document** — `docs/design/DESIGN.md`. Update when tokens change
  in `tokens.css` or when the designer's Figma file evolves.

---

*Last updated: 2026-09-02. Maintained by Fabián.*

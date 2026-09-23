# Frontend design

AquaLens reads as a *scientific instrument* in the app shell and as
*editorial* in the marketing chrome. References for the quality bar
are Linear (motion + density), Vercel and Resend (typographic
restraint), Stripe (chart depth), Sentinel Hub EO Browser and NASA
Worldview (map-first chrome), and Mapbox storytelling pages
(scroll-driven geo demos).

## Tokens

All colors are authored in OKLCH for perceptually uniform shades. They
live in [`frontend/app/globals.css`](../frontend/app/globals.css) and
are exposed to Tailwind via
[`frontend/tailwind.config.ts`](../frontend/tailwind.config.ts).

| Group | Tokens |
| --- | --- |
| Brand | `--aqua-50 … --aqua-950` (11 stops) |
| Risk | `--risk-low/--risk-medium/--risk-high` (+ foregrounds) |
| Neutrals | `--ink`, `--paper`, `--surface-0…3`, `--muted/--subtle` |
| Surfaces | `--card`, `--popover`, `--accent`, `--secondary` |
| Border/Input/Ring | `--border`, `--input`, `--ring` |
| Type | `--font-sans` (Geist), `--font-mono` (Geist Mono), `--font-display` (Instrument Serif) |

Light is the default in CI builds, dark is the runtime default in the
ThemeProvider. Both are fully designed.

## Typography

- Body, UI, charts → Geist Sans variable.
- Numbers, scene IDs, code → Geist Mono variable.
- Marketing display headlines → Instrument Serif.

Custom Tailwind type scale (12 / 13 / 14 / 16 / 18 / 20 / 24 / 32 / 48 /
64 / 80) with line-height and letter-spacing tuned per step.

## Motion

The `framer-motion`-based primitives live in `components/motion/*`:

- `FadeIn` — viewport-triggered fade + 12 px translate-up over 320 ms
  with the brand easing `[0.22, 1, 0.36, 1]`.
- `Stagger` / `StaggerItem` — list children animate in with a 60 ms
  cascade.
- `AnimatedNumber` — tweens a numeric prop with `framer-motion`'s
  `animate()` controller.

Bespoke animations:

- `RiskBadge` — SVG ring fills from 0 to the score over 900 ms with a
  spring; the colour swaps when the level changes.
- Top nav — glass-blur on scroll via a `scrollY > 12` threshold.
- Marketing CTA / feature cards — hover lift + subtle gradient overlay.
- Citations strip — pure CSS `marquee-x` keyframe with a left/right mask
  fade.

Every animation is gated behind `useReducedMotion()`. When the OS
setting is on, motion collapses to opacity-only changes.

## Accessibility

- Skip-to-content link in the root layout.
- Keyboard-only navigable; visible focus ring uses the `--ring` token.
- ARIA labels on the map (`role="region"`), the basemap switcher,
  the place / coordinate inputs, and chart canvases.
- Forms use `<Label>` + `aria-describedby` for errors and toasts
  acknowledge success via `sonner` (which announces via a polite
  live-region by default).
- Risk badge renders the human-readable score in an `role="img"`
  wrapper with an `aria-label`.

## Performance

- The MapLibre map and its basemap switcher are dynamically imported
  with `ssr: false`. Only the `/monitor` and `/sessions/[id]` chunks
  load them.
- Map style assets are static JSON files served from `/map-styles/*`
  with a one-year `Cache-Control`.
- Geist fonts come from `next/font/google` (subset, preloaded, swap).
- Lucide and Framer Motion are listed in
  `experimental.optimizePackageImports` so Next ships fewer KBs.
- TanStack Query defaults: `staleTime: 30s`, no refetch on focus, retry
  on 5xx only.
- Session detail polls every 2 s while processing, then stops.

## File map

```
app/
  layout.tsx                 # fonts, providers, theme, sonner, command menu
  globals.css                # OKLCH tokens for both themes
  (marketing)/...            # public pages
  (app)/...                  # in-app pages
components/
  ui/                        # shadcn primitives
  chrome/                    # logo, top nav, app sidebar, command menu, theme toggle, footer
  marketing/                 # hero, workflow, agent surface, indices showcase, citations, CTA
  map/                       # MapLibre wrapper, basemap switcher, place / coordinate search, mini-map
  session/                   # session wizard, risk badge/card, index grid/table, scene metadata, processing skeleton, agent trace, analysis summary
  evidence/                  # evidence form, evidence list
  report/                    # download button
  motion/                    # fade-in, stagger, animated-number
lib/
  api-client.ts              # typed fetch wrapper
  api-types.ts               # mirrored Pydantic schemas
  query-client.ts, query-keys.ts
  format.ts, geo.ts, env.ts, seo.ts, utils.ts
hooks/
  use-sessions.ts, use-water-bodies.ts, use-evidence.ts
```

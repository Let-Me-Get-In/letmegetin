# Design System — LetMeGetIn

The visual world is warm, editorial and quiet: paper, ink, one green. It should feel like a
well-set reference book, not a startup dashboard. The accessibility record is the hero asset.

## Tokens

Defined as Tailwind theme variables in `web/src/app/globals.css`; components never hardcode
colour except for the fixed dark API band and the soft card shadow.

| Token | Light | Dark |
| --- | --- | --- |
| `paper` | `#f7f4ec` | `#101613` |
| `ink` | `#18211c` | `#eef2eb` |
| `accent` | `#1f6f4a` | `#7fd1a6` |
| `accent-soft` | `#e2efe6` | `#17261d` |
| `line` | `#d8ddd4` | `#2a352e` |
| `muted` | `#5d6a61` | `#a3b0a6` |
| `warn` | `#a3521f` | `#e0a07a` |

Radii: `rounded-md` for controls, `rounded-full` for pills, square or `rounded-sm` for cards.
Borders are 1px `line`. Shadows are soft and low: `0 18px 45px -32px rgba(24,33,28,0.55)`.

## Typography

- Display: **Literata** (`--font-display`), 400/600, tight tracking (`-0.02em`) on large headings.
- Body: system sans (`--font-sans`), 16px base, `leading-relaxed` for prose.
- Section headings: `text-4xl sm:text-5xl`, max 13–18ch.
- Eyebrow labels: uppercase, `text-[0.7rem]`, `tracking-[0.16em]`, muted — used for metadata,
  never as a kicker above a heading.
- Numbers: display face, `tabular-nums`.

## Layout

- App shell: `max-w-6xl`, `px-4`, `py-8`.
- Marketing shell: full-bleed sections; inner content `max-w-6xl px-4`, `py-16 sm:py-24`.
- Hairline rules (`border-line`) separate sections; no card grid as page structure.
- Breakpoints: mobile first, one column; `sm` for inline nav and two-column metadata;
  `lg` for split heroes and sticky section headings.

## Components

- **Buttons**: accent fill, paper text, `rounded-md`, `px-5 py-3`, hover opacity 90%.
  Secondary actions are underlined text links with `underline-offset-4`.
- **Inputs**: paper fill, 1px line, 12px left padding for a search icon, focus border accent.
- **Record card**: bordered paper panel, small uppercase header row, place name in display,
  green pill, criteria rows separated by hairlines with a trailing check.
- **Pills**: `accent-soft` fill, `accent` text, full radius, 14px medium.
- **Marketing header**: wordmark left; section anchors, locale switch and app CTA right.
  On mobile only the wordmark and locale switch remain, keeping one 61px row.
- **Marketing footer**: wordmark, one-line positioning, then contact, source, licence and app links.

## Motion

- `landing-rise`: 700ms, 10px rise + fade, staggered 90/170/250ms for hero elements only.
- All animation is disabled by the global `prefers-reduced-motion` rule.
- No parallax, no scroll-jacking, no looping decoration.

## Accessibility

- Target WCAG 2.2 AA. Text and UI contrast checked in both themes.
- `:focus-visible` is a 3px accent outline with 2px offset.
- Search input has a visible label for assistive tech; form submits with Enter.
- Semantic landmarks (`header`, `nav`, `main`, `footer`), one `h1` per page, ordered headings.
- Decorative SVG is `aria-hidden`; links and buttons use real text.

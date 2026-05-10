# Brekora BMS — Design System

## Typography

| Role | Font | Weights | Usage |
|------|------|---------|-------|
| Display / Headlines | **Playfair Display** | 400, 500, 600, 700 (italic for emphasis) | Hero titles, page headers, public landing pages, marketing copy |
| UI / Body | **Manrope** | 400, 500, 600, 700 | Navigation, buttons, forms, tables, dashboards, all interface text |

### Type scale

| Token | Size | Weight | Line-height | Font |
|-------|------|--------|-------------|------|
| `display-xl` | 42px | 600 | 1.1 | Playfair Display |
| `display-lg` | 32px | 600 | 1.15 | Playfair Display |
| `heading-xl` | 24px | 700 | 1.3 | Manrope |
| `heading-lg` | 20px | 600 | 1.3 | Manrope |
| `heading-md` | 16px | 600 | 1.4 | Manrope |
| `body-lg` | 16px | 400 | 1.6 | Manrope |
| `body-md` | 15px | 400 | 1.6 | Manrope |
| `body-sm` | 14px | 400 | 1.5 | Manrope |
| `label` | 12px | 600 | 1.4 | Manrope — uppercase, letter-spacing 0.04em |
| `metric` | 28px | 700 | 1.2 | Manrope — `font-variant-numeric: tabular-nums` |

### Loading

Add to `index.html`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Manrope:wght@400;500;600;700&display=swap" rel="stylesheet">
```

Update `tailwind.config.js`:

```js
theme: {
  extend: {
    fontFamily: {
      display: ["'Playfair Display'", 'Georgia', 'serif'],
      body: ["'Manrope'", '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
    },
  },
}
```

---

## Color palette

### Brand (teal / ocean)

| Token | Hex | Usage |
|-------|-----|-------|
| `brand-50` | `#f0f9ff` | Lightest backgrounds, hover tints |
| `brand-100` | `#e0f2fe` | Subtle highlights, selection bg |
| `brand-200` | `#bae6fd` | Borders, disabled states |
| `brand-300` | `#7dd3fc` | Dark-mode primary text |
| `brand-400` | `#38bdf8` | Links, dark-mode accents |
| `brand-500` | `#0ea5e9` | Secondary buttons, badges |
| `brand-600` | `#026ba0` | **Primary buttons, active nav, CTAs** |
| `brand-700` | `#0369a1` | Hover states for primary |
| `brand-800` | `#075985` | Deep accents |
| `brand-900` | `#0c4a6e` | Darkest brand tone, headings on light bg |

### Grays

| Token | Hex | Usage |
|-------|-----|-------|
| `gray-50` | `#f9fafb` | Page backgrounds |
| `gray-100` | `#f3f4f6` | Card backgrounds, subtle stripes |
| `gray-200` | `#e5e7eb` | Borders, dividers |
| `gray-300` | `#d1d5db` | Disabled borders |
| `gray-400` | `#6b7280` | Muted text, placeholders — **WCAG AA safe** |
| `gray-500` | `#4b5563` | Secondary text |
| `gray-600` | `#374151` | Body text on light bg |
| `gray-700` | `#1f2937` | Strong text, labels |
| `gray-800` | `#111827` | Headings |
| `gray-900` | `#030712` | Deepest text |

### Semantic

| Token | Hex | Usage |
|-------|-----|-------|
| `success` | `#047857` | Confirmed bookings, positive trends |
| `warning` | `#b45309` | Pending actions, alerts |
| `error` | `#dc2626` | Errors, cancellations, overbookings |
| `info` | `#0369a1` | Tips, info banners |
| `secondary` | `#c27d3a` | Accent warmth — gold/amber highlights, ratings |
| `secondary-light` | `#d99a5e` | Hover on secondary accents |

---

## Spacing

Base unit: **4px**

Use Tailwind defaults: `1 = 4px`, `2 = 8px`, `4 = 16px`, `6 = 24px`, `8 = 32px`, `12 = 48px`, `16 = 64px`.

Key layout values:
- Sidebar width: `256px` (`w-64`)
- Max content width: `1280px` (`max-w-7xl`)
- Page padding: `16px` mobile → `24px` tablet → `32px` desktop

---

## Radius

| Token | Value | Usage |
|-------|-------|-------|
| `sm` | 4px | Inputs, small tags |
| `md` | 8px | Cards, panels, buttons |
| `lg` | 12px | Modals, large cards, popovers |
| `full` | 9999px | Pills, avatars, badges |

---

## Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `sm` | `0 1px 2px rgba(28,25,23,0.05)` | Subtle elevation, inputs |
| `md` | `0 4px 6px -1px rgba(28,25,23,0.07), 0 2px 4px -1px rgba(28,25,23,0.04)` | Cards, dropdowns |
| `lg` | `0 10px 15px -3px rgba(28,25,23,0.07), 0 4px 6px -2px rgba(28,25,23,0.03)` | Modals, toasts |

---

## Dark mode

Strategy: `class`-based toggling via Tailwind `darkMode: 'class'`.

When `<html class="dark">` is present:
- Background flips to `gray-900` / `gray-800`
- Text flips to `gray-100` / `gray-200`
- Brand shifts to lighter tones (`brand-300`/`brand-400`) for contrast
- Shadows deepen with higher opacity

---

## Component patterns

### Buttons

| Variant | Background | Text | Border | Hover |
|---------|------------|------|--------|-------|
| Primary | `brand-600` | white | none | `brand-700` |
| Secondary | white | `brand-600` | `gray-200` | `brand-50` |
| Ghost | transparent | `gray-600` | none | `gray-100` |
| Danger | `error` | white | none | darken 10% |

All buttons: `radius-md`, `font-weight-600`, `padding 10px 20px`.

### Cards

- Background: `surface` (white) or `gray-50`
- Border: `1px solid gray-200`
- Radius: `radius-lg`
- Shadow: `shadow-sm` or `shadow-md` when hovered/elevated
- Padding: `24px`

### Forms / Inputs

- Background: white
- Border: `1px solid gray-200`
- Radius: `radius-md`
- Focus ring: `2px brand-500` with `outline-none`
- Placeholder: `gray-400`

### Tables

- Header: `gray-50` background, `gray-600` text, `font-weight-600`
- Rows: alternate white / `gray-50`
- Border: `1px solid gray-200` between rows
- Cell padding: `12px 16px`

### Navigation

- Active item: `brand-600` background, white text, `shadow-md`
- Inactive item: `gray-600` text, hover `brand-50` + `brand-700` text
- Icon size: `20px`
- Item padding: `10px 12px`, radius `radius-md`

---

## Accessibility

- All gray text on white must be `gray-400` (#6b7280) or darker for WCAG AA (4.5:1).
- Exactly one `<h1>` per page.
- Heading levels must not skip (no `h1` → `h3` without `h2`).
- Landmark regions (`<main>`, `<aside>`, `<nav>`) must have `aria-label` when multiple exist.
- Focus indicators must be visible (`ring-2 ring-brand-500`).
- `font-variant-numeric: tabular-nums` on all currency, percentage, and count displays.

---

## Files to touch for a full rollout

1. `frontend/index.html` — add Google Fonts link
2. `frontend/tailwind.config.js` — add `fontFamily.display` and `fontFamily.body`
3. `frontend/src/index.css` — remove utility overrides if no longer needed; ensure `font-body` applied to `body`
4. `frontend/src/App.tsx` — confirm `font-body` on root
5. Any hard-coded `font-serif` / `font-sans` in components → swap to `font-display` / `font-body`

---

*Fonts chosen: Playfair Display for editorial elegance (luxury hospitality feel) + Manrope for clean, warm UI readability.*

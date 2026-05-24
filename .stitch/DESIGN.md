# AgriNet AI — Organic Tech Design System

## 1. Brand Identity

**Product:** AgriNet AI — Smart Farming Network for Indian Farmers  
**Tagline:** Where soil meets silicon  
**Aesthetic:** Organic Tech — the warmth of the earth fused with precision AI

---

## 2. Color Palette

### Primary Colors
- **Forest Green (Primary):** `#3D6B35` — Deep, rich forest green for primary actions
- **Olive Dark (Hero BG):** `#2D4229` — Dark olive green for hero panels and sidebar
- **Sidebar BG:** `#2A3D24` — Deep forest for sidebar background
- **Chartreuse (Accent):** `#D2F124` — Electric lime for CTAs, active states, highlights

### Background Colors
- **Sand (Page BG):** `#EDEBE0` — Warm sand/parchment for main background
- **Card BG Light:** `#FFFFFF` — Pure white for cards in light mode
- **Card BG Dark:** `#1C2416` — Deep forest card for dark mode

### Neutral Colors
- **Text Primary:** `#1A1D16` — Near black with green undertone
- **Text Secondary:** `#6B7260` — Warm olive gray for secondary text
- **Border Light:** `#D8D5C8` — Warm sand border
- **Border Dark:** `#3A4A32` — Dark forest border

### Semantic Colors
- **Success/Up:** `#3D6B35` — Forest green
- **Warning:** `#C47F17` — Amber
- **Error/Down:** `#C14646` — Brick red
- **Info:** `#2563EB` — Royal blue

---

## 3. Typography

### Font Families
- **Display Font:** `Plus Jakarta Sans` — geometric, premium, modern (weights: 500, 600, 700, 800)
- **Body Font:** `Plus Jakarta Sans` — consistent, clean (weights: 400, 500, 600)
- **Monospace:** `JetBrains Mono` — for blockchain hashes, code snippets

### Type Scale
- **Hero Headline:** 40px / 800 weight / -1px letter-spacing
- **Section Title:** 20px / 700 weight / -0.3px letter-spacing
- **Card Title:** 16px / 600 weight
- **Body:** 14px / 400 weight / 1.6 line-height
- **Label/Caption:** 12px / 500 weight / 0.5px letter-spacing
- **Metric Big:** 36px / 800 weight (for KPI cards)
- **Metric Small:** 24px / 700 weight

---

## 4. Shape & Spacing

### Border Radius
- **XL (Hero cards, main containers):** `28px`
- **LG (Standard cards):** `20px`
- **MD (Inputs, buttons, tags):** `12px`
- **SM (Badges, chips):** `8px`
- **Pill (Nav items, tags):** `100px`

### Spacing Scale
- `xs`: 4px
- `sm`: 8px
- `md`: 16px
- `lg`: 24px
- `xl`: 32px
- `2xl`: 48px

### Shadows
- **Elevation 1 (default):** `0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)`
- **Elevation 2 (hover):** `0 4px 16px rgba(45,66,41,0.12)`
- **Elevation 3 (modal):** `0 8px 32px rgba(45,66,41,0.18)`
- **Glow (accent):** `0 0 20px rgba(210,241,36,0.25)`

---

## 5. Component Patterns

### Sidebar Navigation
- Background: `#2A3D24` (deep forest)
- Width: 260px fixed
- Nav item default: white/cream text, transparent background
- Nav item hover: semi-transparent white bg `rgba(255,255,255,0.08)`, chartreuse left border
- Nav item active: chartreuse `#D2F124` background, `#1A1D16` text, bold
- Logo area: 64px height, brand green gradient icon
- Bottom section: user avatar, settings, language toggle

### Hero Banner
- Background: `#2D4229` (olive dark) with topographic SVG line pattern overlay
- Decorative floating leaf/grain elements (CSS animations)
- Two-column: left = AI insight text + chartreuse CTA; right = mini AI chat input
- Border radius: 28px

### KPI Cards
- White background, 20px radius
- Hover: `translateY(-4px)` + Elevation 2 shadow
- Icon: in colored pill (not square) — top-left placement
- Metric: 36px, 800 weight, with green color for positive values
- Trend badge: pill shape, green bg for up, red for down
- Subtle left border accent (4px, colored per metric type)

### Data Bars
- Height: 10px
- Background track: `#EDEBE0` (sand)
- Fill: gradient per value (green → yellow → red based on risk)
- Transition: 1s cubic-bezier ease

### Buttons
- **Primary:** Chartreuse `#D2F124` bg, `#1A1D16` text, 12px radius, 600 weight
- **Secondary:** Forest green `#3D6B35` bg, white text
- **Ghost:** Transparent bg, forest green border + text
- Hover: slight darken + `translateY(-1px)`

### Tags / Badges
- Pill shape (100px radius)
- Up: `rgba(61,107,53,0.12)` bg, `#3D6B35` text
- Down: `rgba(193,70,70,0.08)` bg, `#C14646` text
- Warn: `rgba(196,127,23,0.08)` bg, `#C47F17` text

### Cards
- White bg (light) / `#1C2416` (dark)
- 20px radius
- Elevation 1 shadow
- 24px padding
- On hover: Elevation 2

### Form Inputs
- `#EDEBE0` sand background
- `1.5px` border, `#D8D5C8` default
- `#3D6B35` focus border with subtle glow
- 12px radius
- 14px font size

### Chat Bubbles
- User bubble: white bg, `#D8D5C8` border, `border-bottom-left-radius: 4px`
- AI bubble: `rgba(61,107,53,0.08)` green-tinted bg, `border-bottom-right-radius: 4px`
- Both: 18px radius

---

## 6. Animation & Motion

### Micro-animations
- **Hover lift:** `transform: translateY(-4px)` on cards, 200ms ease
- **Sidebar active:** background color transition, 150ms
- **Bar fill:** width transition 1s cubic-bezier(0.23, 1, 0.32, 1)
- **Fade in sections:** `opacity: 0 → 1` + `translateY(12px → 0)`, 350ms

### Perpetual Animations
- **Hero leaves float:** `@keyframes float` — subtle vertical bob, 6s infinite ease-in-out
- **KPI pulse:** `@keyframes pulse` on status indicators — radial glow, 2s infinite
- **Shimmer loader:** `@keyframes shimmer` — left-to-right light sweep on loading states

---

## 7. Dark Mode

Dark mode uses forest-immersion palette:
- BG: `#0D1209` (near-black green)
- Card: `#1C2416` (deep forest)
- Border: `#3A4A32`
- Text: `#E8EDE0` (cream)
- Text secondary: `#8B9A7A`

---

## 8. Design System Notes for Stitch Generation

**Use these tokens in all Stitch generation prompts:**

- Warm sandy/parchment background with white content cards
- Deep forest-green sidebar navigation (fixed left, 260px)
- Chartreuse/lime-green accent color for all primary CTAs and active nav states
- Plus Jakarta Sans typography throughout
- High border radius (20-28px) on all cards and containers
- Organic warmth — earth tones, natural textures, topographic patterns
- Dark olive-green hero panels at the top of each major section
- Premium agricultural dashboard aesthetic
- All metric numbers large and bold (36px+)
- Pill-shaped navigation items in sidebar

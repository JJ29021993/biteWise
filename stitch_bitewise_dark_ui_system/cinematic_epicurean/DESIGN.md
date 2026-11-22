---
name: Cinematic Epicurean
colors:
  surface: '#121316'
  surface-dim: '#121316'
  surface-bright: '#38393c'
  surface-container-lowest: '#0d0e11'
  surface-container-low: '#1b1b1f'
  surface-container: '#1f1f23'
  surface-container-high: '#292a2d'
  surface-container-highest: '#343538'
  on-surface: '#e3e2e6'
  on-surface-variant: '#e4bebc'
  inverse-surface: '#e3e2e6'
  inverse-on-surface: '#303034'
  outline: '#ab8987'
  outline-variant: '#5b403f'
  surface-tint: '#ffb3b1'
  primary: '#ffb3b1'
  on-primary: '#680011'
  primary-container: '#ff535a'
  on-primary-container: '#5b000e'
  inverse-primary: '#bb162c'
  secondary: '#ffb3af'
  on-secondary: '#68000d'
  secondary-container: '#b1021e'
  on-secondary-container: '#ffbdb9'
  tertiary: '#4ae176'
  on-tertiary: '#003915'
  tertiary-container: '#00a74b'
  on-tertiary-container: '#003111'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdad8'
  primary-fixed-dim: '#ffb3b1'
  on-primary-fixed: '#410007'
  on-primary-fixed-variant: '#92001c'
  secondary-fixed: '#ffdad7'
  secondary-fixed-dim: '#ffb3af'
  on-secondary-fixed: '#410005'
  on-secondary-fixed-variant: '#930017'
  tertiary-fixed: '#6bff8f'
  tertiary-fixed-dim: '#4ae176'
  on-tertiary-fixed: '#002109'
  on-tertiary-fixed-variant: '#005321'
  background: '#121316'
  on-background: '#e3e2e6'
  surface-variant: '#343538'
typography:
  display-lg:
    fontFamily: Outfit
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.015em
  headline-xl:
    fontFamily: Outfit
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
    letterSpacing: -0.015em
  headline-xl-mobile:
    fontFamily: Outfit
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Outfit
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: 0em
  body-lg:
    fontFamily: Source Sans 3
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Source Sans 3
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Source Sans 3
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Source Sans 3
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Source Sans 3
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-xs:
    fontFamily: Source Sans 3
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.04em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.25rem
  gutter-sm: 0.75rem
  gutter-lg: 1.75rem
  margin: 1.5rem
  margin-sm: 1rem
  margin-lg: 3rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style
This design system establishes an atmospheric, high-contrast, late-night discovery environment tailored for food enthusiasts navigating Bangalore’s dense culinary scene. The experience evokes the energy of evening dining out: deep shadowy ambiences, warm spotlighting, and crisp, decisive typography that puts food imagery front and center.

The aesthetic fuses modern dark-mode utility with subtle culinary theatricality. It eschews generic purple tech glows and heavy frosted glass in favor of grounded, near-black canvas tones, razor-sharp 1px border lines, and disciplined ambient crimson glows (`#E23744` at low opacities). Surfaces feel physical, clean, and elevated—designed to make imagery of hot dosas, craft beers, and slow-cooked biryanis visually jump off the screen while keeping dense data (ratings, wait times, neighborhood tags) instantly legible.

## Colors

The color architecture is built for strict nocturnal comfort and visual hierarchy, anchored against a charcoal base with targeted chromatic signals for decision making:

- **Canvas & Surfaces:**
  - Base Canvas: `#0E0F12` (deep charcoal-black, non-pure black to prevent smearing and harsh contrast).
  - Elevated Surface Layer: `#171A1F` (restaurant cards, filter sidebars, floating modal trays).
  - High-Tier Hover/Active Surface: `#20242B`.
  - Structural Stroke / Divider: `#2A2F38` (structural 1px outlines ensuring card boundaries never dissolve into background).

- **Brand Crimson (Action & Identity):**
  - Primary Accent: `#E23744` (primary buttons, AI highlight badges, active tab markers).
  - Deep Press / Hover: `#CB202D`.
  - Ambient Glow Wash: `rgba(226, 55, 68, 0.08)` to `rgba(226, 55, 68, 0.15)` behind hero query bars and recommendation callouts.

- **Typography & Neutrals:**
  - Text Primary: `#F4F4F5` (crisp near-white; passes WCAG AAA on all surfaces).
  - Text Muted / Secondary: `#9AA0A6` (curated metadata: cuisines, distances, price bands, reviews count).
  - Text Disabled / Sub-border: `#4B5362`.

- **Semantic Performance Tiers (Rating Badges):**
  - Tier 1 (>= 4.0): `#22C55E` with deep green container `rgba(34, 197, 94, 0.14)`.
  - Tier 2 (3.0 – 3.9): `#EAB308` with amber container `rgba(234, 179, 8, 0.14)`.
  - Tier 3 (< 3.0): `#F97316` with burnt orange container `rgba(249, 115, 22, 0.14)`.

## Typography

The typographic hierarchy pairs **Outfit** for expressive identity headers with **Source Sans 3** for rapid scannability and content density:

- **Outfit** carries geometric energy, contemporary proportions, and generous counter-spaces, giving restaurant titles, curated collection tags, and AI persona queries immediate charisma. Letter-spacing is slightly tightened on sizes above 24px to preserve visual cohesion against dark backgrounds.
- **Source Sans 3** manages all technical and informational load: price ranges, open hours, Bangalore locality labels (e.g., Indiranagar, Koramangala), ingredients, and sentiment tags. It maintains open apertures and clear distinction between similar glyphs, guaranteeing effortless reading under reduced outdoor brightness or low-light indoor environments.

## Layout & Spacing

The layout is built around a rigorous 4px/8px modular rhythm designed to accommodate dense listings, map split-views, and conversational AI recommendation feeds.

- **Grid Strategy:**
  - **Desktop (>= 1200px):** 12-column fluid grid, 28px (`gutter-lg`) gutters, max-width `1360px` centered with variable margins. Split layout default: 7 columns feed, 5 columns contextual map or interactive tasting breakdown.
  - **Tablet (768px - 1199px):** 8-column layout, 20px (`gutter`) gutters, 24px outer margin.
  - **Mobile (< 768px):** Single-column stacked cards or dual-column quick-chips, 12px (`gutter-sm`) gutters, 16px (`margin-sm`) margins.
- **Vertical Scansion:** Restaurant listing card blocks rely on `space-md` (16px) internal padding, while macro sections (e.g., "Trending in HSR", "AI Match Score") use `space-xl` (40px) vertical clearances to maintain visual breathing room.

## Elevation & Depth

Visual hierarchy does not use diffuse white drop shadows or heavy blur overlays. Instead, depth is structured through tonal shifting, hairline borders, and localized ambient warm backlights:

- **Base Layer (0dp):** Deep `#0E0F12` canvas.
- **Layer 1 - Content Surface (1dp):** `#171A1F` background bounded by a crisp `1px solid #2A2F38` stroke. This defines resting restaurant cards, filter ribbons, and sidebar trays.
- **Layer 2 - Lifted / Interactive (2dp):** On hover or selection, the card elevates via a `#20242B` surface tint, shifts its border to `#3B424F`, and casts a concentrated shadow: `0 8px 24px -6px rgba(0, 0, 0, 0.6)`.
- **Layer 3 - Floating Modals & Overlays (3dp):** Bottom sheets, AI conversational trays, and sticky action docks utilize `#1B1E24` framed with `1px solid #363C47`, supported by an expansive ambient occlusion shadow: `0 20px 48px -8px rgba(0, 0, 0, 0.85)`.
- **Atmospheric Accent Glow:** Reserved strictly for primary action clusters and high-confidence AI match badges. Constructed using an underlaid radial gradient: `radial-gradient(circle at 50% 0%, rgba(226, 55, 68, 0.15) 0%, transparent 70%)`.

## Shapes

This design system uses balanced curvature (`roundedness: 2`), centering around 12px to 16px corner geometry to yield a polished, modern, tactile consumer experience:

- **Standard Cards & Surfaces (`rounded-lg` / 16px):** Primary listing containers, AI answer boxes, and photographic hero frames use 16px outer corners. Nested visual media maintains 12px corners to follow organic concentric geometry.
- **Input Fields, Badges & Filter Controls (8px to 12px):** Search inputs, numeric score tiles, and date/time steppers use 8px–12px for compact ergonomics.
- **Pill Form Factor (Full Radius / 9999px):** Applied strictly to atomic UI components: food category tags (e.g., "South Indian", "Microbrewery"), sentiment pills, dynamic filter chips, and primary rating indicators.

## Components

### Buttons
- **Primary:** Solid `#E23744` background, `#F4F4F5` bold typography (`label-md`), full or 12px roundedness. Hover transitions to `#CB202D` with subtle glow (`0 4px 16px rgba(226, 55, 68, 0.35)`). Active state applies a scale transformation to 0.98.
- **Secondary / Ghost:** Transparent surface with 1px border in `#2A2F38`, hover fill `#171A1F` with border brightening to `#3B424F`. Text is `#F4F4F5`.
- **Icon Action Buttons:** 40x40px or 36x36px squares, 10px corner radius, `#171A1F` surface, 1px `#2A2F38` stroke. Used for bookmarks, share, and filter triggers.

### Chips & Filter Pills
- **Unselected:** Background `#171A1F`, border `1px solid #2A2F38`, text `#9AA0A6`.
- **Selected / Active:** Background `rgba(226, 55, 68, 0.15)`, border `1px solid #E23744`, text `#F4F4F5`. Includes optional clear `×` icon.
- **Metadata Micro-Chips:** Compact, non-clickable pills (`label-xs`) indicating dietary suitability (Veg, Non-Veg, Vegan) using industry-standard green dot / red triangle icons within translucent dark backdrops.

### Rating Badges
- **Compact Block / Pill:** Inline badge displaying score + star icon.
  - **4.0+:** Solid `#22C55E` text with `rgba(34, 197, 94, 0.16)` surface and subtle `rgba(34, 197, 94, 0.3)` border.
  - **3.0–3.9:** Solid `#EAB308` text with `rgba(234, 179, 8, 0.16)` surface and border.
  - **< 3.0:** Solid `#F97316` text with `rgba(249, 115, 22, 0.16)` surface and border.

### Restaurant Listing Cards
- Built using `#171A1F` surface with 16px corners, `1px solid #2A2F38` stroke, and overflow hidden.
- Top half features a 16:9 photographic crop with a bottom-to-top gradient darkening (`rgba(14, 15, 18, 0.8)` to `transparent`) to protect superimposed badges (e.g., "Trending", "AI Match 94%").
- Content panel hosts the restaurant title in `headline-sm` (`Outfit`), neighborhood and distance in `#9AA0A6`, followed by a divider stroke and highlighted crowd favorites.

### Input Fields & Search Bars
- **Omni-Search Bar:** 52px height, `#171A1F` surface, `1px solid #2A2F38`, 12px radius. Left icon: dynamic crimson spark for AI prompt status; right action: location selector chip ("Koramangala 5th Block"). Focus state swaps border to `#E23744` and casts a tight halo ring `0 0 0 3px rgba(226, 55, 68, 0.2)`.

### Checkboxes & Radio Buttons
- 20x20px dimension, 6px radius (checkbox) or circular (radio). Unchecked state: `#171A1F` background, `1.5px solid #2A2F38`. Checked state: solid `#E23744` with `#F4F4F5` SVG checkmark or center pip.

### AI Insight Notices (Transparent Meta Callouts)
- Lightweight recommendation explanations (e.g., *"Why BiteWise picked this: Matches your craving for authentic ghee roast with low wait times"*).
- Styled with `rgba(226, 55, 68, 0.06)` background, left-bordered with a 3px accent stroke in `#E23744`, 8px right radius, and text in `#F4F4F5` (`body-sm`).
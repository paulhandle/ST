---
name: Kinetic Precision
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#3a3939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#e6beb2'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#ad897e'
  outline-variant: '#5c4037'
  surface-tint: '#ffb59e'
  primary: '#ffb59e'
  on-primary: '#5e1700'
  primary-container: '#ff571a'
  on-primary-container: '#521300'
  inverse-primary: '#ae3200'
  secondary: '#bdf4ff'
  on-secondary: '#00363d'
  secondary-container: '#00e3fd'
  on-secondary-container: '#00616d'
  tertiary: '#a5c8ff'
  on-tertiary: '#00315e'
  tertiary-container: '#2492ff'
  on-tertiary-container: '#002a53'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdbd0'
  primary-fixed-dim: '#ffb59e'
  on-primary-fixed: '#3a0b00'
  on-primary-fixed-variant: '#852400'
  secondary-fixed: '#9cf0ff'
  secondary-fixed-dim: '#00daf3'
  on-secondary-fixed: '#001f24'
  on-secondary-fixed-variant: '#004f58'
  tertiary-fixed: '#d4e3ff'
  tertiary-fixed-dim: '#a5c8ff'
  on-tertiary-fixed: '#001c3a'
  on-tertiary-fixed-variant: '#004785'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display-xl:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '800'
    lineHeight: '1.1'
    letterSpacing: -0.04em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.03em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  body-base:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: -0.01em
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: '0'
  data-label:
    fontFamily: Space Grotesk
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: 0.05em
  metric-value:
    fontFamily: Space Grotesk
    fontSize: 20px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: -0.02em
spacing:
  unit: 4px
  gutter: 16px
  margin: 24px
  panel-padding: 20px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

This design system centers on a **Technical Performance** aesthetic, merging the rigorous clarity of medical-grade instrumentation with the aggressive energy of professional athletics. The brand personality is authoritative and evidence-based, designed to instill confidence in high-stakes training environments.

The visual style utilizes a **Modern-Industrial** approach: a focus on information density, structural integrity, and zero-redundancy. Every element serves a functional purpose, utilizing thin structural lines and high-contrast typography to organize complex physiological data into actionable insights. The emotional response is one of focus, discipline, and elite-level professionalism.

## Colors

The palette is anchored in a "Deep Charcoal" environment to reduce eye strain during data-heavy analysis sessions and to provide a premium, cockpit-like atmosphere.

- **Primary (Safety Orange):** A high-visibility #FF4D00 used exclusively for primary actions, critical alerts, and peak performance metrics.
- **Secondary (Electric Blue):** A precise #00E5FF utilized for secondary data streams, recovery metrics, and interactive states.
- **Neutrals:** A monochromatic range from absolute black to cool-toned greys, providing the structural framework for panels and borders.
- **Logic:** Colors must never be used as decorative gradients. Solid fills emphasize the binary, evidence-based nature of the data.

## Typography

The typography system prioritizes legibility under duress. **Inter** is used for all functional UI and body text, utilizing tight tracking to achieve a compact, technical feel. **Space Grotesk** is introduced for data labels and numeric metrics to provide a geometric, scientific character that distinguishes raw data from instructional text.

Large headlines should always use "Extra Bold" weights with negative letter spacing to evoke a sense of strength and athletic power. Data labels are consistently set in uppercase with slight tracking increases to ensure clarity at small scales.

## Layout & Spacing

This design system employs a **Fixed Grid** logic for dashboard environments and a **Modular Panel** system for mobile applications. The rhythm is based on a strict 4px baseline grid to ensure mathematical alignment across dense data visualizations.

Layouts should favor high information density. Content is organized into discrete panels that use consistent internal padding. Relationships between data points are established through proximity and thin vertical dividers rather than excessive whitespace.

## Elevation & Depth

Depth is achieved through **Tonal Layering** rather than traditional drop shadows. Surfaces are stacked using varying shades of charcoal to indicate hierarchy.

- **Level 0 (Base):** The primary background (#0A0A0A).
- **Level 1 (Panels):** Raised surfaces (#141414) with a 1px solid border (#262626).
- **Level 2 (Popovers/Modals):** Elevated surfaces with a subtle, 10% opacity black shadow and a slightly brighter border (#3F3F46) to separate from the background.

Avoid all "soft" or "blurred" aesthetics. Intersections should feel crisp and engineered.

## Shapes

The shape language is **Strictly Geometric**. Sharp corners (0px radius) are used for all major structural panels and containers to reinforce the "protocol" and "scientific" narrative.

Subtle 2px radii may be applied to internal interactive elements like input fields or small buttons to provide a micro-hint of "touchability," but the overall silhouette of the interface must remain rectilinear and rigid.

## Components

**Buttons:**
- **Primary:** Solid Safety Orange with black text. Sharp corners. No gradients.
- **Ghost:** 1px white or blue border with no fill. State changes indicated by filling the border color.

**Data Panels:**
- Must include a header row with a `data-label` styled title and a 1px divider.
- Values within panels should use the `metric-value` style.

**Input Fields:**
- Dark backgrounds (#050505) with 1px borders (#262626).
- Active state: Border changes to Electric Blue with no glow/blur.

**Timeline/Calendar:**
- Use a monochromatic grid with "active" days highlighted by a 2px bottom bar in the Primary color.
- Avoid rounded bubbles; use blocks to represent duration and intensity.

**Training Metrics:**
- Represent intensity through bar charts or stepped line graphs. Avoid curved interpolation on graphs; use straight, point-to-point lines to emphasize raw, un-smoothed data.

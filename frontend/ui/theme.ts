/**
 * PRAHARI Design System & Theme Tokens
 * Aesthetic: Warm Cream + Deep Defence Olive + Editorial Healthcare
 */

export const PRAHARI_COLORS = {
  // Backgrounds & Surfaces
  bg: "#FBFBF8",
  bgSecondary: "#F3F2EB",
  surface: "#FFFFFF",
  card: "#FFFFFF",
  cardHover: "#F6F7F3",

  // Defence Olive & Forest Green Tokens
  olive: "#2C5127",
  oliveDark: "#1A3217",
  oliveLight: "#46723F",
  oliveSoft: "#EAF1E9",
  oliveBorder: "#CFDDCE",

  // Backward-compatible alias
  blue: "#2C5127",
  blueLight: "#46723F",
  blueSoft: "#EAF1E9",
  blueBorder: "#CFDDCE",

  // Navigation & Headers (Deep Defence Olive)
  navy: "#1A3217",
  navyMid: "#244320",
  navySoft: "#2C5127",

  // Identity / Brass Gold Accents
  gold: "#B8860B",
  goldLight: "#D4AF37",
  goldSoft: "rgba(184, 134, 11, 0.12)",
  goldBorder: "rgba(184, 134, 11, 0.3)",

  // Welfare Risk Status Tiers (Strict 3 Locked Bands + Pending)
  low: {
    label: "Normal / Stable",
    text: "#15803D",
    bg: "#ECFDF5",
    border: "#A7F3D0",
    dot: "#22C55E",
  },
  medium: {
    label: "Elevated / Watch",
    text: "#B45309",
    bg: "#FFFBEB",
    border: "#FDE68A",
    dot: "#F59E0B",
  },
  high: {
    label: "Critical / Attention",
    text: "#B91C1C",
    bg: "#FEF2F2",
    border: "#FECACA",
    dot: "#EF4444",
  },
  neutral: {
    label: "Assessment Pending",
    text: "#4B5563",
    bg: "#F3F4F6",
    border: "#E5E7EB",
    dot: "#9CA3AF",
  },

  // Typography Palette (Graphite with Deep Olive Undertones)
  textPrimary: "#182417",
  textSecondary: "#3B4B3A",
  textMuted: "#677766",
  textInverse: "#FFFFFF",

  // Structural Borders & Dividers
  border: "#CFDDCE",
  borderLight: "#E4ECE3",
  borderFocus: "#2C5127",
} as const;

export const PRAHARI_SHADOWS = {
  sm: "0 1px 2px 0 rgba(24, 36, 23, 0.04)",
  card: "0 2px 8px -1px rgba(24, 36, 23, 0.05), 0 1px 3px 0 rgba(24, 36, 23, 0.03)",
  cardHover: "0 8px 24px -4px rgba(24, 36, 23, 0.08), 0 3px 8px -2px rgba(24, 36, 23, 0.04)",
  modal: "0 24px 64px -12px rgba(16, 29, 16, 0.22)",
  header: "0 2px 10px rgba(26, 50, 23, 0.15)",
} as const;

export const PRAHARI_RADII = {
  sm: "6px",
  md: "8px",
  lg: "12px",
  xl: "16px",
  "2xl": "20px",
  full: "9999px",
} as const;

export const PRAHARI_THEME = {
  colors: PRAHARI_COLORS,
  shadows: PRAHARI_SHADOWS,
  radii: PRAHARI_RADII,
} as const;

export default PRAHARI_THEME;

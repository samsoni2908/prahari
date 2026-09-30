/**
 * PRAHARI Design System & Theme Tokens
 * Clean Defence + Modern Enterprise: White + Olive Green Theme
 */

export const PRAHARI_COLORS = {
  // Backgrounds & Surfaces
  bg: "#F8F9FA",
  surface: "#FFFFFF",
  card: "#FFFFFF",
  cardHover: "#F5F8F4",

  // Defence Olive Green Theme Tokens
  olive: "#385E31",
  oliveDark: "#243D20",
  oliveLight: "#4D7A45",
  oliveSoft: "#EFF5EE",
  oliveBorder: "#CDE0CB",

  // Backward-compatible alias
  blue: "#385E31",
  blueLight: "#4D7A45",
  blueSoft: "#EFF5EE",
  blueBorder: "#CDE0CB",

  // Navigation & Headers (Deep Defence Olive Gradient)
  navy: "#243D20",
  navyMid: "#2E4F28",
  navySoft: "#385E31",

  // Identity / Prahari Gold Accents
  gold: "#D98E04",
  goldLight: "#F59E0B",
  goldSoft: "rgba(217, 142, 4, 0.16)",
  goldBorder: "rgba(217, 142, 4, 0.35)",

  // Welfare Risk Status Tiers (Preserved Semantics)
  low: {
    label: "Stable",
    text: "#2E7D32",
    bg: "#E8F5E9",
    border: "#A5D6A7",
    dot: "#4CAF50",
  },
  medium: {
    label: "Watch",
    text: "#E65100",
    bg: "#FFF3E0",
    border: "#FFCC80",
    dot: "#FF9800",
  },
  high: {
    label: "Attention",
    text: "#C62828",
    bg: "#FFEBEE",
    border: "#EF9A9A",
    dot: "#F44336",
  },
  neutral: {
    label: "Assessment Pending",
    text: "#728070",
    bg: "#F5F8F4",
    border: "#E1E8DF",
    dot: "#9EB09C",
  },

  // Typography Palette (Charcoal with Olive Undertone)
  textPrimary: "#1C281A",
  textSecondary: "#465444",
  textMuted: "#728070",
  textInverse: "#FFFFFF",

  // Structural Borders & Dividers
  border: "#E1E8DF",
  borderLight: "#F0F4EF",
  borderFocus: "#385E31",
} as const;

export const PRAHARI_SHADOWS = {
  sm: "0 1px 2px 0 rgba(28, 40, 26, 0.04)",
  card: "0 1px 3px 0 rgba(28, 40, 26, 0.05), 0 1px 2px 0 rgba(28, 40, 26, 0.03)",
  cardHover: "0 4px 14px 0 rgba(28, 40, 26, 0.08)",
  modal: "0 20px 60px rgba(28, 40, 26, 0.18)",
  header: "0 2px 8px rgba(36, 61, 32, 0.20)",
} as const;

export const PRAHARI_RADII = {
  sm: "6px",
  md: "8px",
  lg: "12px",
  xl: "16px",
  full: "9999px",
} as const;

export const PRAHARI_THEME = {
  colors: PRAHARI_COLORS,
  shadows: PRAHARI_SHADOWS,
  radii: PRAHARI_RADII,
} as const;

export default PRAHARI_THEME;

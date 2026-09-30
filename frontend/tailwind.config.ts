import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./ui/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        prahari: {
          // Backgrounds (Clean White + Off-white)
          bg: "#F8F9FA",
          surface: "#FFFFFF",
          card: "#FFFFFF",
          cardHover: "#F5F8F4",

          // Defence Olive Green Theme
          olive: "#385E31",
          oliveDark: "#243D20",
          oliveLight: "#4D7A45",
          oliveSoft: "#EFF5EE",
          oliveBorder: "#CDE0CB",

          // Navigation & Headers (Deep Military Olive)
          navy: "#243D20",
          navyMid: "#2E4F28",
          navySoft: "#385E31",

          // Primary accent (mapped to Olive for seamless compatibility)
          blue: "#385E31",
          blueLight: "#4D7A45",
          blueSoft: "#EFF5EE",

          // Typography (Charcoal with Olive undertone)
          textPrimary: "#1C281A",
          textSecondary: "#465444",
          textMuted: "#728070",

          // Structural Borders
          border: "#E1E8DF",
          borderDark: "#C9D4C7",

          // Welfare Risk Status Tiers (Preserved Semantics)
          low: "#2E7D32",       // LOW risk (0-39) — stable
          lowBg: "#E8F5E9",
          lowBorder: "#A5D6A7",
          med: "#F57C00",       // MEDIUM risk (40-69) — watch
          medBg: "#FFF3E0",
          medBorder: "#FFCC80",
          high: "#C62828",      // HIGH risk (70-100) — attention
          highBg: "#FFEBEE",
          highBorder: "#EF9A9A",

          // Wellbeing subtle accent
          violet: "#5C4A72",
          violetBg: "#F4EFF8",
          violetBorder: "#D4C7DF",

          // Gold for PRAHARI identity / badges
          gold: "#D98E04",
          goldBg: "#FEF7E8",
        },
        swasti: {
          bg: "#F8F9FA",
          surface: "#FFFFFF",
          card: "#FFFFFF",
          cardHover: "#F5F8F4",
          olive: "#385E31",
          oliveDark: "#243D20",
          oliveLight: "#4D7A45",
          oliveSoft: "#EFF5EE",
          oliveBorder: "#CDE0CB",
          navy: "#243D20",
          navyMid: "#2E4F28",
          navySoft: "#385E31",
          blue: "#385E31",
          blueLight: "#4D7A45",
          blueSoft: "#EFF5EE",
          textPrimary: "#1C281A",
          textSecondary: "#465444",
          textMuted: "#728070",
          border: "#E1E8DF",
          borderDark: "#C9D4C7",
          low: "#2E7D32",
          lowBg: "#E8F5E9",
          lowBorder: "#A5D6A7",
          med: "#F57C00",
          medBg: "#FFF3E0",
          medBorder: "#FFCC80",
          high: "#C62828",
          highBg: "#FFEBEE",
          highBorder: "#EF9A9A",
          violet: "#5C4A72",
          violetBg: "#F4EFF8",
          violetBorder: "#D4C7DF",
          gold: "#D98E04",
          goldBg: "#FEF7E8",
        }
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "Courier New", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 3px 0 rgba(28, 40, 26, 0.05), 0 1px 2px 0 rgba(28, 40, 26, 0.03)",
        cardHover: "0 4px 14px 0 rgba(28, 40, 26, 0.08)",
        nav: "0 2px 8px 0 rgba(36, 61, 32, 0.20)",
        modal: "0 20px 60px 0 rgba(28, 40, 26, 0.18)",
      },
      borderRadius: {
        card: "12px",
      }
    },
  },
  plugins: [],
};

export default config;

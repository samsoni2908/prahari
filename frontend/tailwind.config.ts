import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
    "./ui/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: "var(--background)",
          secondary: "var(--background-secondary)",
          cream: "#FAF9F5",
        },
        surface: {
          DEFAULT: "var(--surface)",
          raised: "var(--surface-raised)",
          hover: "var(--surface-hover)",
        },
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
          disabled: "var(--text-disabled)",
        },
        primary: {
          DEFAULT: "var(--primary)",
          hover: "var(--primary-hover)",
          muted: "var(--primary-muted)",
        },
        border: {
          subtle: "var(--border-subtle)",
          DEFAULT: "var(--border-default)",
          strong: "var(--border-strong)",
          focus: "var(--border-focus)",
        },
        state: {
          normal: "var(--state-normal)",
          "normal-bg": "var(--state-normal-bg)",
          elevated: "var(--state-elevated)",
          "elevated-bg": "var(--state-elevated-bg)",
          critical: "var(--state-critical)",
          "critical-bg": "var(--state-critical-bg)",
          info: "var(--state-info)",
          "info-bg": "var(--state-info-bg)",
          neutral: "var(--state-neutral)",
          "neutral-bg": "var(--state-neutral-bg)",
        },
        // Dedicated PRAHARI Defence Palette
        olive: {
          50: "#f4f7f3",
          100: "#e5ede3",
          200: "#cbddc7",
          300: "#a6c3a0",
          400: "#7aa373",
          500: "#578450",
          600: "#436a3d",
          700: "#365332",
          800: "#2d442a",
          900: "#243722",
          950: "#142013",
        },
        forest: {
          900: "#1A2E1A",
          950: "#101D10",
        },
        cream: {
          50: "#FDFCF9",
          100: "#FAF9F5",
          200: "#F4F1EA",
          300: "#EBE6DC",
        },
        sand: {
          50: "#FBF9F4",
          100: "#F7F3E9",
          200: "#EFE6D5",
          300: "#DFD2B8",
        },
      },
      fontFamily: {
        serif: ["'Playfair Display'", "Georgia", "Cambria", "serif"],
        display: ["'Playfair Display'", "Georgia", "serif"],
        sans: ["'Inter'", "system-ui", "-apple-system", "sans-serif"],
      },
      boxShadow: {
        editorial: "0 2px 10px rgba(20, 32, 19, 0.05), 0 1px 3px rgba(20, 32, 19, 0.03)",
        card: "0 4px 20px -2px rgba(20, 32, 19, 0.06), 0 2px 6px -1px rgba(20, 32, 19, 0.03)",
        cardHover: "0 10px 30px -4px rgba(20, 32, 19, 0.1), 0 4px 10px -2px rgba(20, 32, 19, 0.04)",
        dropdown: "0 12px 32px -4px rgba(20, 32, 19, 0.15), 0 4px 12px -2px rgba(20, 32, 19, 0.06)",
        modal: "0 24px 64px -12px rgba(16, 29, 16, 0.25)",
      },
      borderRadius: {
        sm: "6px",
        md: "8px",
        lg: "12px",
        xl: "16px",
        "2xl": "20px",
        "3xl": "24px",
      },
    },
  },
  plugins: [],
};

export default config;

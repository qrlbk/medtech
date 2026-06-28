import type { Config } from "tailwindcss";

/**
 * Tokens derived from design.json — "MedServicePrice Design DNA".
 * Accent teal is used sparingly (CTA, links, active states, key data);
 * navy is the trust color for large blocks and primary buttons.
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Teal accent
        brand: {
          50: "#E8FAFC",
          100: "#CDF1F5",
          200: "#A6E6ED",
          300: "#6FD6E1",
          400: "#42D0D4",
          500: "#1FAFC1",
          600: "#1998AB",
          700: "#0F6F8A",
        },
        // Navy / trust
        navy: {
          DEFAULT: "#16365F",
          600: "#1D3E6E",
          700: "#234A7E",
          800: "#16365F",
        },
        page: "#F4F7FB",
        surface: "#FFFFFF",
        subtle: "#EEF3F8",
        ink: {
          DEFAULT: "#20262E",
          secondary: "#5F6975",
          muted: "#8893A2",
        },
        line: {
          DEFAULT: "#E5EBF2",
          light: "#EEF2F6",
        },
        success: "#32C65C",
        warning: "#F5B93A",
        danger: "#E55353",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
        display: ["var(--font-manrope)", "Manrope", "Inter", "sans-serif"],
      },
      borderRadius: {
        lg: "12px",
        xl: "16px",
        "2xl": "18px",
        "3xl": "24px",
      },
      boxShadow: {
        soft: "0 4px 12px rgba(31,41,55,0.06)",
        card: "0 12px 36px rgba(25,42,70,0.08)",
        "card-hover": "0 18px 48px rgba(25,42,70,0.12)",
        cta: "0 10px 24px rgba(22,54,95,0.18)",
        focus: "0 0 0 4px rgba(31,175,193,0.15)",
      },
      letterSpacing: {
        tightish: "-0.01em",
        heading: "-0.02em",
      },
      maxWidth: {
        content: "1200px",
      },
      transitionTimingFunction: {
        smooth: "cubic-bezier(0.16, 1, 0.3, 1)",
      },
      backgroundImage: {
        "hero-teal": "linear-gradient(135deg, #27B8C7 0%, #42D0D4 100%)",
        "header-navy": "linear-gradient(90deg, #16365F 0%, #234A7E 100%)",
      },
    },
  },
  plugins: [],
};

export default config;

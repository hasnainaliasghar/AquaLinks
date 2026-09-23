import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

// Keep slash-opacity utilities working with design-token colors.
// Example: `bg-risk-medium/30` -> `oklch(from var(--risk-medium) l c h / 0.3)`
const tokenColor = (cssVar: string) => `oklch(from ${cssVar} l c h / <alpha-value>)`;

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx,mdx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./content/**/*.{md,mdx}",
  ],
  theme: {
    container: {
      center: true,
      padding: { DEFAULT: "1.25rem", md: "2rem" },
      screens: { "2xl": "1280px" },
    },
    extend: {
      colors: {
        ink: tokenColor("var(--ink)"),
        paper: tokenColor("var(--paper)"),
        border: tokenColor("var(--border)"),
        input: tokenColor("var(--input)"),
        ring: tokenColor("var(--ring)"),
        background: tokenColor("var(--background)"),
        foreground: tokenColor("var(--foreground)"),
        muted: {
          DEFAULT: tokenColor("var(--muted)"),
          foreground: tokenColor("var(--muted-foreground)"),
        },
        subtle: {
          DEFAULT: tokenColor("var(--subtle)"),
          foreground: tokenColor("var(--subtle-foreground)"),
        },
        card: {
          DEFAULT: tokenColor("var(--card)"),
          foreground: tokenColor("var(--card-foreground)"),
        },
        popover: {
          DEFAULT: tokenColor("var(--popover)"),
          foreground: tokenColor("var(--popover-foreground)"),
        },
        primary: {
          DEFAULT: tokenColor("var(--primary)"),
          foreground: tokenColor("var(--primary-foreground)"),
        },
        secondary: {
          DEFAULT: tokenColor("var(--secondary)"),
          foreground: tokenColor("var(--secondary-foreground)"),
        },
        accent: {
          DEFAULT: tokenColor("var(--accent)"),
          foreground: tokenColor("var(--accent-foreground)"),
        },
        destructive: {
          DEFAULT: tokenColor("var(--destructive)"),
          foreground: tokenColor("var(--destructive-foreground)"),
        },
        aqua: {
          50: tokenColor("var(--aqua-50)"),
          100: tokenColor("var(--aqua-100)"),
          200: tokenColor("var(--aqua-200)"),
          300: tokenColor("var(--aqua-300)"),
          400: tokenColor("var(--aqua-400)"),
          500: tokenColor("var(--aqua-500)"),
          600: tokenColor("var(--aqua-600)"),
          700: tokenColor("var(--aqua-700)"),
          800: tokenColor("var(--aqua-800)"),
          900: tokenColor("var(--aqua-900)"),
          950: tokenColor("var(--aqua-950)"),
        },
        risk: {
          low: tokenColor("var(--risk-low)"),
          "low-fg": tokenColor("var(--risk-low-fg)"),
          medium: tokenColor("var(--risk-medium)"),
          "medium-fg": tokenColor("var(--risk-medium-fg)"),
          high: tokenColor("var(--risk-high)"),
          "high-fg": tokenColor("var(--risk-high-fg)"),
        },
        surface: {
          0: tokenColor("var(--surface-0)"),
          1: tokenColor("var(--surface-1)"),
          2: tokenColor("var(--surface-2)"),
          3: tokenColor("var(--surface-3)"),
        },
      },
      borderRadius: {
        xs: "6px",
        sm: "10px",
        md: "14px",
        lg: "18px",
        xl: "22px",
        "2xl": "28px",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular"],
        display: ["var(--font-display)", "ui-serif", "Georgia"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem", letterSpacing: "0.01em" }],
        xs: ["0.75rem", { lineHeight: "1.1rem", letterSpacing: "0.01em" }],
        sm: ["0.8125rem", { lineHeight: "1.2rem" }],
        base: ["0.9375rem", { lineHeight: "1.55rem" }],
        lg: ["1.0625rem", { lineHeight: "1.65rem" }],
        xl: ["1.25rem", { lineHeight: "1.75rem", letterSpacing: "-0.005em" }],
        "2xl": ["1.5rem", { lineHeight: "2rem", letterSpacing: "-0.01em" }],
        "3xl": ["2rem", { lineHeight: "2.4rem", letterSpacing: "-0.015em" }],
        "4xl": ["3rem", { lineHeight: "3.3rem", letterSpacing: "-0.02em" }],
        "5xl": ["4rem", { lineHeight: "4.2rem", letterSpacing: "-0.025em" }],
        "6xl": ["5rem", { lineHeight: "5.2rem", letterSpacing: "-0.03em" }],
      },
      boxShadow: {
        "elev-1":
          "0 1px 2px 0 oklch(0 0 0 / 0.04), 0 1px 1px -0.5px oklch(0 0 0 / 0.06)",
        "elev-2":
          "0 4px 12px -2px oklch(0 0 0 / 0.08), 0 2px 4px -1px oklch(0 0 0 / 0.04)",
        "elev-3":
          "0 12px 28px -8px oklch(0 0 0 / 0.16), 0 6px 12px -4px oklch(0 0 0 / 0.08)",
        "elev-4":
          "0 24px 56px -12px oklch(0 0 0 / 0.22), 0 12px 24px -8px oklch(0 0 0 / 0.12)",
        focus: "0 0 0 4px var(--ring)",
      },
      transitionTimingFunction: {
        brand: "cubic-bezier(0.22, 1, 0.36, 1)",
        "in-out-quart": "cubic-bezier(0.76, 0, 0.24, 1)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "ring-pulse": {
          "0%, 100%": { transform: "scale(1)", opacity: "1" },
          "50%": { transform: "scale(1.06)", opacity: "0.7" },
        },
        "marquee-x": {
          from: { transform: "translateX(0)" },
          to: { transform: "translateX(-50%)" },
        },
      },
      animation: {
        "fade-in": "fade-in 320ms cubic-bezier(0.22, 1, 0.36, 1) both",
        shimmer: "shimmer 1.6s linear infinite",
        "ring-pulse": "ring-pulse 1.6s ease-in-out infinite",
        marquee: "marquee-x 32s linear infinite",
      },
      backgroundImage: {
        "grid-fade":
          "radial-gradient(circle at 50% 0%, transparent 0%, var(--background) 70%), linear-gradient(to right, var(--border) 1px, transparent 1px), linear-gradient(to bottom, var(--border) 1px, transparent 1px)",
      },
    },
  },
  plugins: [animate],
};

export default config;

import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#0E0F12",
        surface: {
          DEFAULT: "#171A1F",
          2: "#1F1F23",
          3: "#20242B",
          high: "#292A2D",
          lowest: "#0D0E11",
        },
        stroke: {
          DEFAULT: "#2A2F38",
          hot: "#3B424F",
        },
        crimson: {
          DEFAULT: "#E23744",
          deep: "#CB202D",
          bright: "#FF535A",
          soft: "#FFB3B1",
        },
        ink: "#F4F4F5",
        muted: "#9AA0A6",
        tertiary: "#4AE176",
        rating: {
          high: "#22C55E",
          mid: "#EAB308",
          low: "#F97316",
        },
      },
      fontFamily: {
        display: ["var(--font-outfit)", "system-ui", "sans-serif"],
        body: ["var(--font-source-sans)", "system-ui", "sans-serif"],
      },
      maxWidth: {
        shell: "1180px",
      },
      boxShadow: {
        card: "0 12px 36px rgba(0,0,0,0.35)",
        glow: "0 8px 22px rgba(226,55,68,0.35)",
      },
      keyframes: {
        pulseDot: {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.45", transform: "scale(0.85)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        pulseDot: "pulseDot 1.4s ease-in-out infinite",
        shimmer: "shimmer 1.4s linear infinite",
        fadeUp: "fadeUp 0.45s ease-out both",
      },
    },
  },
  plugins: [],
} satisfies Config;

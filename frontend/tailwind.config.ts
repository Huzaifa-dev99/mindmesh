import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        app: "#0f1115",
        foreground: "#f3f4f6",
        soft: "rgba(243,244,246,0.74)",
        muted: "rgba(243,244,246,0.46)",
        accent: "#9ae6b4",
        border: "rgba(255,255,255,0.09)",
        ink: {
          950: "#07080d",
          900: "#0d111a",
          800: "#151b29",
          700: "#20283a"
        },
        mint: "#48d7a6",
        coral: "#ff7a66",
        gold: "#f6c85f"
      },
      boxShadow: {
        panel: "0 18px 60px rgba(7, 8, 13, 0.28)",
        glow: "0 0 0 1px rgba(255,255,255,0.08), 0 20px 80px rgba(72,215,166,0.13)"
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
} satisfies Config;

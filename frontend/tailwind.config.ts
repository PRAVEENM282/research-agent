import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        mineral: "var(--mineral)",
        ink: "var(--ink)",
        agent: "var(--agent)",
        human: "var(--human)",
        success: "var(--success)",
        failure: "var(--failure)",
      },
      fontFamily: { sans: ["Fira Sans", "sans-serif"], mono: ["Fira Mono", "monospace"] },
    },
  },
  plugins: [],
} satisfies Config;

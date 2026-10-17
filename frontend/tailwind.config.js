/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        background: "#030406",
        surface: "rgba(10, 13, 20, 0.78)",
        surfaceHover: "rgba(18, 24, 38, 0.85)",
        borderSubtle: "rgba(255, 255, 255, 0.08)",
        cinema: {
          bg: "#030406",
          card: "rgba(8, 10, 16, 0.76)",
          cardHover: "rgba(16, 20, 30, 0.85)",
          border: "rgba(255, 255, 255, 0.08)",
          borderBright: "rgba(255, 255, 255, 0.18)",
          cyan: "#00f0ff",
          purple: "#a855f7",
          pink: "#f43f5e",
          amber: "#f59e0b",
          lime: "#caff70",
        },
        pastel: {
          bg: "#030406",
          canvas: "#030406",
          card: "rgba(10, 13, 20, 0.8)",
          cardMuted: "rgba(16, 20, 30, 0.6)",
          border: "rgba(255, 255, 255, 0.08)",
          borderSubtle: "rgba(255, 255, 255, 0.05)",
          ink: "#FFFFFF",
          inkMuted: "#A1A1AA",
          inkLight: "#71717A",
          peach: "rgba(251, 146, 60, 0.15)",
          peachDark: "#FB923C",
          peachBorder: "rgba(251, 146, 60, 0.3)",
          lavender: "rgba(168, 85, 247, 0.15)",
          lavenderDark: "#C084FC",
          lavenderBorder: "rgba(168, 85, 247, 0.3)",
          sky: "rgba(0, 240, 255, 0.15)",
          skyDark: "#38BDF8",
          skyBorder: "rgba(0, 240, 255, 0.3)",
          mint: "rgba(52, 211, 153, 0.15)",
          mintDark: "#34D399",
          mintBorder: "rgba(52, 211, 153, 0.3)",
          rose: "rgba(244, 63, 94, 0.15)",
          roseDark: "#FB7185",
          roseBorder: "rgba(244, 63, 94, 0.3)",
          butter: "rgba(245, 158, 11, 0.15)",
          butterDark: "#FBBF24",
        }
      }
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'signal-buy': '#10b981',
        'signal-sell': '#ef4444',
        'signal-hold': '#6b7280',
        'signal-strong': '#059669',
        'signal-moderate': '#3b82f6',
      },
    },
  },
  plugins: [],
}

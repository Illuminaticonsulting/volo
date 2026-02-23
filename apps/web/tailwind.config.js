/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Volo brand colors — overridden per white-label tenant
        brand: {
          50: 'var(--brand-50, #f0f4ff)',
          100: 'var(--brand-100, #dbe4ff)',
          200: 'var(--brand-200, #bac8ff)',
          300: 'var(--brand-300, #91a7ff)',
          400: 'var(--brand-400, #748ffc)',
          500: 'var(--brand-500, #5c7cfa)',
          600: 'var(--brand-600, #4c6ef5)',
          700: 'var(--brand-700, #4263eb)',
          800: 'var(--brand-800, #3b5bdb)',
          900: 'var(--brand-900, #364fc7)',
          950: 'var(--brand-950, #1e3a8a)',
        },
        surface: {
          0: 'var(--surface-0, #ffffff)',
          1: 'var(--surface-1, #f8f9fa)',
          2: 'var(--surface-2, #f1f3f5)',
          3: 'var(--surface-3, #e9ecef)',
        },
        'surface-dark': {
          0: 'var(--surface-dark-0, #0a0a0b)',
          1: 'var(--surface-dark-1, #111113)',
          2: 'var(--surface-dark-2, #19191d)',
          3: 'var(--surface-dark-3, #222228)',
        },
      },
      fontFamily: {
        sans: ['var(--font-sans, "Inter")', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono, "JetBrains Mono")', 'monospace'],
      },
      animation: {
        'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
        'slide-up': 'slide-up 0.3s ease-out',
        'fade-in': 'fade-in 0.2s ease-out',
        'thinking': 'thinking 1.5s ease-in-out infinite',
      },
      keyframes: {
        'pulse-soft': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.7 },
        },
        'slide-up': {
          '0%': { transform: 'translateY(10px)', opacity: 0 },
          '100%': { transform: 'translateY(0)', opacity: 1 },
        },
        'fade-in': {
          '0%': { opacity: 0 },
          '100%': { opacity: 1 },
        },
        'thinking': {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.05)' },
        },
      },
    },
  },
  plugins: [],
};

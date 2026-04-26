/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          900: '#0a0908',
          800: '#16140f',
          700: '#231f17',
          600: '#3b342a',
          500: '#6b6357',
          400: '#9b9387',
          300: '#c8c0b3',
          200: '#e6dfd2',
          100: '#f5f0e6',
          50:  '#faf6ee',
        },
        flame: {
          DEFAULT: '#e25822',
          light:   '#f08456',
          dark:    '#a73d11',
        },
        moss: {
          DEFAULT: '#4a5d23',
          light:   '#6b7f3a',
        },
        ocean: {
          DEFAULT: '#1c4159',
          light:   '#3b6e8f',
        },
        // Tier colors
        tierA: '#2d6a4f',
        tierB: '#a16207',
        tierC: '#9f1239',
      },
      fontFamily: {
        display: ['"Fraunces"', '"Times New Roman"', 'serif'],
        body: ['"Söhne"', '"Inter"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      letterSpacing: {
        editorial: '-0.04em',
      },
      boxShadow: {
        editorial: '0 1px 0 0 rgb(0 0 0 / 0.04), 0 8px 24px -8px rgb(20 14 8 / 0.12)',
        'inner-paper': 'inset 0 1px 0 0 rgb(255 255 255 / 0.6)',
      },
      backgroundImage: {
        'noise': "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3'/%3E%3CfeColorMatrix values='0 0 0 0 0.04 0 0 0 0 0.04 0 0 0 0 0.04 0 0 0 0.5 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.4'/%3E%3C/svg%3E\")",
      },
      animation: {
        'fade-up': 'fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both',
        'shimmer': 'shimmer 2.4s linear infinite',
        'pulse-soft': 'pulseSoft 2.5s ease-in-out infinite',
      },
      keyframes: {
        fadeUp: {
          from: { opacity: '0', transform: 'translateY(12px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '0.6' },
          '50%':      { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}

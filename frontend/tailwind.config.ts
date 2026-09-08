import type { Config } from 'tailwindcss'

/**
 * Warm, local, community palette — terracotta and olive drawn from southern
 * Lebanese soil and olive groves, deliberately not corporate-SaaS blue.
 *
 * `brand`, `wheat` and `sea` are read off the جنوبنا mark: the deep forest
 * green of the wordmark and ring, the gold of the wheat ears, and the blue of
 * the sea below the hills. `clay` and `olive` were already close to the mark's
 * terracotta and foliage, so they are left alone — the new scales are what the
 * logo adds, not a repaint of what was there.
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Cairo', 'Tajawal', 'system-ui', 'sans-serif'],
        display: ['Tajawal', 'Cairo', 'system-ui', 'sans-serif'],
      },
      colors: {
        sand: {
          50: '#fdfaf6', 100: '#faf3ea', 200: '#f3e6d3',
          300: '#e8d2b4', 400: '#d9b98d', 500: '#c99f68',
        },
        clay: {
          50: '#fdf5f2', 100: '#fbe8e1', 200: '#f6cdbf',
          300: '#eda992', 400: '#e07c5c', 500: '#c65d3b',
          600: '#a84a2c', 700: '#8a3c24', 800: '#6d3020', 900: '#4d221a',
        },
        olive: {
          50: '#f4f7f2', 100: '#e6ede1', 200: '#cddbc4',
          300: '#a9c199', 400: '#7fa06b', 500: '#5d8049',
          600: '#476638', 700: '#3a512f', 800: '#2f4127', 900: '#233019',
        },
        brand: {
          50: '#eef6f0', 100: '#d6e9dc', 200: '#a9d0b6',
          300: '#6fb287', 400: '#3d9460', 500: '#1b6b3a',
          600: '#155830', 700: '#114626', 800: '#0d351d', 900: '#082312',
        },
        wheat: {
          100: '#fdf3d8', 200: '#fae7ae', 300: '#f5d786',
          500: '#e8ae1f', 600: '#c9911a', 700: '#9a6f14',
        },
        sea: {
          100: '#dceaf4', 300: '#8fbcd9', 500: '#1c6ea4',
          600: '#175c8a', 700: '#124e75',
        },
        ink: {
          50: '#f6f6f5', 100: '#e7e7e5', 300: '#b9b8b4',
          500: '#7a7975', 700: '#403f3c', 900: '#1f1e1c',
        },
      },
      borderRadius: { xl: '1rem', '2xl': '1.25rem', '3xl': '1.75rem' },
      boxShadow: {
        card: '0 1px 2px rgba(31,30,28,0.04), 0 8px 24px -12px rgba(31,30,28,0.18)',
        lift: '0 4px 12px rgba(31,30,28,0.08), 0 16px 40px -16px rgba(31,30,28,0.24)',
      },
      keyframes: {
        'fade-up': { '0%': { opacity: '0', transform: 'translateY(6px)' }, '100%': { opacity: '1', transform: 'none' } },
      },
      animation: { 'fade-up': 'fade-up 240ms ease-out both' },
    },
  },
  plugins: [],
} satisfies Config

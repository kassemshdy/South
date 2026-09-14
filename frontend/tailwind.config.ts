import type { Config } from 'tailwindcss'

/**
 * Warm, local, community palette — terracotta and olive drawn from southern
 * Lebanese soil and olive groves, deliberately not corporate-SaaS blue.
 *
 * **`brand` is olive and `sand` is sea sand** — «لون الزيتون ولون الرمل
 * البحري», asked for directly. Two scales changed and no component touched:
 * every `brand-*` and `sand-*` class in the app already pointed here, so the
 * whole repaint is these hex values plus the favicon, which hard-codes two of
 * them.
 *
 * `brand` was the deep forest green of the جنوبنا wordmark and ring. It is
 * now the olive of the groves — the mark's foliage rather than its ring, which
 * is the one thing this gives up and the reason `public/favicon.svg` moves
 * with it. `wheat` and `sea` still come off the mark untouched: the gold of
 * the wheat ears and the blue of the sea below the hills. The gold matters
 * more than it did — it is what keeps olive from reading as drab.
 *
 * `sand` kept a golden-desert bias through several revisions. Sea sand is the
 * paler, cooler, greyer thing you actually stand on at Tyre, so saturation
 * drops by roughly half across the ramp and the hue cools — while every
 * lightness step stays exactly where it was. That last part is what makes it
 * safe to repaint in one go: `sand-50` and `sand-100` are the ground under a
 * hundred surfaces, `sand-300` is a border and `sand-500` a placeholder
 * glyph, so holding lightness constant means nothing loses contrast against
 * anything.
 *
 * `clay` and `olive` are untouched. `olive` was already the foliage green and
 * is used more widely than `brand` ever was; the two now sit in one family
 * rather than two, which is the point of the change.
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
        // Sea sand. Same lightness steps as the golden sand it replaces, about
        // half the saturation, hue cooled — so no existing pairing shifts in
        // contrast, only in temperature.
        sand: {
          50: '#fbfaf7', 100: '#f5f2e9', 200: '#eae4d6',
          300: '#d7d0be', 400: '#beb6a1', 500: '#a39b85',
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
        // Olive, in place of the forest green. 700 is the anchor the app
        // actually leans on — header and footer mark, the homepage band, the
        // video frame — and carries white at 10.6:1 where the forest green
        // carried it at 10.9:1, so every white-on-brand surface that
        // passed before still passes.
        brand: {
          50: '#f2f6ee', 100: '#e0ebd8', 200: '#c3d7b6',
          300: '#9cbd8a', 400: '#739c60', 500: '#547d45',
          600: '#41633a', 700: '#2e4433', 800: '#243528', 900: '#18241b',
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

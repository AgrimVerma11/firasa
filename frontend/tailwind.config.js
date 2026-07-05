/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Brand palette shared with the backend (see ml/config.py).
        brand: {
          50: '#f2f1fb',
          100: '#e6e4f7',
          200: '#cdc9ef',
          300: '#a9a1e2',
          400: '#8479d2',
          500: '#6459c4',
          600: '#534ab7',
          700: '#45409b',
          800: '#3a367e',
          900: '#302e64',
          950: '#1f1d40',
        },
        ink: {
          50: '#f6f7f9',
          100: '#eceef2',
          200: '#d5dae2',
          300: '#b0bac8',
          400: '#8593a8',
          500: '#65748c',
          600: '#505d73',
          700: '#424c5e',
          800: '#3a4250',
          900: '#343a45',
          950: '#22262e',
        },
        risk: {
          low: '#1d9e75',
          moderate: '#ef9f27',
          high: '#d85a30',
        },
      },
      fontFamily: {
        sans: ['"Inter Variable"', 'Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(16, 24, 40, 0.04), 0 12px 32px -12px rgba(48, 46, 100, 0.18)',
        lift: '0 24px 48px -20px rgba(48, 46, 100, 0.35)',
      },
      borderRadius: {
        '2xl': '1.125rem',
        '3xl': '1.5rem',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.5s ease-out both',
      },
    },
  },
  plugins: [],
};

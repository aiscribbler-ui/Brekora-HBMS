/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  safelist: ['font-display', 'font-body'],
  theme: {
    extend: {
      borderRadius: {
        md: '8px',
      },
      boxShadow: {
        sm: '0 1px 2px 0 rgb(194 125 58 / 0.05)',
        DEFAULT: '0 1px 3px 0 rgb(194 125 58 / 0.1), 0 1px 2px -1px rgb(194 125 58 / 0.1)',
        md: '0 4px 6px -1px rgb(194 125 58 / 0.1), 0 2px 4px -2px rgb(194 125 58 / 0.1)',
        lg: '0 10px 15px -3px rgb(194 125 58 / 0.1), 0 4px 6px -4px rgb(194 125 58 / 0.1)',
        xl: '0 20px 25px -5px rgb(194 125 58 / 0.1), 0 8px 10px -6px rgb(194 125 58 / 0.1)',
      },
      colors: {
        brand: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#026ba0',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        gray: {
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#6b7280',
          500: '#4b5563',
          600: '#374151',
          700: '#1f2937',
          800: '#111827',
          900: '#030712',
        },
        success: {
          light: '#ecfdf5',
          DEFAULT: '#047857',
          dark: '#065f46',
        },
        warning: {
          light: '#fffbeb',
          DEFAULT: '#b45309',
          dark: '#92400e',
        },
        info: {
          light: '#eff6ff',
          DEFAULT: '#0369a1',
          dark: '#075985',
        },
        secondary: {
          light: '#fef3e2',
          DEFAULT: '#c27d3a',
          dark: '#9a5e2a',
        },
        error: {
          light: '#fef2f2',
          DEFAULT: '#dc2626',
          dark: '#b91c1c',
        },
      },
      fontFamily: {
        display: ["'Playfair Display'", 'Georgia', 'serif'],
        body: ["'Manrope'", '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      keyframes: {
        'float-slow': {
          '0%, 100%': { transform: 'translate(0, 0) scale(1)' },
          '50%': { transform: 'translate(20px, -20px) scale(1.05)' },
        },
        'float-medium': {
          '0%, 100%': { transform: 'translate(0, 0) scale(1)' },
          '50%': { transform: 'translate(-15px, 15px) scale(0.95)' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
      },
      animation: {
        'float-slow': 'float-slow 12s ease-in-out infinite',
        'float-medium': 'float-medium 9s ease-in-out infinite',
        'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}

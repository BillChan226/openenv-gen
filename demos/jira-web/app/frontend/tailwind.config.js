/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: 'rgb(var(--bg))',
          muted: 'rgb(var(--bg-muted))',
          elevated: 'rgb(var(--bg-elevated))',
        },
        fg: {
          DEFAULT: 'rgb(var(--fg))',
          muted: 'rgb(var(--fg-muted))',
        },
        border: 'rgb(var(--border))',
        primary: {
          DEFAULT: 'rgb(var(--primary))',
          fg: 'rgb(var(--primary-fg))',
        },
        success: {
          DEFAULT: 'rgb(var(--success))',
          fg: 'rgb(var(--success-fg))',
        },
        danger: {
          DEFAULT: 'rgb(var(--danger))',
          fg: 'rgb(var(--danger-fg))',
        },
        warning: {
          DEFAULT: 'rgb(var(--warning))',
          fg: 'rgb(var(--warning-fg))',
        },
      },
      boxShadow: {
        card: '0 1px 0 rgba(0,0,0,0.08), 0 4px 20px rgba(0,0,0,0.12)',
      },
    },
  },
  plugins: [],
};

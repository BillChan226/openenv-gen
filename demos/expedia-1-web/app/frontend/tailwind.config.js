/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#EFF6FF',
          100: '#DBEAFE',
          200: '#BFDBFE',
          300: '#93C5FD',
          400: '#60A5FA',
          500: '#3B82F6',
          600: '#1668E3',
          700: '#0B5BD3',
          800: '#1E40AF',
          900: '#1E3A8A'
        },
        accent: {
          500: '#F59E0B',
          600: '#D97706'
        }
      },
      boxShadow: {
        card: '0 1px 2px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.06)',
        dropdown: '0 10px 30px rgba(0,0,0,0.12)'
      },
      borderRadius: {
        xl: '20px'
      }
    }
  },
  plugins: []
};

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef5ff',
          100: '#d8e9ff',
          200: '#b3d3ff',
          300: '#7fb7ff',
          400: '#4593ff',
          500: '#1668E3',
          600: '#0f56c2',
          700: '#0d459a',
          800: '#0d3b7a',
          900: '#0b315f'
        },
        accent: {
          500: '#F4B400'
        }
      },
      borderRadius: {
        card: '16px'
      },
      boxShadow: {
        soft: '0 10px 30px rgba(2, 6, 23, 0.08)'
      }
    }
  },
  plugins: []
};

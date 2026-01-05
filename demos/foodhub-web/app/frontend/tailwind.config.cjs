/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          500: '#FF3008',
          600: '#E62B07'
        }
      },
      boxShadow: {
        soft: '0 10px 30px rgba(17, 17, 17, 0.08)',
        card: '0 12px 28px rgba(17, 17, 17, 0.10)'
      },
      borderRadius: {
        xl: '16px',
        '2xl': '20px'
      }
    }
  },
  plugins: []
};

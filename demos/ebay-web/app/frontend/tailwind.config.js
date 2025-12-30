/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          blue: '#0B66C3',
        },
      },
      boxShadow: {
        header: '0 1px 0 rgba(0,0,0,0.08)',
      },
    },
  },
  plugins: [],
};

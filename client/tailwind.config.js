/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'fra-cream': '#F5F2EA',
        'fra-cream-card': '#FAF8F3',
        'fra-yellow': '#FFE600',
        'fra-yellow-hover': '#edd600',
        'fra-black': '#000000',
        'fra-sidebar': '#0A0A0A',
        'fra-sidebar-card': '#141414',
        'fra-border': '#000000',
        'fra-gray': '#E5DFD3',
        'fra-green': '#22C55E',
        'fra-amber': '#F59E0B',
        'fra-red': '#EF4444',
      },
      fontFamily: {
        sans: ['"Space Grotesk"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        body: ['Inter', 'sans-serif'],
      },
      boxShadow: {
        brutal: '2px 2px 0px #000000',
        'brutal-sm': '1.5px 1.5px 0px #000000',
        'brutal-lg': '4px 4px 0px #000000',
        'brutal-xl': '6px 6px 0px #000000',
      },
    },
  },
  plugins: [],
};

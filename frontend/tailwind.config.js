/** Design tokens carried over unchanged from the studysphere.html prototype. */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#244B45', dark: '#1a3733', light: '#3a675f' },
        gold: { DEFAULT: '#D9A441', dark: '#B4842E', light: '#EFCB80' },
        bg: '#F7F5F0',
        surface: '#FFFFFF',
        ink: '#202522',
        muted: '#6F756F',
        line: '#E3E0D8',
      },
      fontFamily: {
        display: ['"DM Sans"', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      // The prototype used /8 and /15 opacity steps, which Tailwind's default scale lacks.
      opacity: { 8: '0.08', 15: '0.15' },
    },
  },
  plugins: [],
}

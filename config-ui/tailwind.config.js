import preset from 'locveil-ui-kit/preset'

/** @type {import('tailwindcss').Config} */
export default {
  // Locveil preset (tokens pair: locveil-ui-kit/tokens.css, imported in main.tsx);
  // the kit's dist is scanned so utility classes inside kit components are generated.
  presets: [preset],
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
    './node_modules/locveil-ui-kit/dist/**/*.js',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}

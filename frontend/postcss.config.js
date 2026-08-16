/** Tailwind v4 runs as a PostCSS plugin; the whole theme lives in app/globals.css.
 *  CommonJS on purpose: this Next version resolves .js PostCSS configs reliably and
 *  quietly ignored the .mjs spelling, which shipped a page with raw @apply in it. */
module.exports = {
  plugins: {
    '@tailwindcss/postcss': {},
  },
}

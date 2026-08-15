import { FlatCompat } from '@eslint/eslintrc'

// Committed so `npm run lint` runs in a gate rather than opening a setup prompt. A lint step
// that asks a question is a lint step no pipeline can run.
const compat = new FlatCompat({ baseDirectory: import.meta.dirname })

const config = [
  ...compat.extends('next/core-web-vitals', 'next/typescript'),
  { ignores: ['.next/**', 'node_modules/**', 'next-env.d.ts'] },
]

export default config

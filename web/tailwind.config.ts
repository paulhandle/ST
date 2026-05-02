import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        ink: 'var(--ink)',
        'ink-faint': 'var(--ink-faint)',
        'ink-mid': 'var(--ink-mid)',
        paper: 'var(--paper)',
        accent: 'var(--accent)',
        'accent-light': 'var(--accent-light)',
        rule: 'var(--rule)',
        'rule-soft': 'var(--rule-soft)',
      },
      fontFamily: {
        hand: ['var(--font-hand)', 'Kalam', 'cursive'],
        annot: ['var(--font-annot)', 'Caveat', 'cursive'],
        mono: ['var(--font-mono)', 'ui-monospace', 'monospace'],
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [],
}

export default config

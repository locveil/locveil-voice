// eslint-9 flat config (UI-18; sprint-01 decision 1 — was .eslintrc.cjs).
// Lint scope = shipped app code, ts/tsx only, same as the old --ext ts,tsx run.
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';

export default tseslint.config(
  { ignores: ['dist/**'] },
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      ...tseslint.configs.recommended,
      // type-aware rules (no-floating-promises, no-misused-promises, await-thenable, ...) —
      // require the project setup below; this is what catches the bugs `tsc` + plain lint miss.
      ...tseslint.configs.recommendedTypeChecked,
    ],
    languageOptions: {
      parserOptions: {
        // every linted file must belong to one of these projects for type-aware rules to resolve.
        // tsconfig.json = app code (src); tsconfig.node.json = vite.config.ts.
        project: ['./tsconfig.json', './tsconfig.node.json'],
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      // Disable base ESLint no-unused-vars and use TypeScript version
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          ignoreRestSiblings: true,
          args: 'none', // Don't check function/method parameters
        },
      ],
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/ban-ts-comment': 'off',
      'prefer-const': 'off',
      '@typescript-eslint/no-non-null-assertion': 'off',

      // --- type-aware tuning (identical to ../wb-mqtt-bridge/ui) ---
      // The no-unsafe-* family + restrict-template-expressions fire constantly in a codebase that
      // intentionally allows `any` (no-explicit-any is off above); they'd bury the signal. Keep the
      // high-value async/correctness rules from recommended-type-checked, drop the `any`-noise ones.
      '@typescript-eslint/no-unsafe-assignment': 'off',
      '@typescript-eslint/no-unsafe-member-access': 'off',
      '@typescript-eslint/no-unsafe-call': 'off',
      '@typescript-eslint/no-unsafe-return': 'off',
      '@typescript-eslint/no-unsafe-argument': 'off',
      '@typescript-eslint/restrict-template-expressions': 'off',
      '@typescript-eslint/no-redundant-type-constituents': 'off',
      // un-awaited promises are a real bug class (esp. in fetch-and-render code); keep as errors.
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
    },
  }
);

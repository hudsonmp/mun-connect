// eslint.config.js
const { FlatCompat } = require('@eslint/eslintrc');
const path = require('path');

const compat = new FlatCompat({
  baseDirectory: __dirname,
  recommendedConfig: {},
  allConfig: {}
});

module.exports = [
  {
    ignores: [
      '**/node_modules/**', 
      '.next/**', 
      '**/mun-connect/.next/**',
      '*.config.js', 
      '*.config.mjs', 
      '*.setup.js', 
      '*.sql', 
      '.vercel/**'
    ]
  },
  // Extending Next.js ESLint config
  ...compat.extends('next/core-web-vitals'),
  {
    linterOptions: {
      reportUnusedDisableDirectives: true
    },
    rules: {
      'react/react-in-jsx-scope': 'off',
      'react/prop-types': 'off',
      'no-console': 'off' // Allow console statements for now
    }
  }
]; 
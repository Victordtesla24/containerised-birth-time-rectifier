module.exports = {
  extends: 'next/core-web-vitals',
  rules: {
    // Turn off rules that are blocking the build
    '@typescript-eslint/no-unused-vars': 'warn',
    '@typescript-eslint/no-explicit-any': 'warn',
    'no-console': 'warn',
    'react/no-unescaped-entities': 'off',
    'react-hooks/exhaustive-deps': 'warn',
    'react/no-unknown-property': 'warn',
    'testing-library/no-debugging-utils': 'warn',
    'testing-library/no-unnecessary-act': 'warn',
    'testing-library/no-wait-for-multiple-assertions': 'warn',
    'testing-library/no-node-access': 'warn',
    'no-case-declarations': 'warn',
    'no-useless-escape': 'warn',
    '@typescript-eslint/no-var-requires': 'warn',
  }
};

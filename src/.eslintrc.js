module.exports = {
  extends: ['next/core-web-vitals'],
  rules: {
    '@typescript-eslint/no-unused-vars': 'off',
    '@typescript-eslint/no-explicit-any': 'off',
    '@typescript-eslint/no-var-requires': 'off',
    'testing-library/no-debugging-utils': 'off',
    'testing-library/no-unnecessary-act': 'off',
    'testing-library/no-wait-for-multiple-assertions': 'off',
    'testing-library/no-node-access': 'off',
    'no-console': 'off',
    'react-hooks/exhaustive-deps': 'off',
    'react/no-unknown-property': 'off',
    'react/no-unescaped-entities': 'off',
    '@next/next/no-page-custom-font': 'off'
  }
};

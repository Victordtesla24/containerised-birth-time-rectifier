const nextJest = require('next/jest');

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files in your test environment
  dir: './',
});

// Add any custom config to be passed to Jest
/** @type {import('jest').Config} */
const customJestConfig = {
  // Add more setup options before each test is run
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.{js,jsx,ts,tsx}',
    '<rootDir>/tests/unit/**/*.{js,jsx,ts,tsx}'
  ],
  // Ignore certain patterns
  testPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/.next/',
    '<rootDir>/tests/integration/',
    '<rootDir>/tests/e2e/',
    '<rootDir>/tests/performance/',
    '<rootDir>/cypress/'
  ],
  moduleNameMapper: {
    // Handle CSS imports (with CSS modules)
    '\\.module\\.(css|sass|scss)$': 'identity-obj-proxy',
    // Handle CSS imports (without CSS modules)
    '\\.(css|sass|scss)$': '<rootDir>/__mocks__/styleMock.js',
    // Handle image imports
    '\\.(jpg|jpeg|png|gif|webp|svg)$': '<rootDir>/__mocks__/fileMock.js',
    // Handle module aliases
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  // Transform files with babel
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['babel-jest', { presets: ['next/babel'] }]
  },
  // Whether to use watchman for file crawling
  watchman: false,
  // Enforce strict testing behavior - treat all errors as terminal
  // and prevent test continuation after failures
  clearMocks: true,
  resetMocks: true,
  restoreMocks: true,
  // Fail tests if there are any console.error calls
  errorOnDeprecated: true,
  // Don't allow test files to override global functions
  testEnvironmentOptions: {
    suppressConsole: false
  },
  // Exit immediately on test failures
  bail: true,
  // For coverage reporting
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
    '!src/**/__tests__/**/*',
    '!src/pages/_app.tsx',
    '!src/pages/_document.tsx',
  ]
};

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig);

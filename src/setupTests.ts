// Mock window.scrollTo
window.scrollTo = jest.fn();

// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// MSW server is disabled to allow real API calls
// If you need to re-enable MSW for specific tests, import and setup the server in those test files

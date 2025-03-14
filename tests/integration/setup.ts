// Add type declarations for jest-dom matchers
import '@testing-library/jest-dom';

// Extend the Jest matchers to include testing-library matchers
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeInTheDocument(): R;
      toHaveTextContent(text: string | RegExp): R;
      toBeVisible(): R;
      toBeDisabled(): R;
      toBeEnabled(): R;
      toHaveAttribute(attr: string, value?: string): R;
      toHaveClass(className: string): R;
      toHaveFocus(): R;
      toBeChecked(): R;
      toBeRequired(): R;
    }
  }
}

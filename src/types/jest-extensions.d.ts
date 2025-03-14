// Type declarations for Jest extensions

declare namespace jest {
  interface Matchers<R> {
    toBeInTheDocument(): R;
    toHaveAttribute(attr: string, value?: string): R;
    toHaveTextContent(text: string | RegExp): R;
    toHaveClass(className: string): R;
    toBeVisible(): R;
    toBeDisabled(): R;
    toBeEnabled(): R;
    toBeChecked(): R;
    toBeEmpty(): R;
    toHaveFocus(): R;
    toHaveStyle(style: Record<string, any>): R;
    toHaveValue(value: string | number | string[]): R;
  }
}

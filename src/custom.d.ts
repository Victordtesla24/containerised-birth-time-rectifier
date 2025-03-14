/* Custom declarations file for non-standard imports */

// CSS Module declarations
declare module '*.module.css' {
  const classes: { readonly [key: string]: string };
  export default classes;
}

declare module '*.module.scss' {
  const classes: { readonly [key: string]: string };
  export default classes;
}

// Specific CSS module files that TypeScript can't find
declare module './BirthDetailsForm.module.css' {
  const classes: { readonly [key: string]: string };
  export default classes;
}

declare module './LocationAutocomplete.module.css' {
  const classes: { readonly [key: string]: string };
  export default classes;
}

declare module './TimeRangePicker.module.css' {
  const classes: { readonly [key: string]: string };
  export default classes;
}

// Add other asset imports if needed
declare module '*.svg' {
  import React = require('react');
  export const ReactComponent: React.FC<React.SVGProps<SVGSVGElement>>;
  const src: string;
  export default src;
}

declare module '*.jpg' {
  const content: string;
  export default content;
}

declare module '*.png' {
  const content: string;
  export default content;
}

declare module '*.json' {
  const content: Record<string, any>;
  export default content;
}

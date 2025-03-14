// React override types
/// <reference types="react" />

// Use namespace import * as React from 'react' instead of default import
declare module 'react' {
  export = React;
  export as namespace React;
}

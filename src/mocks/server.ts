import { setupServer } from 'msw/node';
import { handlers } from './handlers';

// This configures a request mocking server with the given request handlers
export const server = setupServer(...handlers);

// Add a type definition for the MSW server to fix imports
declare global {
  // eslint-disable-next-line no-var
  var msw: {
    server: ReturnType<typeof setupServer>;
  };
}

// Export server globally for easy testing access
globalThis.msw = { server };

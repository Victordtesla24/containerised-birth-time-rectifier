// Mock Next.js router for testing
function createMockRouter(props) {
  return {
    basePath: '',
    pathname: '/',
    route: '/',
    asPath: '/',
    query: {},
    push: jest.fn(() => Promise.resolve(true)),
    replace: jest.fn(() => Promise.resolve(true)),
    reload: jest.fn(() => Promise.resolve(true)),
    back: jest.fn(() => Promise.resolve(true)),
    prefetch: jest.fn(() => Promise.resolve()),
    beforePopState: jest.fn(),
    events: {
      on: jest.fn(),
      off: jest.fn(),
      emit: jest.fn()
    },
    isFallback: false,
    isReady: true,
    ...props
  };
}

module.exports = { createMockRouter };

const React = require('react');
const { RouterContext } = require('next/dist/shared/lib/router-context.shared-runtime');
const { createMockRouter } = require('./mockRouter');

function withMockRouter(Component, routerProps = {}) {
  const mockRouter = createMockRouter(routerProps);

  return function WrappedComponent(props) {
    return (
      React.createElement(
        RouterContext.Provider,
        { value: mockRouter },
        React.createElement(Component, props)
      )
    );
  };
}

module.exports = {
  withMockRouter,
  createMockRouter
};

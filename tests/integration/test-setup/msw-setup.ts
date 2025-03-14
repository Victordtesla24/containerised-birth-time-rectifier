/**
 * Real API Integration Test Setup
 *
 * This file completely removes all mocks and ensures tests use real services.
 * If services are not available, tests will fail with clear error messages.
 */

/**
 * DO NOT USE - this function is intentionally designed to throw an error
 * @deprecated All tests should use real services
 */
export const setupMockAPI = () => {
  throw new Error(`
  ==================================================================
  ERROR: setupMockAPI has been removed to prevent tests from using mocks.

  All tests must use real services. Please ensure required services are running:
  - Run 'docker-compose up' to start all services
  - Or start the services manually according to the documentation

  Tests should fail properly when services are unavailable to ensure
  correct error handling in the application.
  ==================================================================
  `);
};

/**
 * DO NOT USE - this function is intentionally designed to throw an error
 * @deprecated All tests should use real services
 */
export const mockApiCall = (path: string, responseData: any) => {
  throw new Error(`
  ==================================================================
  ERROR: mockApiCall has been removed to prevent tests from using mocks.

  All tests must use real services. Please ensure required services are running:
  - Run 'docker-compose up' to start all services
  - Or start the services manually according to the documentation

  Tests should fail properly when services are unavailable to ensure
  correct error handling in the application.
  ==================================================================
  `);
};

/**
 * Checks if services are available and returns a detailed report
 * Use this to verify service status but do not skip tests
 */
export const checkAllServices = async (): Promise<{
  allAvailable: boolean;
  services: {
    api: boolean;
    frontend: boolean;
    ai: boolean;
  };
  message: string;
}> => {
  try {
    // Determine service URLs from environment variables or use defaults
    const frontendUrl = process.env.FRONTEND_URL || 'http://localhost:3000';
    const apiUrl = `${frontendUrl}/api`;
    const aiServiceUrl = process.env.AI_SERVICE_URL || 'http://localhost:8000';

    console.log(`Checking services at:
    - Frontend: ${frontendUrl}
    - API: ${apiUrl}/health
    - AI: ${aiServiceUrl}/health`);

    // Check each service
    const apiResponse = await fetch(`${apiUrl}/health`).catch(() => ({ ok: false }));
    const aiResponse = await fetch(`${aiServiceUrl}/health`).catch(() => ({ ok: false }));
    const frontendResponse = await fetch(`${frontendUrl}`).catch(() => ({ ok: false }));

    // Determine status
    const services = {
      api: apiResponse.ok,
      ai: aiResponse.ok,
      frontend: frontendResponse.ok
    };

    console.log(`Service status:
    - Frontend: ${services.frontend ? 'OK' : 'Not Available'}
    - API: ${services.api ? 'OK' : 'Not Available'}
    - AI: ${services.ai ? 'OK' : 'Not Available'}`);

    const allAvailable = services.api && services.ai && services.frontend;

    // Generate message
    let message = allAvailable
      ? "All services are available"
      : "Some services are not available:";

    if (!services.api) message += "\n- API service is not running";
    if (!services.ai) message += "\n- AI service is not running";
    if (!services.frontend) message += "\n- Frontend service is not running";

    if (!allAvailable) {
      message += "\n\nPlease start all required services before running tests:";
      message += "\n- Run 'docker-compose up' to start all services";
      message += "\n- Or run 'npm run start:services' to start them individually";
    }

    return {
      allAvailable,
      services,
      message
    };
  } catch (error) {
    return {
      allAvailable: false,
      services: {
        api: false,
        frontend: false,
        ai: false
      },
      message: `Error checking services: ${error}`
    };
  }
};

/**
 * Fetch utility functions for making API requests with timeout and error handling
 */

interface FetchWithTimeoutOptions extends RequestInit {
  timeout?: number;
}

class FetchTimeoutError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'FetchTimeoutError';
  }
}

/**
 * Wrapper around fetch that supports timeout
 * @param url The URL to fetch
 * @param options Fetch options with additional timeout property
 * @returns Promise that resolves to fetch Response
 * @throws FetchTimeoutError if the request times out
 */
export async function fetchWithTimeout(
  url: string,
  options: FetchWithTimeoutOptions = {}
): Promise<Response> {
  const { timeout = 30000, ...fetchOptions } = options;

  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new FetchTimeoutError(`Request timed out after ${timeout}ms`);
    }
    throw error;
  }
}

/**
 * Handles API responses with proper error handling
 * @param response The fetch Response object
 * @returns Promise that resolves to the parsed JSON response
 * @throws Error if the response status is not in the 200-299 range
 */
export async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const errorMessage =
      errorData.message ||
      errorData.error ||
      `API error: ${response.status} ${response.statusText}`;

    const error = new Error(errorMessage);
    throw error;
  }

  return await response.json() as T;
}

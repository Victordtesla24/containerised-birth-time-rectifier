// Mock Service Worker - Production version
// This file is used for Vercel deployments to avoid build errors

export const worker = {
  start: () => Promise.resolve(),
  stop: () => Promise.resolve(),
  use: () => null,
  resetHandlers: () => null
};

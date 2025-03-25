/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Enable webpack configuration for Docker environment
  webpack: (config, { dev, isServer }) => {
    // Additional webpack configurations for Docker environment
    if (process.env.DOCKER_ENV === 'true') {
      // Optimize for Docker environment
      config.watchOptions = {
        // Poll files for changes instead of using file system events
        poll: 1000,
        // Ignore node_modules except for specific packages
        ignored: ['node_modules/**', '!node_modules/some-package-to-watch/**'],
      };
    }
    return config;
  },
  // Output standalone builds for containerization
  output: process.env.NODE_ENV === 'production' ? 'standalone' : undefined,
};

module.exports = nextConfig;

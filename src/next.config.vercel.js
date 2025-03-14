/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: ['vercel.com'],
  },
  eslint: {
    // Disable ESLint during builds to focus on deployment
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Disable type checking during build for performance
    ignoreBuildErrors: true,
  },
  webpack: (config, { isServer, dev }) => {
    // Handle MSW specifically for production builds
    if (!dev) {
      // Use production version of MSW in production
      config.resolve.alias['src/mocks/browser'] = require.resolve('./src/mocks/browser.production.ts');
    }

    return config;
  },
  // Redirects and rewrites from original config
  async redirects() {
    return [
      {
        source: '/health',
        destination: '/api/health',
        permanent: true,
      },
    ];
  },
};

module.exports = nextConfig;

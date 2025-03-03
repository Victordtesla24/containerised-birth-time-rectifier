/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: [],
    // Specify the path prefix for the local images
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
      },
    ],
  },
  // Allow images to be loaded from the public folder using paths like /images/*
  async rewrites() {
    return [
      {
        source: '/images/:path*',
        destination: '/images/:path*',
      },
    ];
  },
  // Add pageExtensions to clarify which files to use as pages
  pageExtensions: ['tsx', 'ts', 'jsx', 'js'],
  // Disable directory scanning for old directories
  onDemandEntries: {
    // Additional configuration to prevent scanning old directories
    maxInactiveAge: 25 * 1000,
    pagesBufferLength: 2,
  },
  // Disable directories we've consolidated
  transpilePackages: [],
  // Add Webpack configuration to ignore old directories
  webpack: (config, { isServer }) => {
    // WASM configuration for Swiss Ephemeris
    config.experiments = {
      ...config.experiments,
      asyncWebAssembly: true,
    };

    // Optimize production builds
    if (!isServer) {
      config.optimization.splitChunks.cacheGroups = {
        ...config.optimization.splitChunks.cacheGroups,
        commons: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all',
          priority: 10,
        },
      };

      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        path: false,
      };
    }

    // This helps ignore the old directory structures
    config.watchOptions = {
      ...config.watchOptions,
      ignored: ['**/service-manager/**', '**/frontend/**', '**/node_modules/**']
    };
  
    return config;
  },
  // Environment variables that need to be available to the client
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
};

module.exports = nextConfig;
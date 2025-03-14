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
  // Configure rewrites to proxy API requests to the backend
  async rewrites() {
    return [
      {
        source: '/images/:path*',
        destination: '/images/:path*',
      },
      {
        source: '/api/health',
        destination: '/api/health',
      },
      {
        // Forward API requests to the backend service
        source: '/api/:path*',
        destination: process.env.DOCKER_ENV === 'true' ? 'http://ai_service:8000/api/:path*' : 'http://localhost:8000/api/:path*',
      }
    ];
  },

  // Add Webpack configuration to ignore old directories and fix imports
  webpack: (config, { isServer }) => {
    // Fix the three-mesh-bvh BatchedMesh import issue by providing a fallback module
    config.resolve.alias = {
      ...config.resolve.alias,
      // Intercept imports of three-mesh-bvh/src/utils/ExtensionUtilities.js
      'three-mesh-bvh/src/utils/ExtensionUtilities.js': require.resolve('./patches/three-mesh-bvh/fix-batched-mesh.js'),
    };

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

// Vercel-specific configurations
if (process.env.VERCEL) {
  nextConfig.env = {
    ...nextConfig.env,
    NEXT_PUBLIC_API_URL: process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}/api` : 'https://birth-time-rectifier.vercel.app/api',
    IS_VERCEL: 'true',
  };
}

module.exports = nextConfig;

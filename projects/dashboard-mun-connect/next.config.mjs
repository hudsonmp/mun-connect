/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  typescript: {
    // Allow production builds to complete even with type errors
    ignoreBuildErrors: true,
  },
  eslint: {
    // Allow production builds to complete even with ESLint errors
    ignoreDuringBuilds: true,
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
  // Configure base path for the dashboard
  basePath: '/dashboard',
  // Configure environment variables
  env: {
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    DEPLOYMENT_TARGET: 'dashboard',
    NEXT_PUBLIC_SITE_URL: process.env.NEXT_PUBLIC_SITE_URL || 'https://mun-connect-dashboard.vercel.app',
    NEXT_PUBLIC_STATIC_SITE_URL: process.env.NEXT_PUBLIC_STATIC_SITE_URL || 'https://mun-connect.vercel.app',
    // Add this to help components be aware of the basePath
    NEXT_PUBLIC_BASE_PATH: '/dashboard',
  },
  // Configure redirects from the root to the dashboard and fix duplicate paths
  async redirects() {
    return [
      {
        source: '/',
        destination: '/dashboard',
        permanent: false,
      },
      // Handle duplicate dashboard path
      {
        source: '/dashboard/dashboard',
        destination: '/dashboard',
        permanent: false,
      },
      // Handle possible auth callback paths
      {
        source: '/dashboard/dashboard/auth/callback',
        destination: '/dashboard/auth/callback',
        permanent: false,
      }
    ]
  },
  // Add headers to help with authentication and CORS
  async headers() {
    return [
      {
        // Apply these headers to all routes
        source: '/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-store, max-age=0',
          },
          {
            key: 'Pragma',
            value: 'no-cache',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
      {
        // Apply these headers specifically to auth routes
        source: '/auth/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-store, max-age=0',
          },
          {
            key: 'Pragma',
            value: 'no-cache',
          }
        ],
      },
    ];
  },
  // Extended experimental features to support authentication
  experimental: {
    serverActions: {
      allowedOrigins: ['localhost:3000', '127.0.0.1:3000']
    },
  }
};

export default nextConfig; 
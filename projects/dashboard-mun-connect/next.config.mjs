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
  experimental: {
    // Handle packages that need to be external
    serverComponentsExternalPackages: ['@supabase/supabase-js']
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
  },
  // Configure redirects from the root to the dashboard 
  async redirects() {
    return [
      {
        source: '/',
        destination: '/dashboard',
        permanent: false,
      }
    ]
  }
};

export default nextConfig; 
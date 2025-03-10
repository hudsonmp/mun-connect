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
  // Configure build environment based on deployment target
  env: {
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    DEPLOYMENT_TARGET: process.env.DEPLOYMENT_TARGET || 'main',
  },
  // Configure redirects to the dashboard site
  async redirects() {
    return [
      {
        source: '/dashboard',
        destination: 'https://dashboard.munconnect.org/dashboard',
        permanent: false,
      },
      {
        source: '/dashboard/:path*',
        destination: 'https://dashboard.munconnect.org/dashboard/:path*',
        permanent: false,
      },
    ]
  }
};

export default nextConfig; 
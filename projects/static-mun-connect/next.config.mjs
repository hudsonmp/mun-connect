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
  // Configure build environment based on deployment target
  env: {
    DEPLOYMENT_TARGET: 'static',
    NEXT_PUBLIC_DASHBOARD_URL: process.env.NEXT_PUBLIC_DASHBOARD_URL || 'https://mun-connect-dashboard.vercel.app',
    NEXT_PUBLIC_SITE_URL: process.env.NEXT_PUBLIC_SITE_URL || 'https://mun-connect.vercel.app',
  },
  // Configure redirects to the dashboard site
  async redirects() {
    const dashboardUrl = process.env.NEXT_PUBLIC_DASHBOARD_URL || 'https://mun-connect-dashboard.vercel.app';
    return [
      {
        source: '/dashboard',
        destination: `${dashboardUrl}/dashboard`,
        permanent: false,
      },
      {
        source: '/dashboard/:path*',
        destination: `${dashboardUrl}/dashboard/:path*`,
        permanent: false,
      },
    ]
  }
};

export default nextConfig; 
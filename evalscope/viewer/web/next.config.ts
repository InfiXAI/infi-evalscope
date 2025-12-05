import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // output: 'export', // Enable for static export, requires removing dynamic routes
  // distDir: 'dist',
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;

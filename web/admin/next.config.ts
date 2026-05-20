import { config } from 'dotenv';

config();

/** @type {import('next').NextConfig} */
const nextConfig: import('next').NextConfig = {
  output: 'standalone',
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;

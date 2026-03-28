/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Required for a minimal Docker image (Next.js standalone output)
  output: "standalone",
};

export default nextConfig;

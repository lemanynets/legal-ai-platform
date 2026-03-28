/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Required for a minimal Docker image (Next.js standalone output)
  output: "standalone",
  // Prevent browser caching of JS chunks in development
  headers: async () => {
    if (process.env.NODE_ENV !== "production") {
      return [
        {
          source: "/_next/static/:path*",
          headers: [
            { key: "Cache-Control", value: "no-store, must-revalidate" },
          ],
        },
      ];
    }
    return [];
  },
};

export default nextConfig;

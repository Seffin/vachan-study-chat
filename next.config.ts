import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  allowedDevOrigins: ["192.168.1.101", "192.168.1.102", "192.168.1.104", "localhost", "127.0.0.1"],
  
  // Production optimizations for Vercel
  compress: true,
  productionBrowserSourceMaps: false,
  
  // Image optimization (if using Next.js Image component)
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**.vercel.app" },
    ],
  },
  
  // React Compiler (promoted out of experimental in Next.js 15+)
  reactCompiler: true,
};

export default nextConfig;

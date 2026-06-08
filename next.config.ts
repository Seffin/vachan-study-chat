import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  allowedDevOrigins: ["192.168.1.101", "192.168.1.102", "localhost", "127.0.0.1"],
};

export default nextConfig;

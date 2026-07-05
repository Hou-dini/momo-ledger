import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: "export",
  reactCompiler: true,
  allowedDevOrigins: ["172.28.208.1", "localhost", "127.0.0.1"],
};

export default nextConfig;

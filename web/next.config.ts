import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Smaller runtime image for Docker / container deploys (see docs/deployment-plan.md).
  output: "standalone",
};

export default nextConfig;

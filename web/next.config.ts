import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: [
    "sequelize",
    "pg",
    "pg-hstore",
    "winston",
    "winston-daily-rotate-file",
    "archiver",
  ],
};

export default nextConfig;
import { loadEnvConfig } from "@next/env";
import type { NextConfig } from "next";
import path from "node:path";

const cwd = process.cwd();
// In local dev (docker / bare node): cwd is `frontend/`, so we look one
// level up for the shared root .env.  On Vercel env vars are injected
// directly — the parent directory doesn't exist, so we just skip loading.
const envDirectory =
  path.basename(cwd) === "frontend" ? path.resolve(cwd, "..") : cwd;
try {
  loadEnvConfig(envDirectory);
} catch {
  // Vercel: no parent .env file — env vars come from the dashboard.
}

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: {
    optimizePackageImports: [
      "lucide-react",
      "framer-motion",
      "recharts",
      "@tanstack/react-query",
    ],
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "planetarycomputer.microsoft.com",
      },
      {
        protocol: "https",
        hostname: "*.blob.core.windows.net",
      },
    ],
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "geolocation=(self), camera=(self)" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
        ],
      },
      {
        source: "/map-styles/(.*)",
        headers: [{ key: "Cache-Control", value: "public, max-age=31536000, immutable" }],
      },
    ];
  },
};

export default nextConfig;

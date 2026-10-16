import type { NextConfig } from "next";

// Same origin (DESIGN §18, ADR-005): the browser only ever calls /api/*. In development
// Next forwards it to Django; in production nginx routes /api/ to Django directly.
const API_ORIGIN = process.env.API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // web/CLAUDE.md is the agent guide here; don't let `next dev` write AGENTS.md.
  agentRules: false,
  poweredByHeader: false,
  // Production runs the standalone server behind nginx (web/Dockerfile, infra/systemd).
  output: "standalone",
  reactStrictMode: true,
  // Django URLs end with a slash; keep the path exactly as the client wrote it.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      { source: "/api/:path*/", destination: `${API_ORIGIN}/api/:path*/` },
      { source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` },
    ];
  },
  async headers() {
    return [
      {
        // Pages may show PHI once loaded: never cache them, never frame them.
        source: "/:path*",
        headers: [
          { key: "Cache-Control", value: "no-store" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "no-referrer" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;

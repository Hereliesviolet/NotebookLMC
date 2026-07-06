/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  // Server-seitiger Proxy fuer relative "/api/*"-Aufrufe (siehe lib/api-client.ts):
  // der Next.js-Server selbst (im Container) leitet sie ueber das Docker-Netz an
  // die API weiter, bevor sie den Next.js-Router erreichen. Dadurch funktioniert
  // die App auch ohne Caddy direkt ueber Port 3000 - INTERNAL_API_URL ist eine
  // reine Server-Runtime-Env (kein NEXT_PUBLIC_*), wird also bei jedem Start neu
  // gelesen und erfordert keinen Image-Rebuild (siehe docs/deployment.md).
  async rewrites() {
    const internalApiUrl = process.env.INTERNAL_API_URL ?? "http://api:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${internalApiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;

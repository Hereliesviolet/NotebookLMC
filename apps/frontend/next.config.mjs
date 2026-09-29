/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  // No rewrites() proxy for "/api/*" (see lib/api-client.ts): the rewrites()
  // proxy uses Node's http client with a fixed, non-configurable timeout and
  // cut off long-running Studio generations (30-60+ s) with "socket hang up"
  // / ECONNRESET although the API finished successfully. The manual route
  // handler in app/api/[...path]/route.ts sets its own timeout instead, see
  // docs/deployment.md.
};

export default nextConfig;

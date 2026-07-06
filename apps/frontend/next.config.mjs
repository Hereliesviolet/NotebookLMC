/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  // Kein rewrites()-Proxy mehr fuer "/api/*" (siehe lib/api-client.ts): Next.js'
  // rewrites()-Proxy laeuft ueber Node's http-Client mit fixen, nicht
  // konfigurierbaren Timeouts und kappte lang laufende Studio-Generierungen
  // (Briefing/Quiz/Mindmap, 30-60+s) mit "socket hang up"/ECONNRESET, obwohl
  // die API im Hintergrund erfolgreich fertig lief. Ersetzt durch einen
  // manuellen Route-Handler (app/api/[...path]/route.ts) ohne diese
  // Timeout-Grenze - siehe docs/deployment.md.
};

export default nextConfig;

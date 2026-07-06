import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Ersetzt den frueheren rewrites()-Proxy in next.config.mjs: dessen internem
// Node-http-Client liess sich keine ausreichend hohe Zeitgrenze mitgeben,
// wodurch lang laufende Studio-Generierungen (Briefing/Quiz/Mindmap,
// 30-60+s) mit "socket hang up"/ECONNRESET abbrachen, obwohl die API im
// Hintergrund weiterlief und erfolgreich fertig wurde. Hier steuern wir das
// Timeout explizit selbst.
//
// 310s statt exakt der 300s aus apps/api/Dockerfile (Gunicorn --timeout):
// Gunicorn bricht einen haengenden Worker nach 300s selbst ab und die API
// antwortet dann bereits mit einem eigenen Fehler - der Proxy-Timeout muss
// also etwas GROESSER sein, sonst wuerde der Proxy in einem Gleichstand mit
// Gunicorn manchmal vor dessen eigener (saubereren) Fehlerantwort abbrechen.
const PROXY_TIMEOUT_MS = 310_000;

const INTERNAL_API_URL = process.env.INTERNAL_API_URL ?? "http://api:8000";

// Hop-by-hop-Header (RFC 7230 §6.1) duerfen nicht 1:1 weitergereicht werden -
// sie beschreiben die einzelne TCP-Verbindung selbst, nicht die eigentliche
// Nutzlast, und wuerden bei Client<->Proxy und Proxy<->API unterschiedliche
// Bedeutung haben.
const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "transfer-encoding",
  "upgrade",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "host",
]);

function buildTargetUrl(path: string[], search: string): string {
  const suffix = path.map((segment) => encodeURIComponent(segment)).join("/");
  return `${INTERNAL_API_URL}/api/${suffix}${search}`;
}

function forwardRequestHeaders(incoming: Headers): Headers {
  const headers = new Headers();
  incoming.forEach((value, key) => {
    if (HOP_BY_HOP_HEADERS.has(key.toLowerCase())) return;
    // fetch() berechnet die Framing-Header (chunked vs. Content-Length) beim
    // Streamen des Body selbst neu - der urspruengliche Content-Length-Wert
    // (fuer den ungestreamten Original-Body des Clients) passt sonst nicht
    // mehr und fuehrt zu haengenden/kaputten Requests an die API.
    if (key.toLowerCase() === "content-length") return;
    headers.append(key, value);
  });
  return headers;
}

function forwardResponseHeaders(upstream: Headers): Headers {
  const headers = new Headers();
  upstream.forEach((value, key) => {
    if (HOP_BY_HOP_HEADERS.has(key.toLowerCase())) return;
    headers.append(key, value);
  });
  return headers;
}

async function proxy(request: NextRequest, path: string[]): Promise<Response> {
  const { search } = new URL(request.url);
  const targetUrl = buildTargetUrl(path, search);
  const hasBody = request.method !== "GET" && request.method !== "HEAD";

  let upstream: Response;
  try {
    upstream = await fetch(targetUrl, {
      method: request.method,
      headers: forwardRequestHeaders(request.headers),
      body: hasBody ? request.body : undefined,
      // @ts-expect-error -- Node-only Option, im DOM-Typ von RequestInit fehlt sie.
      duplex: hasBody ? "half" : undefined,
      redirect: "manual",
      signal: AbortSignal.timeout(PROXY_TIMEOUT_MS),
      cache: "no-store",
    });
  } catch (error) {
    const isTimeout = error instanceof Error && error.name === "TimeoutError";
    const message = isTimeout
      ? `API-Gateway-Timeout nach ${PROXY_TIMEOUT_MS / 1000}s ohne Antwort von ${INTERNAL_API_URL}`
      : `API nicht erreichbar (${INTERNAL_API_URL}): ${error instanceof Error ? error.message : String(error)}`;
    return new Response(JSON.stringify({ detail: message }), {
      status: isTimeout ? 504 : 502,
      headers: { "content-type": "application/json" },
    });
  }

  // Content-type-agnostisch: der Response-Body wird unveraendert als Stream
  // durchgereicht (nicht als JSON/Text geparst), damit Binaerantworten wie
  // der Mindmap-PNG-Export oder PDF/DOCX-Exports unbeschaedigt beim Client
  // ankommen.
  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: forwardResponseHeaders(upstream.headers),
  });
}

// Next.js 15: `params` ist in Route Handlern jetzt ein Promise (statt eines
// synchronen Objekts) und muss vor dem Zugriff awaited werden.
type RouteParams = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: RouteParams) {
  return proxy(request, (await params).path);
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  return proxy(request, (await params).path);
}

export async function PUT(request: NextRequest, { params }: RouteParams) {
  return proxy(request, (await params).path);
}

export async function PATCH(request: NextRequest, { params }: RouteParams) {
  return proxy(request, (await params).path);
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  return proxy(request, (await params).path);
}

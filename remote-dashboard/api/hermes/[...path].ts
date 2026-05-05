import type { IncomingHttpHeaders } from "node:http";

type QueryValue = string | string[] | undefined;

type VercelRequest = {
  method?: string;
  headers: IncomingHttpHeaders;
  query: Record<string, QueryValue>;
  body?: unknown;
};

type VercelResponse = {
  status: (code: number) => VercelResponse;
  setHeader: (name: string, value: string) => void;
  send: (body: unknown) => void;
  end: () => void;
};

const ALLOWED_PREFIXES = [
  "/healthz",
  "/api/companion/text-turns",
  "/api/companion/voice-turns",
  "/api/companion/audio",
  "/api/jobs",
  "/api/skills",
];

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

function configuredToken(): string {
  return String(process.env.REMOTE_DASHBOARD_TOKEN || "").trim();
}

function configuredTunnelUrl(): string {
  return String(process.env.HERMES_TUNNEL_URL || "").trim().replace(/\/+$/, "");
}

function requestToken(req: VercelRequest): string {
  const headerToken = req.headers["x-remote-dashboard-token"];
  if (Array.isArray(headerToken)) return headerToken[0] || "";
  if (headerToken) return headerToken;

  const auth = req.headers.authorization || "";
  const match = auth.match(/^Bearer\s+(.+)$/i);
  return match?.[1] || "";
}

function hermesPath(req: VercelRequest): string {
  const value = req.query.path;
  const parts = Array.isArray(value) ? value : value ? [value] : [];
  return `/${parts.map((part) => encodeURIComponent(String(part))).join("/")}`;
}

function allowedPath(path: string): boolean {
  return ALLOWED_PREFIXES.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
}

function passthroughQuery(req: VercelRequest): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(req.query)) {
    if (key === "path") continue;
    const values = Array.isArray(value) ? value : [value];
    for (const item of values) {
      if (item !== undefined) params.append(key, String(item));
    }
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

function requestBody(req: VercelRequest): BodyInit | undefined {
  if (req.method === "GET" || req.method === "HEAD") return undefined;
  if (Buffer.isBuffer(req.body)) {
    return req.body.toString("utf8");
  }
  if (typeof req.body === "string") return req.body;
  if (req.body === undefined || req.body === null) return undefined;
  return JSON.stringify(req.body);
}

function proxyHeaders(req: VercelRequest, token: string): HeadersInit {
  const headers: Record<string, string> = {
    "X-Hermes-Remote-Token": token,
  };
  for (const [key, value] of Object.entries(req.headers)) {
    const lowered = key.toLowerCase();
    if (HOP_BY_HOP_HEADERS.has(lowered)) continue;
    if (["host", "content-length", "authorization", "x-remote-dashboard-token"].includes(lowered)) continue;
    if (Array.isArray(value)) headers[key] = value.join(", ");
    else if (value !== undefined) headers[key] = String(value);
  }
  if (req.body && !headers["content-type"] && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}

function sendJson(res: VercelResponse, status: number, payload: unknown): void {
  res.status(status).setHeader("Content-Type", "application/json; charset=utf-8");
  res.send(JSON.stringify(payload));
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }

  const token = configuredToken();
  const tunnelUrl = configuredTunnelUrl();
  if (!token || !tunnelUrl) {
    sendJson(res, 500, { error: "remote_dashboard_not_configured" });
    return;
  }

  if (requestToken(req) !== token) {
    sendJson(res, 401, { error: "unauthorized" });
    return;
  }

  let parsedTunnel: URL;
  try {
    parsedTunnel = new URL(tunnelUrl);
  } catch {
    sendJson(res, 500, { error: "invalid_tunnel_url" });
    return;
  }
  if (!["https:", "http:"].includes(parsedTunnel.protocol)) {
    sendJson(res, 500, { error: "invalid_tunnel_url_scheme" });
    return;
  }

  const path = hermesPath(req);
  if (!allowedPath(path)) {
    sendJson(res, 404, { error: "path_not_allowed", path });
    return;
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 45_000);
  try {
    const upstream = await fetch(`${parsedTunnel.toString().replace(/\/+$/, "")}${path}${passthroughQuery(req)}`, {
      method: req.method,
      headers: proxyHeaders(req, token),
      body: requestBody(req),
      signal: controller.signal,
    });
    const body = Buffer.from(await upstream.arrayBuffer());
    res.status(upstream.status);
    upstream.headers.forEach((value, key) => {
      if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase()) && key.toLowerCase() !== "content-length") {
        res.setHeader(key, value);
      }
    });
    res.setHeader("Content-Length", String(body.length));
    res.send(body);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    sendJson(res, 502, { error: "tunnel_proxy_failed", detail: message });
  } finally {
    clearTimeout(timer);
  }
}

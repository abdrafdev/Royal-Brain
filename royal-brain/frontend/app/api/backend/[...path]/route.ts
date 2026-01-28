import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { cookies } from "next/headers";

import { AUTH_COOKIE } from "@/lib/constants";
import { getBackendUrl } from "@/lib/server-env";

export const runtime = "nodejs";

type RouteContext = {
  // Next.js 16 types params as a Promise
  params: Promise<{
    path: string[];
  }>;
};

const ALLOWED_PREFIXES = new Set([
  // canonical routers
  "users",
  "sources",
  "persons",
  "relationships",
  "jurisdictions",
  "titles",
  "orders",
  "heraldic-entities",

  // engine and nested API paths
  "api",
  "ai",
  "auth",
  "health",
]);

function isAllowedPath(pathParts: string[]) {
  if (!pathParts.length) return false;
  return ALLOWED_PREFIXES.has(pathParts[0] ?? "");
}

function joinPath(parts: string[]) {
  // Encode each segment to avoid path injection.
  return parts.map((p) => encodeURIComponent(p)).join("/");
}

async function proxy(req: NextRequest, context: RouteContext) {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE)?.value;

  if (!token) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const { path: pathParts } = await context.params;
  if (!isAllowedPath(pathParts)) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }

  const incomingUrl = req.nextUrl;
  const backendBase = getBackendUrl().replace(/\/$/, "");
  const targetUrl = new URL(`${backendBase}/${joinPath(pathParts)}`);
  targetUrl.search = incomingUrl.search;

  const headers = new Headers();
  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const accept = req.headers.get("accept");
  if (accept) headers.set("accept", accept);

  headers.set("authorization", `Bearer ${token}`);

  const method = req.method.toUpperCase();
  const body = method === "GET" || method === "HEAD" ? undefined : await req.arrayBuffer();

  const resp = await fetch(targetUrl, {
    method,
    headers,
    body,
    cache: "no-store",
  });

  const out = new NextResponse(await resp.arrayBuffer(), {
    status: resp.status,
  });

  // Forward a small set of safe response headers.
  const passthroughHeaders = ["content-type", "content-disposition", "location"];
  for (const key of passthroughHeaders) {
    const v = resp.headers.get(key);
    if (v) out.headers.set(key, v);
  }
  out.headers.set("cache-control", "no-store");

  return out;
}

export async function GET(req: NextRequest, context: RouteContext) {
  return proxy(req, context);
}

export async function POST(req: NextRequest, context: RouteContext) {
  return proxy(req, context);
}

export async function PUT(req: NextRequest, context: RouteContext) {
  return proxy(req, context);
}

export async function PATCH(req: NextRequest, context: RouteContext) {
  return proxy(req, context);
}

export async function DELETE(req: NextRequest, context: RouteContext) {
  return proxy(req, context);
}

import { NextResponse } from "next/server";
import { cookies } from "next/headers";

import { AUTH_COOKIE } from "@/lib/constants";
import { getBackendUrl } from "@/lib/server-env";

export const runtime = "nodejs";

export async function POST(req: Request) {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE)?.value;

  if (!token) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const body = await req.json().catch(() => null);
  if (!body || !body.result) {
    return NextResponse.json({ detail: "Invalid request" }, { status: 400 });
  }

  const backendUrl = getBackendUrl();

  const resp = await fetch(`${backendUrl}/ai/explain-succession`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({ detail: "Backend error" }));
    return NextResponse.json(errorData, { status: resp.status });
  }

  const data = await resp.json();
  return NextResponse.json(data);
}

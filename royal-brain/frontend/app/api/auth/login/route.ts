import { NextResponse } from "next/server";

import { AUTH_COOKIE } from "@/lib/constants";
import { getBackendUrl } from "@/lib/server-env";

export const runtime = "nodejs";

type LoginBody = {
  email?: unknown;
  password?: unknown;
};

export async function POST(req: Request) {
  const body = (await req.json().catch(() => ({}))) as LoginBody;

  if (typeof body.email !== "string" || typeof body.password !== "string") {
    return NextResponse.json(
      { error: "Invalid request." },
      { status: 400, headers: { "Cache-Control": "no-store" } },
    );
  }

  const backendUrl = getBackendUrl();

  const form = new URLSearchParams();
  form.set("username", body.email);
  form.set("password", body.password);

  const resp = await fetch(`${backendUrl}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
    cache: "no-store",
  });

  if (!resp.ok) {
    return NextResponse.json(
      { error: "Authentication failed." },
      { status: 401, headers: { "Cache-Control": "no-store" } },
    );
  }

  const data = (await resp.json()) as { access_token?: unknown };
  if (typeof data.access_token !== "string") {
    return NextResponse.json(
      { error: "Authentication failed." },
      { status: 401, headers: { "Cache-Control": "no-store" } },
    );
  }

  const res = NextResponse.json(
    { ok: true },
    {
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );

  res.cookies.set({
    name: AUTH_COOKIE,
    value: data.access_token,
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60,
  });

  return res;
}

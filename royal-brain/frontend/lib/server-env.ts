import "server-only";

import fs from "node:fs";
import path from "node:path";

type EnvMap = Record<string, string>;

function parseDotenv(contents: string): EnvMap {
  const env: EnvMap = {};

  for (const rawLine of contents.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;

    const eq = line.indexOf("=");
    if (eq === -1) continue;

    const key = line.slice(0, eq).trim();
    let value = line.slice(eq + 1).trim();

    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }

    env[key] = value;
  }

  return env;
}

let _cachedRootEnv: EnvMap | null = null;

export function getRootEnv(): EnvMap {
  if (_cachedRootEnv) return _cachedRootEnv;

  const rbEnv = (process.env.RB_ENV ?? "dev").trim() || "dev";

  // In production (Docker/standalone output), the repo-root env file usually isn't present.
  // Prefer runtime environment variables and treat file-based env loading as best-effort.
  try {
    const repoRoot = path.resolve(process.cwd(), "..");
    const envPath = path.join(repoRoot, `.env.${rbEnv}`);

    if (!fs.existsSync(envPath)) {
      _cachedRootEnv = {};
      return _cachedRootEnv;
    }

    const contents = fs.readFileSync(envPath, "utf8");
    _cachedRootEnv = parseDotenv(contents);
    return _cachedRootEnv;
  } catch {
    _cachedRootEnv = {};
    return _cachedRootEnv;
  }
}

export function getBackendUrl(): string {
  // Prefer runtime env vars for deployments.
  const raw =
    process.env.BACKEND_URL ||
    getRootEnv().BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    "http://localhost:8000";

  const trimmed = raw.trim();

  // On some Windows setups, `localhost` may resolve to IPv6 (::1) first, while the backend
  // listens on IPv4 only. Normalize to 127.0.0.1 for server-side fetches.
  try {
    const url = new URL(trimmed);
    if (url.hostname === "localhost") url.hostname = "127.0.0.1";
    return url.toString().replace(/\/$/, "");
  } catch {
    return trimmed.replace(/\/$/, "");
  }
}

import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone', // Required for Docker production builds
  turbopack: {
    // Ensure Turbopack resolves the workspace from this app directory (monorepo-friendly).
    root: __dirname,
  },
};

export default nextConfig;

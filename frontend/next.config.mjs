import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Use frontend as Turbopack root so a parent package-lock.json doesn't trigger the lockfile warning
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;

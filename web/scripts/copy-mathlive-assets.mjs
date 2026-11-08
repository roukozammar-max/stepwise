// Copy MathLive's fonts into public/ so the browser can load them from
// /mathlive/fonts. Runs automatically after `npm install` and before
// `npm run dev` / `npm run build`.
import { cpSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const from = join(root, "node_modules", "mathlive", "fonts");
const to = join(root, "public", "mathlive", "fonts");

if (!existsSync(from)) {
  console.warn("MathLive isn't installed yet; skipping font copy.");
  process.exit(0);
}
cpSync(from, to, { recursive: true });
console.log("Copied MathLive fonts to public/mathlive/fonts");

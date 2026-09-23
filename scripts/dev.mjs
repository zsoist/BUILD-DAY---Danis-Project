// Sitio local CON el proxy real: sirve web/ y manda /api/opina al handler de
// api/opina.js (el mismo archivo que se despliega). Lee .env; no imprime llaves.
//   node scripts/dev.mjs            → http://localhost:8377
import { createServer } from "node:http";
import { readFileSync, existsSync, statSync } from "node:fs";
import { join, extname, normalize } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const RAIZ = fileURLToPath(new URL("..", import.meta.url));
const WEB = join(RAIZ, "web");
const PUERTO = +(process.env.PORT || 8377);
for (const l of readFileSync(join(RAIZ, ".env"), "utf8").split("\n")) {
  const m = l.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
  if (m && !(m[1] in process.env)) process.env[m[1]] = m[2].replace(/^["']|["']$/g, "");
}
process.env.ALLOWED_ORIGINS = `http://localhost:${PUERTO}`;
process.env.BANCO_URL = `http://localhost:${PUERTO}/banco.json`;
const { default: opina } = await import(pathToFileURL(join(RAIZ, "api", "opina.js")).href);

const TIPO = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".mjs": "text/javascript",
  ".json": "application/json", ".webp": "image/webp", ".png": "image/png", ".svg": "image/svg+xml",
  ".css": "text/css", ".woff2": "font/woff2" };

// la forma mínima de req/res que usa el handler de Vercel
function envolver(res) {
  res.status = c => { res.statusCode = c; return res; };
  res.json = o => { if (!res.headersSent) res.setHeader("Content-Type", "application/json"); res.end(JSON.stringify(o)); return res; };
  return res;
}

createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PUERTO}`);
  if (url.pathname.replace(/\/$/, "") === "/api/opina") {
    let crudo = "";
    for await (const t of req) crudo += t;
    try { req.body = crudo ? JSON.parse(crudo) : {}; } catch { req.body = {}; }
    try { await opina(req, envolver(res)); }
    catch (e) { console.error("opina:", e.message); if (!res.headersSent) envolver(res).status(500).json({ error: "local" }); }
    return;
  }
  let f = normalize(join(WEB, decodeURIComponent(url.pathname)));
  if (!f.startsWith(WEB)) { res.statusCode = 403; return res.end(); }
  if (existsSync(f) && statSync(f).isDirectory()) f = join(f, "index.html");
  if (!existsSync(f)) { res.statusCode = 404; return res.end("no"); }
  res.setHeader("Content-Type", TIPO[extname(f)] || "application/octet-stream");
  res.setHeader("Cache-Control", "no-store");
  res.end(readFileSync(f));
}).listen(PUERTO, () => console.log(`ColombIA local con proxy: http://localhost:${PUERTO}`));

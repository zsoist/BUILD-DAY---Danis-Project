/* EXPERIMENTO "¿son personas reales?" — generación A/B.
   A = andamiaje completo de producción (persona() + sondeoInstr(), extraídos del index.html vivo)
   B = control desnudo (mismos residentes, prompt mínimo)
   Mismos residentes, misma pregunta, misma temperatura => la diferencia ES el andamiaje. */
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import path from "node:path";

// la raíz del repo, calculada: una ruta de disco quemada solo servía en una máquina
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const html = fs.readFileSync(path.join(ROOT, "web/index.html"), "utf8");
const script = html.slice(html.indexOf("<script>") + 8, html.lastIndexOf("</script>"));

/* extractor por nombre: toma la declaración completa balanceando llaves/corchetes */
function extraer(nombre) {
  const pats = [
    new RegExp(`\\nfunction ${nombre}\\s*\\(`),
    new RegExp(`\\nconst ${nombre}\\s*=`),
  ];
  for (const [k, re] of pats.entries()) {
    const m = script.match(re);
    if (!m) continue;
    const i = m.index + 1;
    // `function f(...)` → emparejar SOLO las llaves del cuerpo, desde su primer '{'
    const desde = k === 0 ? script.indexOf("{", script.indexOf("(", i)) : i;
    let prof = 0, abierto = false, q = null, esc = false;
    for (let j = desde; j < script.length; j++) {
      const c = script[j];
      if (esc) { esc = false; continue; }
      if (q) { if (c === "\\") esc = true; else if (c === q) q = null; continue; }
      if (c === '"' || c === "'" || c === "`") { q = c; continue; }
      if ("{[(".includes(c)) { prof++; abierto = true; }
      else if ("}])".includes(c)) {
        prof--;
        if (k === 0 && prof === 0) return script.slice(i, j + 1);   // fin del cuerpo
      }
      // `const X = ...;` → termina en el ';' de nivel cero
      else if (k === 1 && c === ";" && prof === 0 && abierto) return script.slice(i, j + 1);
      else if (k === 1 && c === "\n" && prof === 0 && abierto) return script.slice(i, j);
    }
  }
  throw new Error(`no encontré ${nombre}`);
}

const NOMBRES = ["TEMPERAMENTOS", "LEAN", "FRANQUEZA", "ARRANQUES", "estiloDe",
  "FUNDAMENTOS", "marcoDe", "COMPROMISO_TXT", "LEAN_TXT", "leanLinea",
  "vida", "DIALECTOS", "dialectoDe", "persona", "sondeoInstr"];
const fuente = NOMBRES.map(extraer).join("\n");
const OPC = null;                                    // sondeo libre, sin opciones A/B
const mod = new Function("OPC", fuente + "\nreturn {persona,sondeoInstr,marcoDe,estiloDe,vida};")(OPC);

/* ── residentes: misma muestra determinista para A y B ── */
const RES = JSON.parse(fs.readFileSync(path.join(ROOT, "web/residents_v2.json"), "utf8"));
const residentes = (RES.residentes || RES).filter(r => r.edad >= 16);
const DOS = JSON.parse(fs.readFileSync(path.join(ROOT, "web/dossiers.json"), "utf8"));
const MARG = JSON.parse(fs.readFileSync(path.join(ROOT, "web/marginals.json"), "utf8")).departamentos;

/* PRNG con semilla fija: el experimento es reproducible */
let seed = 20260922;
const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
const N = Number(process.argv[2] || 24);
const muestra = [], usados = new Set();
const codigos = Object.keys(MARG), pesos = codigos.map(c => [c, MARG[c]?.poblacion || 1]);
const tot = pesos.reduce((a, [, w]) => a + w, 0);
let guardia = 0;
while (muestra.length < N && guardia++ < N * 400) {
  let x = rnd() * tot, cod = pesos[0][0];
  for (const [c, w] of pesos) { x -= w; if (x <= 0) { cod = c; break; } }
  const pool = residentes.filter(r => r.dpto === cod && !usados.has(r.id));
  if (pool.length) { const r = pool[Math.floor(rnd() * pool.length)]; usados.add(r.id); muestra.push(r); }
}

const PREGUNTA = process.argv[3] || "¿Debería el Estado dar un subsidio mensual a los jóvenes que ni estudian ni trabajan?";

/* ── llamadas a DeepSeek (nada de Anthropic: los $91 no se tocan) ── */
const env = Object.fromEntries(fs.readFileSync(path.join(ROOT, ".env"), "utf8")
  .split("\n").filter(l => l.includes("=") && !l.trim().startsWith("#"))
  .map(l => [l.slice(0, l.indexOf("=")).trim(), l.slice(l.indexOf("=") + 1).trim().replace(/^["']|["']$/g, "")]));
const KEY = env.DEEPSEEK_API_KEY || env.DEEPSEEK_KEY;
if (!KEY) throw new Error("falta DEEPSEEK_API_KEY");

async function flash(messages, max_tokens = 220) {
  for (let intento = 0; intento < 3; intento++) {
    try {
      const r = await fetch("https://api.deepseek.com/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${KEY}` },
        body: JSON.stringify({ model: "deepseek-flash", messages, max_tokens, temperature: 1.0, reasoning_effort: "none" }),
      });
      if (!r.ok) { await new Promise(s => setTimeout(s, 1500 * (intento + 1))); continue; }
      const j = await r.json();
      return j.choices?.[0]?.message?.content || "";
    } catch (e) { await new Promise(s => setTimeout(s, 1500 * (intento + 1))); }
  }
  return "";
}

const CIERRE = "\nCierra SIEMPRE con [POSTURA: a_favor|en_contra|depende|ni_ni].";
function promptA(r) {
  const dos = DOS[r.dpto] || {};
  return mod.persona(r, dos) + mod.sondeoInstr(r);
}
function promptB(r) {   // control desnudo: lo que haría cualquiera sin el andamiaje
  return `Eres un colombiano de ${r.edad} años, ${r.sexo}, ${r.ocupacion}, de ${r.dpto_nombre}. `
    + `Responde la encuesta en 1-2 frases, hablando como hablaría esa persona.` + CIERRE;
}

async function lote(nombre, hacerPrompt) {
  const out = [];
  const cola = [...muestra];
  const workers = Array.from({ length: 6 }, async () => {
    while (cola.length) {
      const r = cola.shift();
      const txt = await flash([{ role: "system", content: hacerPrompt(r) }, { role: "user", content: PREGUNTA }]);
      out.push({ id: r.id, edad: r.edad, sexo: r.sexo, dpto: r.dpto, dpto_nombre: r.dpto_nombre,
        ocupacion: r.ocupacion, educacion: r.educacion, clase: r.clase, compromiso: r.compromiso,
        lean: r.lean, marco: mod.marcoDe(r).cons, fund: mod.marcoDe(r).fund,
        libreto: mod.estiloDe(r).lean, temp: mod.estiloDe(r).temp, texto: txt });
      process.stderr.write(".");
    }
  });
  await Promise.all(workers);
  process.stderr.write(` ${nombre} listo (${out.length})\n`);
  return out;
}

const A = await lote("A(andamiaje)", promptA);
const B = await lote("B(control)", promptB);
const salida = { pregunta: PREGUNTA, n: muestra.length, fecha: new Date().toISOString(), A, B };
fs.writeFileSync(process.argv[4] || "/tmp/experimento.json", JSON.stringify(salida, null, 1));
console.log(`OK — ${A.length} respuestas A + ${B.length} B → ${process.argv[4] || "/tmp/experimento.json"}`);
